"""Root-owned local service: only certificate/account setup for GC soil nodes.

No shell, arbitrary paths or service names are accepted from callers. Unix peer
credentials and socket permissions restrict callers to the Grow Central service.
"""
from datetime import datetime, timedelta, timezone
import base64
import grp
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

MOSQUITTO = Path('/etc/mosquitto')
BASE = MOSQUITTO / 'grow-central-sensor-broker'
LOCK = threading.Lock()
DEVICE_ID = re.compile(r'^gc-soil-[a-f0-9]{6}$')


def local_hosts():
    result = {'135er-grow-central.local'}
    raw = subprocess.check_output([shutil.which('ip') or '/usr/sbin/ip', '-j', '-4', 'address', 'show', 'up'], timeout=5)
    for interface in json.loads(raw):
        if interface.get('ifname') == 'lo':
            continue
        for address in interface.get('addr_info', []):
            value = ipaddress.ip_address(address['local'])
            if not value.is_loopback and not value.is_link_local and not value.is_multicast:
                result.add(str(value))
    # Prefer routable LAN IPs over mDNS for embedded clients.
    return sorted(result, key=lambda host: not host[0].isdigit())


def write_file(path, data, mode=0o600, gid=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        os.fchmod(descriptor, mode)
        if gid is not None:
            os.fchown(descriptor, 0, gid)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(data if isinstance(data, bytes) else data.encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def certificates(hosts):
    BASE.mkdir(mode=0o750, parents=True, exist_ok=True)
    # Mosquitto needs directory traversal; private CA/accounts remain root:0600.
    os.chmod(BASE, 0o750)  # nosec B103
    broker_gid = grp.getgrnam('mosquitto').gr_gid
    os.chown(BASE, 0, broker_gid)
    now = datetime.now(timezone.utc)
    ca_path, ca_key_path = BASE / 'ca.crt', BASE / 'ca.key'
    if ca_path.exists():
        ca = x509.load_pem_x509_certificate(ca_path.read_bytes())
        key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
        if ca.not_valid_after_utc < now + timedelta(days=30):
            raise RuntimeError('Lokale CA muss erneuert werden; vorhandene Sensoren nicht automatisch umstellen.')
    else:
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Grow Central Sensor CA')])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
              .not_valid_after(now + timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
              .sign(key, hashes.SHA256()))
        write_file(ca_key_path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        write_file(ca_path, ca.public_bytes(serialization.Encoding.PEM), 0o644)
    cert_path = BASE / 'server.crt'
    if cert_path.exists():
        current = x509.load_pem_x509_certificate(cert_path.read_bytes())
        san = current.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        names = set(san.get_values_for_type(x509.DNSName)) | {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
        if set(hosts).issubset(names) and current.not_valid_after_utc > now + timedelta(days=30):
            return ca
    server_key = ec.generate_private_key(ec.SECP256R1())
    sans = []
    for host in hosts:
        try:
            sans.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            sans.append(x509.DNSName(host))
    certificate = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Grow Central MQTT')]))
        .issuer_name(ca.subject).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(sans), False)
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), False)
        .sign(key, hashes.SHA256()))
    write_file(BASE / 'server.key', server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()), 0o640, broker_gid)
    write_file(cert_path, certificate.public_bytes(serialization.Encoding.PEM), 0o644)
    return ca


def password_record(device_id, password):
    descriptor, name = tempfile.mkstemp(dir=BASE, prefix='.account-')
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(device_id + ':' + password + '\n')
        # Only the private single-account temporary file is converted; existing
        # hashes are preserved and passwords never become process arguments.
        subprocess.run([shutil.which('mosquitto_passwd') or '/usr/bin/mosquitto_passwd', '-U', name], check=True, capture_output=True, timeout=5)
        return Path(name).read_text().strip()
    finally:
        os.unlink(name)


