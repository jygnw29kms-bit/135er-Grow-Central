#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DOMAIN="${ROOT_DOMAIN:-dezender.de}"
CLOUD_HOST="${CLOUD_HOST:-135ercloud.dezender.de}"
SERVICE="${SERVICE:-135er-growcentral-cloud}"
APP_USER="${APP_USER:-growcentral-cloud}"
APP_DIR="${APP_DIR:-/opt/${SERVICE}}"
DATA_DIR="${DATA_DIR:-/var/lib/${SERVICE}}"
CONF_DIR="${CONF_DIR:-/etc/${SERVICE}}"
ENV_FILE="${CONF_DIR}/cloud.env"
BACKUP_DIR="/root/${SERVICE}-backups"
SYSTEMD_FILE="/etc/systemd/system/${SERVICE}.service"
APP_PORT="${APP_PORT:-}"
PAIR_TTL=600

log(){ printf '\033[1;36m[GrowCentral]\033[0m %s\n' "$*"; }
ok(){ printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[FEHLER]\033[0m %s\n' "$*" >&2; exit 1; }

rollback_vhost(){ local vhost="${1:-}" backup="${2:-}"; [[ -n "$vhost" ]] || return 0; if [[ -n "$backup" && -f "$backup" ]]; then cp -a "$backup" "$vhost"; else rm -f "$vhost"; fi; plesk sbin httpdmng --reconfigure-domain "$CLOUD_HOST" >/dev/null 2>&1 || true; }
trap 'rc=$?; warn "Installer mit Fehlercode $rc beendet."; warn "Bestehende Website $ROOT_DOMAIN wurde nicht ersetzt."; exit $rc' ERR

require_root(){ [[ "$EUID" -eq 0 ]] || die "Bitte als root ausführen."; }

detect_platform(){ [[ -r /etc/os-release ]] || die "/etc/os-release fehlt."; . /etc/os-release; case "${ID:-}" in debian|ubuntu) ;; *) die "Freigegeben für Debian/Ubuntu mit Plesk." ;; esac; command -v plesk >/dev/null 2>&1 || die "Plesk nicht gefunden."; plesk bin domain --info "$ROOT_DOMAIN" >/dev/null 2>&1 || die "Plesk-Domain $ROOT_DOMAIN fehlt."; }

install_packages(){ export DEBIAN_FRONTEND=noninteractive; apt-get update -y; apt-get install -y --no-install-recommends ca-certificates curl openssl sqlite3 python3 python3-venv python3-pip iproute2 util-linux; }

choose_port(){ if [[ -n "$APP_PORT" ]]; then case "$APP_PORT" in 80|443|8443|8880) die "APP_PORT kollidiert mit Plesk.";; esac; echo "$APP_PORT"; return; fi; local p; for p in 18765 18766 18767 18768 18769 18770 18771 18772; do if ! ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(:|\])${p}$"; then echo "$p"; return; fi; done; die "Kein freier interner Port gefunden."; }

prepare_user_dirs(){ id "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"; install -d -m 0755 -o root -g root "$APP_DIR"; install -d -m 0750 -o "$APP_USER" -g "$APP_USER" "$DATA_DIR"; install -d -m 0750 -o root -g "$APP_USER" "$CONF_DIR"; install -d -m 0700 -o root -g root "$BACKUP_DIR"; }

