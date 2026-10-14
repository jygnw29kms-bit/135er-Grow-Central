"""Unix-socket client. Credentials never leave the local USB worker."""
import json
import os
import socket

SOCKET_PATH = '/run/grow-central-provisioning/broker.sock'


def request_broker(action, **values):
    payload = json.dumps({'action': action, **values}).encode() + b'\n'
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(20)
        connection.connect(os.getenv('GC_PROVISIONING_SOCKET', SOCKET_PATH))
        connection.sendall(payload)
        data = bytearray()
        while b'\n' not in data:
            chunk = connection.recv(4096)
            if not chunk or len(data) + len(chunk) > 8192:
                raise RuntimeError('Lokaler Broker-Dienst liefert keine gültige Antwort.')
            data.extend(chunk)
    result = json.loads(data.split(b'\n', 1)[0])
    if not result.get('ok'):
        raise RuntimeError(result.get('error', 'Broker-Einrichtung fehlgeschlagen.'))
    return result