def configure(device_id, host):
    hosts = local_hosts()
    if host not in hosts or not DEVICE_ID.fullmatch(device_id):
        raise ValueError('Ungültiger lokaler Broker oder Sensor.')
    conf = MOSQUITTO / 'conf.d/grow-central-usb-tls.conf'
    for other in (MOSQUITTO / 'conf.d').glob('*.conf'):
        if other != conf and re.search(r'^\s*listener\s+8883\b', other.read_text(), re.MULTILINE):
            raise RuntimeError('Port 8883 wird bereits manuell verwaltet; bestehende Konfiguration zuerst prüfen.')
    ca = certificates(hosts)
    accounts_path = BASE / 'accounts.json'
    accounts = json.loads(accounts_path.read_text()) if accounts_path.exists() else {}
    if device_id not in accounts:
        accounts[device_id] = secrets.token_urlsafe(32)
        write_file(accounts_path, json.dumps(accounts))
    password = accounts[device_id]
    password_path = BASE / 'passwords'
    records = password_path.read_text().splitlines() if password_path.exists() else []
    if not any(line.startswith(device_id + ':') for line in records):
        records.append(password_record(device_id, password))
        write_file(password_path, '\n'.join(records) + '\n', 0o640, grp.getgrnam('mosquitto').gr_gid)
    acl = '\n'.join('pattern write growcentral/v1/devices/%u/' + leaf for leaf in ['announce', 'state', 'availability', 'proof'])
    acl += '\npattern read growcentral/v1/devices/%u/challenge\n'
    write_file(BASE / 'acl', acl, 0o644)
    write_file(conf, f'''# Managed by Grow Central USB onboarding; localhost 1883 stays local-only.
listener 8883 0.0.0.0
allow_anonymous false
password_file {password_path}
acl_file {BASE / 'acl'}
cafile {BASE / 'ca.crt'}
certfile {BASE / 'server.crt'}
keyfile {BASE / 'server.key'}
tls_version tlsv1.2
''', 0o644)
    subprocess.run(['/usr/bin/systemctl', 'restart', 'mosquitto.service'], check=True, capture_output=True, timeout=15)
    return {'ok': True, 'host': host, 'port': 8883, 'username': device_id, 'password': password,
            'ca': base64.b64encode(ca.public_bytes(serialization.Encoding.DER)).decode()}


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        _, uid, _ = struct.unpack('3i', self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
        if uid not in {0, pwd.getpwnam('growcentral').pw_uid}:
            return
        try:
            raw = self.rfile.readline(4097)
            if len(raw) > 4096 or not raw.endswith(b'\n'):
                raise ValueError('Ungültige Broker-Anfrage.')
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('Ungültige Broker-Anfrage.')
            with LOCK:
                if data.get('action') == 'info' and set(data) == {'action'}:
                    result = {'ok': True, 'hosts': local_hosts()}
                elif data.get('action') == 'provision' and set(data) == {'action', 'device_id', 'host'} and isinstance(data['device_id'], str) and isinstance(data['host'], str):
                    result = configure(data['device_id'], data['host'])
                else:
                    raise ValueError('Broker-Aktion nicht erlaubt.')
        except (ValueError, OSError, KeyError, RuntimeError, subprocess.SubprocessError):
            # Do not return exception output, paths, commands or passwords.
            result = {'ok': False, 'error': 'Lokale Broker-Einrichtung fehlgeschlagen; Dienststatus und vorhandene TLS-Konfiguration prüfen.'}
        self.wfile.write(json.dumps(result).encode() + b'\n')


def main():
    path = Path('/run/grow-central-provisioning/broker.sock')
    path.parent.mkdir(mode=0o750, exist_ok=True)
    path.unlink(missing_ok=True)
    with socketserver.ThreadingUnixStreamServer(str(path), Handler) as server:
        os.chown(path, 0, grp.getgrnam('growcentral').gr_gid)
        # This is an AF_UNIX socket, not a credential file. SO_PEERCRED also
        # requires root or the exact growcentral UID before dispatching requests.
        os.chmod(path, 0o660)  # nosec B103
        server.serve_forever()


if __name__ == '__main__':
    main()