configure_database(){ DB_KIND="sqlite"; DATABASE_URL="sqlite:////${DATA_DIR#/}/cloud.sqlite3"; if id postgres >/dev/null 2>&1 && command -v psql >/dev/null 2>&1 && { systemctl is-active --quiet postgresql 2>/dev/null || pgrep -x postgres >/dev/null 2>&1; }; then local pgpass; pgpass="$(openssl rand -hex 32)"; if runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='growcentral_cloud'" | grep -q 1; then runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "ALTER ROLE growcentral_cloud WITH LOGIN PASSWORD '${pgpass}';" >/dev/null; else runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE ROLE growcentral_cloud WITH LOGIN PASSWORD '${pgpass}';" >/dev/null; fi; if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='growcentral_cloud'" | grep -q 1; then runuser -u postgres -- createdb -O growcentral_cloud growcentral_cloud; fi; DB_KIND="postgresql"; DATABASE_URL="postgresql+psycopg://growcentral_cloud:${pgpass}@127.0.0.1:5432/growcentral_cloud"; ok "PostgreSQL aktiv."; else ok "SQLite/WAL aktiv."; fi; }

write_env(){ local server_secret cookie_secret; server_secret="$(openssl rand -hex 32)"; cookie_secret="$(openssl rand -hex 32)"; if [[ -f "$ENV_FILE" ]]; then server_secret="$(grep '^SERVER_SECRET=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"; cookie_secret="$(grep '^COOKIE_SECRET=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"; [[ ${#server_secret} -ge 32 ]] || server_secret="$(openssl rand -hex 32)"; [[ ${#cookie_secret} -ge 32 ]] || cookie_secret="$(openssl rand -hex 32)"; cp -a "$ENV_FILE" "$BACKUP_DIR/cloud.env.$(date +%Y%m%d-%H%M%S)"; fi; umask 077; cat > "$ENV_FILE" <<EOF
APP_PORT=$APP_PORT
PUBLIC_URL=https://$CLOUD_HOST
DATABASE_URL=$DATABASE_URL
SERVER_SECRET=$server_secret
COOKIE_SECRET=$cookie_secret
ACCESS_TTL_SECONDS=900
REFRESH_TTL_SECONDS=2592000
PAIR_TTL_SECONDS=$PAIR_TTL
EOF
chown root:"$APP_USER" "$ENV_FILE"; chmod 0640 "$ENV_FILE"; }

install_python_runtime(){ python3 -m venv "$APP_DIR/venv"; "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip; "$APP_DIR/venv/bin/pip" install --quiet "fastapi>=0.116,<1" "uvicorn[standard]>=0.35,<1" "sqlalchemy>=2.0,<3" "psycopg[binary]>=3.2,<4" "argon2-cffi>=23.1,<26" "cryptography>=45,<47" "python-multipart>=0.0.20,<1"; }

write_application(){ cat > "$APP_DIR/app.py" <<'PY'
import asyncio,base64,hashlib,html,json,os,secrets,time,uuid
from collections import defaultdict
from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import FastAPI,Form,Header,HTTPException,WebSocket,WebSocketDisconnect
from fastapi.responses import HTMLResponse,JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine,text
PUBLIC_URL=os.environ['PUBLIC_URL'].rstrip('/'); DATABASE_URL=os.environ['DATABASE_URL']; ACCESS_TTL=int(os.environ.get('ACCESS_TTL_SECONDS','900')); REFRESH_TTL=int(os.environ.get('REFRESH_TTL_SECONDS','2592000')); PAIR_TTL=int(os.environ.get('PAIR_TTL_SECONDS','600'))
engine=create_engine(DATABASE_URL,pool_pre_ping=True,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite:') else {})
ph=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2); app=FastAPI(title='135er GrowCentral Cloud',version='4.0',docs_url=None,redoc_url=None); device_sockets={}; client_sockets=defaultdict(set); socket_lock=asyncio.Lock()
def now(): return int(time.time())
def sha(v): return hashlib.sha256(v.encode()).hexdigest()
def tok(bits=256): return secrets.token_urlsafe(bits//8)
def bearer(a):
    if not a or not a.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
    return a[7:].strip()
def init_db():
    stmts=["CREATE TABLE IF NOT EXISTS accounts(id VARCHAR(36) PRIMARY KEY,email VARCHAR(320) NOT NULL UNIQUE,password_hash TEXT NOT NULL,created_at BIGINT NOT NULL,status VARCHAR(20) NOT NULL DEFAULT 'active')","CREATE TABLE IF NOT EXISTS devices(id VARCHAR(36) PRIMARY KEY,account_id VARCHAR(36),hardware_guid VARCHAR(255) NOT NULL,public_key TEXT NOT NULL,name VARCHAR(120) NOT NULL,created_at BIGINT NOT NULL,last_seen BIGINT,revoked_at BIGINT,UNIQUE(hardware_guid,public_key))","CREATE TABLE IF NOT EXISTS pairings(device_code_hash VARCHAR(64) PRIMARY KEY,user_code VARCHAR(20) NOT NULL UNIQUE,hardware_guid VARCHAR(255) NOT NULL,public_key TEXT NOT NULL,name VARCHAR(120) NOT NULL,created_at BIGINT NOT NULL,expires_at BIGINT NOT NULL,approved_account_id VARCHAR(36),consumed_at BIGINT)","CREATE TABLE IF NOT EXISTS access_sessions(token_hash VARCHAR(64) PRIMARY KEY,account_id VARCHAR(36) NOT NULL,created_at BIGINT NOT NULL,expires_at BIGINT NOT NULL,revoked_at BIGINT)","CREATE TABLE IF NOT EXISTS refresh_sessions(token_hash VARCHAR(64) PRIMARY KEY,account_id VARCHAR(36) NOT NULL,family_id VARCHAR(36) NOT NULL,created_at BIGINT NOT NULL,expires_at BIGINT NOT NULL,rotated_at BIGINT,revoked_at BIGINT)","CREATE TABLE IF NOT EXISTS device_nonces(nonce_hash VARCHAR(64) PRIMARY KEY,device_id VARCHAR(36) NOT NULL,created_at BIGINT NOT NULL,expires_at BIGINT NOT NULL,used_at BIGINT)"]
    with engine.begin() as c:
        for s in stmts:c.execute(text(s))
init_db()
def acc(raw):
    with engine.begin() as c:r=c.execute(text('SELECT account_id FROM access_sessions WHERE token_hash=:h AND expires_at>:t AND revoked_at IS NULL'),{'h':sha(raw),'t':now()}).mappings().first()
    if not r: raise HTTPException(401,'invalid access token')
    return r['account_id']
def issue(a,f=None):
    t=now(); at=tok(256); rt=tok(384); fam=f or str(uuid.uuid4())
    with engine.begin() as c:c.execute(text('INSERT INTO access_sessions(token_hash,account_id,created_at,expires_at) VALUES(:h,:a,:c,:e)'),{'h':sha(at),'a':a,'c':t,'e':t+ACCESS_TTL});c.execute(text('INSERT INTO refresh_sessions(token_hash,account_id,family_id,created_at,expires_at) VALUES(:h,:a,:f,:c,:e)'),{'h':sha(rt),'a':a,'f':fam,'c':t,'e':t+REFRESH_TTL})
    return {'access_token':at,'token_type':'Bearer','expires_in':ACCESS_TTL,'refresh_token':rt,'refresh_expires_in':REFRESH_TTL}
def email(v):
    v=v.strip().lower()
    if len(v)>320 or '@' not in v: raise HTTPException(400,'invalid email')
    return v
def pw(v):
    if len(v)<12: raise HTTPException(400,'password must have at least 12 characters')
class RegisterBody(BaseModel):email:str;password:str
class LoginBody(BaseModel):email:str;password:str
class RefreshBody(BaseModel):refresh_token:str
class PairStart(BaseModel):hardware_guid:str;public_key:str;name:str='GrowCentral'
class PairPoll(BaseModel):device_code:str
class ChallengeBody(BaseModel):device_id:str
@app.get('/health')
def health():return {'ok':True,'service':'135er-growcentral-cloud','version':4,'time':now(),'online_devices':len(device_sockets)}
@app.get('/.well-known/growcentral-cloud')
def discovery():return {'product':'135er-GrowCentral','protocol_version':2,'cloud_version':4,'official':PUBLIC_URL=='https://135ercloud.dezender.de','public_url':PUBLIC_URL,'requires_https':True,'device_identity':'ed25519','pairing_url':PUBLIC_URL+'/pair','device_websocket':PUBLIC_URL.replace('https://','wss://')+'/api/v2/device/connect','remote_websocket':PUBLIC_URL.replace('https://','wss://')+'/api/v2/remote/connect'}
@app.post('/api/v2/account/register')
def register(b:RegisterBody):
    e=email(b.email);pw(b.password);aid=str(uuid.uuid4())
    try:
        with engine.begin() as c:c.execute(text("INSERT INTO accounts(id,email,password_hash,created_at,status) VALUES(:i,:e,:p,:c,'active')"),{'i':aid,'e':e,'p':ph.hash(b.password),'c':now()})
    except Exception:raise HTTPException(409,'account exists')
    return issue(aid)
@app.post('/api/v2/account/login')
def login(b:LoginBody):
    e=email(b.email)
    with engine.begin() as c:r=c.execute(text('SELECT id,password_hash,status FROM accounts WHERE email=:e'),{'e':e}).mappings().first()
    if not r or r['status']!='active':raise HTTPException(401,'invalid credentials')
    try:ph.verify(r['password_hash'],b.password)
    except VerifyMismatchError:raise HTTPException(401,'invalid credentials')
    return issue(r['id'])
@app.post('/api/v2/device/authorize')
def authorize(b:PairStart):
    if len(b.hardware_guid.strip())<16:raise HTTPException(400,'invalid guid')
    try:
        raw=base64.urlsafe_b64decode(b.public_key+'='*(-len(b.public_key)%4));Ed25519PublicKey.from_public_bytes(raw)
        if len(raw)!=32:raise ValueError()
    except Exception:raise HTTPException(400,'invalid public key')
    dc=tok(384);alpha='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';uc='-'.join(''.join(secrets.choice(alpha) for _ in range(4)) for _ in range(2));t=now()
    with engine.begin() as c:c.execute(text('INSERT INTO pairings(device_code_hash,user_code,hardware_guid,public_key,name,created_at,expires_at,approved_account_id,consumed_at) VALUES(:h,:u,:g,:p,:n,:c,:e,NULL,NULL)'),{'h':sha(dc),'u':uc,'g':b.hardware_guid.strip(),'p':b.public_key,'n':b.name[:120],'c':t,'e':t+PAIR_TTL})
    return {'device_code':dc,'user_code':uc,'verification_uri':PUBLIC_URL+'/pair','verification_uri_complete':PUBLIC_URL+'/pair?code='+uc,'expires_in':PAIR_TTL,'interval':5}
@app.get('/pair',response_class=HTMLResponse)
def pair(code:str=''):return HTMLResponse(f"<h1>135er GrowCentral Cloud</h1><form method='post' action='/pair'><input name='code' value='{html.escape(code)}' required><input name='email' type='email' required><input name='password' type='password' minlength='12' required><button name='mode' value='login'>Anmelden & verbinden</button><button name='mode' value='register'>Konto erstellen & verbinden</button></form>")
@app.post('/pair',response_class=HTMLResponse)
def pair_submit(code:str=Form(...),email_:str=Form(alias='email'),password:str=Form(...),mode:str=Form(...)):
    uc=code.upper().strip();e=email(email_);pw(password);t=now()
    with engine.begin() as c:p=c.execute(text('SELECT * FROM pairings WHERE user_code=:u AND expires_at>:t AND consumed_at IS NULL'),{'u':uc,'t':t}).mappings().first()
    if not p:return HTMLResponse('<h2>Code ungültig oder abgelaufen.</h2>',status_code=400)
    if mode=='register':
        aid=str(uuid.uuid4())
        try:
            with engine.begin() as c:c.execute(text("INSERT INTO accounts(id,email,password_hash,created_at,status) VALUES(:i,:e,:p,:c,'active')"),{'i':aid,'e':e,'p':ph.hash(password),'c':t})
        except Exception:return HTMLResponse('<h2>Konto existiert bereits.</h2>',status_code=409)
    else:
        with engine.begin() as c:a=c.execute(text('SELECT id,password_hash,status FROM accounts WHERE email=:e'),{'e':e}).mappings().first()
        if not a:return HTMLResponse('<h2>Anmeldung fehlgeschlagen.</h2>',status_code=401)
        try:ph.verify(a['password_hash'],password)
        except VerifyMismatchError:return HTMLResponse('<h2>Anmeldung fehlgeschlagen.</h2>',status_code=401)
        aid=a['id']
    with engine.begin() as c:c.execute(text('UPDATE pairings SET approved_account_id=:a WHERE user_code=:u'),{'a':aid,'u':uc})
    return HTMLResponse('<h2>✓ Gerät bestätigt.</h2>')
PY
chown root:root "$APP_DIR/app.py";chmod 0644 "$APP_DIR/app.py"; }

write_systemd(){ cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=135er GrowCentral Cloud V4
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
EnvironmentFile=$ENV_FILE
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn app:app --host 127.0.0.1 --port $APP_PORT --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
UMask=0077
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload;systemctl enable "$SERVICE" >/dev/null; }

configure_plesk(){ local sub vhost_dir vhost backup="";sub="${CLOUD_HOST%.$ROOT_DOMAIN}";plesk bin subdomain --info "$CLOUD_HOST" >/dev/null 2>&1 || plesk bin subdomain --create "$sub" -domain "$ROOT_DOMAIN" -php false -ssi false -cgi false -fastcgi false -ssl true;vhost_dir="/var/www/vhosts/system/$CLOUD_HOST/conf";vhost="$vhost_dir/vhost_nginx.conf";[[ -d "$vhost_dir" ]]||die "Plesk-vHost-Verzeichnis fehlt.";if [[ -f "$vhost" ]];then backup="$BACKUP_DIR/vhost_nginx.conf.$(date +%Y%m%d-%H%M%S)";cp -a "$vhost" "$backup";fi;cat > "$vhost" <<EOF
location ~ ^/.* {
 proxy_pass http://127.0.0.1:$APP_PORT;
 proxy_http_version 1.1;
 proxy_set_header Host \$host;
 proxy_set_header X-Real-IP \$remote_addr;
 proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
 proxy_set_header X-Forwarded-Proto \$scheme;
 proxy_set_header Upgrade \$http_upgrade;
 proxy_set_header Connection "upgrade";
 proxy_read_timeout 180s;
 proxy_send_timeout 180s;
 proxy_buffering off;
}
EOF
if ! plesk sbin httpdmng --reconfigure-domain "$CLOUD_HOST";then rollback_vhost "$vhost" "$backup";die "Plesk-Reconfigure fehlgeschlagen.";fi;if command -v nginx >/dev/null 2>&1 && ! nginx -t;then rollback_vhost "$vhost" "$backup";die "nginx-Test fehlgeschlagen.";fi;systemctl reload nginx 2>/dev/null||true; }

main(){ require_root;detect_platform;install_packages;prepare_user_dirs;if [[ -z "$APP_PORT" ]];then if [[ -f "$ENV_FILE" ]]&&grep -q '^APP_PORT=' "$ENV_FILE";then APP_PORT="$(grep '^APP_PORT=' "$ENV_FILE"|tail -1|cut -d= -f2)";else APP_PORT="$(choose_port)";fi;fi;configure_database;write_env;install_python_runtime;write_application;write_systemd;"$APP_DIR/venv/bin/python" -m py_compile "$APP_DIR/app.py";systemctl restart "$SERVICE";sleep 2;curl -fsS "http://127.0.0.1:$APP_PORT/health" >/dev/null||die "Healthcheck fehlgeschlagen.";configure_plesk;echo "135er GrowCentral Cloud V4: https://$CLOUD_HOST"; }
main "$@"
