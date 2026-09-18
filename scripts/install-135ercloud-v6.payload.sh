#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# 135er GrowCentral Cloud V6
# Official cloud: https://135ercloud.grow-central.de
#
# Goals:
# - Plesk-safe: does not replace Plesk nginx/Apache and does not modify grow-central.de
# - Isolated backend bound to 127.0.0.1 only
# - Accounts can own multiple GrowCentral Pis
# - Pi GUID identifies an installation/device, but NEVER authenticates it
# - Device authentication uses Ed25519 public-key signatures
# - Short-lived device pairing code (10 min)
# - Short-lived access sessions + rotating refresh tokens
# - WebSocket device tunnel and remote relay
# - Nonce/replay protection for device WebSocket authentication
# - Automatic DB selection: dedicated PostgreSQL if a local PostgreSQL service
#   is already active, otherwise SQLite/WAL
# - Automatic backups and Plesk/nginx rollback
#
# This is a production-oriented bootstrap, not a replacement for normal server
# administration. DNS and a valid TLS certificate must exist for public use.
# ==============================================================================

ROOT_DOMAIN="${ROOT_DOMAIN:-grow-central.de}"
CLOUD_HOST="${CLOUD_HOST:-135ercloud.grow-central.de}"
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
APT_REPO_HOST="${APT_REPO_HOST:-repo.grow-central.de}"
APT_REPO_URL="${APT_REPO_URL:-https://${APT_REPO_HOST}/apt}"
APT_REPO_KEY_URL="${APT_REPO_KEY_URL:-${APT_REPO_URL}/growcentral-archive-keyring.gpg}"
APT_KEYRING="/usr/share/keyrings/135er-growcentral-archive-keyring.gpg"
APT_SOURCE="/etc/apt/sources.list.d/135er-growcentral.sources"
PACKAGE_MODE=0
[[ "${1:-}" == "--package-mode" ]] && PACKAGE_MODE=1

log(){ printf '\033[1;36m[GrowCentral]\033[0m %s\n' "$*"; }
ok(){ printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[FEHLER]\033[0m %s\n' "$*" >&2; exit 1; }

SETUP_STEPS_TOTAL=15
SETUP_STEP=0
SETUP_FAILED=0
SETUP_WARNINGS=0

step_begin(){
  SETUP_STEP=$((SETUP_STEP+1))
  printf '\n\033[1;37m[%02d/%02d]\033[0m \033[1;36m%s\033[0m\n' "$SETUP_STEP" "$SETUP_STEPS_TOTAL" "$*"
}
step_ok(){ printf '       \033[1;32m✓ OK\033[0m      %s\n' "$*"; }
step_warn(){ SETUP_WARNINGS=$((SETUP_WARNINGS+1)); printf '       \033[1;33m! WARN\033[0m    %s\n' "$*"; }
step_fail(){ SETUP_FAILED=1; printf '       \033[1;31m✗ FAILED\033[0m  %s\n' "$*" >&2; }

final_status(){
  echo
  echo "=============================================================================="
  echo "  135er GrowCentral Cloud V6 - SETUP STATUS"
  echo "=============================================================================="
  printf "  Cloud               : https://%s\n" "$CLOUD_HOST"
  printf "  APT-Repository      : %s\n" "$APT_REPO_URL"
  printf "  Backend             : 127.0.0.1:%s\n" "${APP_PORT:-unbekannt}"
  printf "  Service             : %s\n" "$SERVICE"
  printf "  Datenbank           : %s\n" "${DB_KIND:-unbekannt}"
  printf "  Warnungen           : %s\n" "$SETUP_WARNINGS"
  echo "------------------------------------------------------------------------------"
  if [[ "$SETUP_FAILED" -ne 0 ]]; then
    printf "  GESAMTSTATUS         : \033[1;31mFAILED\033[0m\n"
    echo "=============================================================================="
    return 1
  elif [[ "$SETUP_WARNINGS" -gt 0 ]]; then
    printf "  GESAMTSTATUS         : \033[1;33mOK MIT WARNUNGEN\033[0m\n"
    echo "=============================================================================="
    return 0
  else
    printf "  GESAMTSTATUS         : \033[1;32mOK\033[0m\n"
    echo "=============================================================================="
    return 0
  fi
}

rollback_vhost() {
  local vhost="${1:-}" backup="${2:-}"
  [[ -n "$vhost" ]] || return 0
  if [[ -n "$backup" && -f "$backup" ]]; then
    cp -a "$backup" "$vhost"
  else
    rm -f "$vhost"
  fi
  plesk sbin httpdmng --reconfigure-domain "$CLOUD_HOST" >/dev/null 2>&1 || true
}

on_error() {
  local rc=$?
  warn "Installer wurde mit Fehlercode $rc beendet."
  warn "Bestehende Website $ROOT_DOMAIN wurde nicht als Ziel-vHost verändert."
  exit "$rc"
}
trap on_error ERR

require_root() {
  [[ "$EUID" -eq 0 ]] || die "Bitte als root ausführen."
}

detect_platform() {
  [[ -r /etc/os-release ]] || die "/etc/os-release fehlt."
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${ID:-}" in
    debian|ubuntu) ;;
    *) die "Freigegeben für Debian/Ubuntu mit Plesk. Erkannt: ${PRETTY_NAME:-unbekannt}" ;;
  esac
  command -v plesk >/dev/null 2>&1 || die "Plesk nicht gefunden."
  plesk bin domain --info "$ROOT_DOMAIN" >/dev/null 2>&1 \
    || die "Plesk-Domain $ROOT_DOMAIN ist nicht vorhanden."
  command -v ss >/dev/null 2>&1 || true
}

install_packages() {
  if [[ "$PACKAGE_MODE" -eq 1 ]]; then
    log "APT-Paketmodus: Systemabhängigkeiten wurden über Depends: installiert."
    return 0
  fi
  log "Installiere/aktualisiere benötigte Systempakete ..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y --no-install-recommends \
    ca-certificates curl wget openssl openssh-server sqlite3 \
    python3 python3-venv python3-pip iproute2 util-linux gnupg
}

choose_port() {
  if [[ -n "$APP_PORT" ]]; then
    case "$APP_PORT" in
      80|443|8443|8880) die "APP_PORT=$APP_PORT kollidiert mit Plesk/Webserver."; ;;
    esac
    echo "$APP_PORT"
    return
  fi
  local p
  for p in 18765 18766 18767 18768 18769 18770 18771 18772; do
    if ! ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(:|\])${p}$"; then
      echo "$p"; return
    fi
  done
  die "Kein freier interner GrowCentral-Port gefunden."
}

prepare_user_dirs() {
  if ! id "$APP_USER" >/dev/null 2>&1; then
    useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
  fi
  install -d -m 0755 -o root -g root "$APP_DIR"
  install -d -m 0750 -o "$APP_USER" -g "$APP_USER" "$DATA_DIR"
  install -d -m 0750 -o root -g "$APP_USER" "$CONF_DIR"
  install -d -m 0700 -o root -g root "$BACKUP_DIR"
}

configure_database() {
  DB_KIND="sqlite"
  DATABASE_URL="sqlite:////${DATA_DIR#/}/cloud.sqlite3"

  # Use PostgreSQL only when it ALREADY exists locally and is active.
  # We do not install/replace Plesk's database stack.
  if id postgres >/dev/null 2>&1 && command -v psql >/dev/null 2>&1; then
    if systemctl is-active --quiet postgresql 2>/dev/null || \
       pgrep -x postgres >/dev/null 2>&1; then
      log "Vorhandenes PostgreSQL erkannt; erstelle dedizierte GrowCentral-DB."
      local pgpass
      pgpass="$(openssl rand -hex 32)"

      if runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='growcentral_cloud'" | grep -q 1; then
        runuser -u postgres -- psql -v ON_ERROR_STOP=1 \
          -c "ALTER ROLE growcentral_cloud WITH LOGIN PASSWORD '${pgpass}';" >/dev/null
      else
        runuser -u postgres -- psql -v ON_ERROR_STOP=1 \
          -c "CREATE ROLE growcentral_cloud WITH LOGIN PASSWORD '${pgpass}';" >/dev/null
      fi

      if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='growcentral_cloud'" | grep -q 1; then
        runuser -u postgres -- createdb -O growcentral_cloud growcentral_cloud
      else
        runuser -u postgres -- psql -v ON_ERROR_STOP=1 \
          -c "ALTER DATABASE growcentral_cloud OWNER TO growcentral_cloud;" >/dev/null
      fi

      DB_KIND="postgresql"
      DATABASE_URL="postgresql+psycopg://growcentral_cloud:${pgpass}@127.0.0.1:5432/growcentral_cloud"
      ok "Dedizierte PostgreSQL-Datenbank aktiv."
    fi
  fi

  if [[ "$DB_KIND" == "sqlite" ]]; then
    ok "PostgreSQL nicht aktiv; verwende isoliertes SQLite mit WAL."
  fi
}

write_env() {
  local server_secret cookie_secret
  server_secret="$(openssl rand -hex 32)"
  cookie_secret="$(openssl rand -hex 32)"

  # Preserve secrets on reinstall, but update URL/port/DB config.
  if [[ -f "$ENV_FILE" ]]; then
    server_secret="$(grep '^SERVER_SECRET=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
    cookie_secret="$(grep '^COOKIE_SECRET=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
    [[ ${#server_secret} -ge 32 ]] || server_secret="$(openssl rand -hex 32)"
    [[ ${#cookie_secret} -ge 32 ]] || cookie_secret="$(openssl rand -hex 32)"
    cp -a "$ENV_FILE" "$BACKUP_DIR/cloud.env.$(date +%Y%m%d-%H%M%S)"
  fi

  umask 077
  cat > "$ENV_FILE" <<EOF
APP_PORT=$APP_PORT
PUBLIC_URL=https://$CLOUD_HOST
DATABASE_URL=$DATABASE_URL
SERVER_SECRET=$server_secret
COOKIE_SECRET=$cookie_secret
ACCESS_TTL_SECONDS=900
REFRESH_TTL_SECONDS=2592000
PAIR_TTL_SECONDS=$PAIR_TTL
EOF
  chown root:"$APP_USER" "$ENV_FILE"
  chmod 0640 "$ENV_FILE"
  # Secrets need 077; runtime files must remain traversable by the service user.
  umask 022
}

install_python_runtime() {
  log "Erzeuge isolierte Python-Laufzeit ..."
  python3 -m venv "$APP_DIR/venv"
  "$APP_DIR/venv/bin/pip" install --disable-pip-version-check --quiet --upgrade pip
  "$APP_DIR/venv/bin/pip" install --disable-pip-version-check --quiet \
    "fastapi>=0.116,<1" \
    "uvicorn[standard]>=0.35,<1" \
    "sqlalchemy>=2.0,<3" \
    "psycopg[binary]>=3.2,<4" \
    "argon2-cffi>=23.1,<26" \
    "cryptography>=45,<47" \
    "python-multipart>=0.0.20,<1"

  chown -R root:"$APP_USER" "$APP_DIR/venv"
  chmod -R g+rX "$APP_DIR/venv"
}

write_application() {
  log "Installiere Cloud-API, Account-Pairing und WSS-Relay ..."
  cat > "$APP_DIR/app.py" <<'PY'
import asyncio
import base64
import hashlib
import html
import json
import os
import re
import secrets
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import FastAPI, Form, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text

PUBLIC_URL = os.environ["PUBLIC_URL"].rstrip("/")
DATABASE_URL = os.environ["DATABASE_URL"]
ACCESS_TTL = int(os.environ.get("ACCESS_TTL_SECONDS", "900"))
REFRESH_TTL = int(os.environ.get("REFRESH_TTL_SECONDS", "2592000"))
PAIR_TTL = int(os.environ.get("PAIR_TTL_SECONDS", "600"))
MAINTENANCE_SPOOL = Path(os.environ.get("MAINTENANCE_SPOOL_DIR", "/var/lib/135er-growcentral-cloud/maintenance/spool"))
MAINTENANCE_RESULTS = Path(os.environ.get("MAINTENANCE_RESULT_DIR", "/var/lib/135er-growcentral-cloud/maintenance/results"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

app = FastAPI(
    title="135er GrowCentral Cloud",
    version="6.1",
    docs_url=None,
    redoc_url=None,
)

# In-memory live tunnel state. Persistent identity/auth state stays in DB.
device_sockets: dict[str, WebSocket] = {}
client_sockets: dict[str, set[WebSocket]] = defaultdict(set)
socket_lock = asyncio.Lock()
maintenance_attempts: dict[str, list[int]] = defaultdict(list)


def now() -> int:
    return int(time.time())


def sha256s(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def token(bits: int = 256) -> str:
    return secrets.token_urlsafe(bits // 8)


def bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    return authorization[7:].strip()


def init_db():
    schema = [
        """CREATE TABLE IF NOT EXISTS accounts(
             id VARCHAR(36) PRIMARY KEY,
             email VARCHAR(320) NOT NULL UNIQUE,
             password_hash TEXT NOT NULL,
             created_at BIGINT NOT NULL,
             status VARCHAR(20) NOT NULL DEFAULT 'active'
           )""",
        """CREATE TABLE IF NOT EXISTS devices(
             id VARCHAR(36) PRIMARY KEY,
             account_id VARCHAR(36),
             hardware_guid VARCHAR(255) NOT NULL,
             public_key TEXT NOT NULL,
             name VARCHAR(120) NOT NULL,
             created_at BIGINT NOT NULL,
             last_seen BIGINT,
             revoked_at BIGINT,
             UNIQUE(hardware_guid, public_key)
           )""",
        """CREATE TABLE IF NOT EXISTS pairings(
             device_code_hash VARCHAR(64) PRIMARY KEY,
             user_code VARCHAR(20) NOT NULL UNIQUE,
             hardware_guid VARCHAR(255) NOT NULL,
             public_key TEXT NOT NULL,
             name VARCHAR(120) NOT NULL,
             created_at BIGINT NOT NULL,
             expires_at BIGINT NOT NULL,
             approved_account_id VARCHAR(36),
             consumed_at BIGINT
           )""",
        """CREATE TABLE IF NOT EXISTS access_sessions(
             token_hash VARCHAR(64) PRIMARY KEY,
             account_id VARCHAR(36) NOT NULL,
             created_at BIGINT NOT NULL,
             expires_at BIGINT NOT NULL,
             revoked_at BIGINT
           )""",
        """CREATE TABLE IF NOT EXISTS refresh_sessions(
             token_hash VARCHAR(64) PRIMARY KEY,
             account_id VARCHAR(36) NOT NULL,
             family_id VARCHAR(36) NOT NULL,
             created_at BIGINT NOT NULL,
             expires_at BIGINT NOT NULL,
             rotated_at BIGINT,
             revoked_at BIGINT
           )""",
        """CREATE TABLE IF NOT EXISTS device_nonces(
             nonce_hash VARCHAR(64) PRIMARY KEY,
             device_id VARCHAR(36) NOT NULL,
             created_at BIGINT NOT NULL,
             expires_at BIGINT NOT NULL,
             used_at BIGINT
           )""",
    ]
    with engine.begin() as con:
        for stmt in schema:
            con.execute(text(stmt))


init_db()


def account_from_access(raw: str) -> str:
    t = now()
    with engine.begin() as con:
        row = con.execute(
            text("""SELECT account_id FROM access_sessions
                    WHERE token_hash=:h AND expires_at>:t AND revoked_at IS NULL"""),
            {"h": sha256s(raw), "t": t},
        ).mappings().first()
    if not row:
        raise HTTPException(401, "invalid or expired access token")
    return row["account_id"]


def issue_sessions(account_id: str, family_id: Optional[str] = None):
    t = now()
    access = token(256)
    refresh = token(384)
    fam = family_id or str(uuid.uuid4())
    with engine.begin() as con:
        con.execute(
            text("""INSERT INTO access_sessions(token_hash,account_id,created_at,expires_at)
                    VALUES(:h,:a,:c,:e)"""),
            {"h": sha256s(access), "a": account_id, "c": t, "e": t + ACCESS_TTL},
        )
        con.execute(
            text("""INSERT INTO refresh_sessions(token_hash,account_id,family_id,created_at,expires_at)
                    VALUES(:h,:a,:f,:c,:e)"""),
            {"h": sha256s(refresh), "a": account_id, "f": fam, "c": t, "e": t + REFRESH_TTL},
        )
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": ACCESS_TTL,
        "refresh_token": refresh,
        "refresh_expires_in": REFRESH_TTL,
    }


def valid_email(email: str) -> str:
    e = email.strip().lower()
    if len(e) > 320 or "@" not in e or e.startswith("@") or e.endswith("@"):
        raise HTTPException(400, "invalid email")
    return e


def password_ok(password: str):
    if len(password) < 12:
        raise HTTPException(400, "password must have at least 12 characters")
    if len(password) > 512:
        raise HTTPException(400, "password too long")


def get_device_for_account(device_id: str, account_id: str):
    with engine.begin() as con:
        row = con.execute(
            text("""SELECT id,name,hardware_guid,last_seen,revoked_at
                    FROM devices WHERE id=:d AND account_id=:a"""),
            {"d": device_id, "a": account_id},
        ).mappings().first()
    if not row or row["revoked_at"] is not None:
        raise HTTPException(404, "device not found")
    return row


class RegisterBody(BaseModel):
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class PairStart(BaseModel):
    hardware_guid: str
    public_key: str
    name: str = "GrowCentral"


class PairPoll(BaseModel):
    device_code: str


class ChallengeBody(BaseModel):
    device_id: str


class MaintenanceEnrollBody(BaseModel):
    activation_code: str
    public_key: str
    hostname: str


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    if PUBLIC_URL.startswith("https://"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "135er-growcentral-cloud",
        "version": 6,
        "time": now(),
        "online_devices": len(device_sockets),
    }


@app.get("/.well-known/growcentral-cloud")
def discovery():
    return {
        "product": "135er-GrowCentral",
        "protocol_version": 2,
        "cloud_version": 6,
        "official": PUBLIC_URL == "https://135ercloud.grow-central.de",
        "public_url": PUBLIC_URL,
        "requires_https": True,
        "device_identity": "ed25519",
        "account_register_endpoint": PUBLIC_URL + "/api/v2/account/register",
        "account_login_endpoint": PUBLIC_URL + "/api/v2/account/login",
        "device_authorization_endpoint": PUBLIC_URL + "/api/v2/device/authorize",
        "pairing_url": PUBLIC_URL + "/pair",
        "device_websocket": PUBLIC_URL.replace("https://", "wss://") + "/api/v2/device/connect",
        "remote_websocket": PUBLIC_URL.replace("https://", "wss://") + "/api/v2/remote/connect",
        "maintenance_enrollment_endpoint": PUBLIC_URL + "/api/v2/maintenance/enroll",
    }


@app.post("/api/v2/maintenance/enroll")
def maintenance_enroll(body: MaintenanceEnrollBody, request: Request):
    client = request.client.host if request.client else "unknown"
    cutoff = now() - 60
    maintenance_attempts[client] = [stamp for stamp in maintenance_attempts[client] if stamp > cutoff]
    if len(maintenance_attempts[client]) >= 5:
        raise HTTPException(429, "too many enrollment attempts")
    maintenance_attempts[client].append(now())
    if sum(1 for _ in MAINTENANCE_SPOOL.glob("*.json")) >= 100:
        raise HTTPException(503, "enrollment queue busy")
    code = body.activation_code.strip().upper()
    key = body.public_key.strip()
    hostname = body.hostname.strip()
    if not re.fullmatch(r"GC-[A-Z2-9]{6}-[A-Z2-9]{6}", code):
        raise HTTPException(422, "invalid activation request")
    if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]{40,120}(?: [^\r\n]{1,100})?", key):
        raise HTTPException(422, "invalid activation request")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,63}", hostname):
        raise HTTPException(422, "invalid activation request")
    request_id = str(uuid.uuid4())
    request_token = token(256)
    payload = {
        "request_id": request_id, "token_hash": sha256s(request_token),
        "activation_code": code, "public_key": key, "hostname": hostname,
        "created_at": now(),
    }
    MAINTENANCE_SPOOL.mkdir(parents=True, exist_ok=True)
    temporary = MAINTENANCE_SPOOL / (request_id + ".tmp")
    final = MAINTENANCE_SPOOL / (request_id + ".json")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, final)
    return {"status": "pending", "request_id": request_id, "request_token": request_token}


@app.get("/api/v2/maintenance/enroll/{request_id}")
def maintenance_enroll_status(request_id: str, authorization: Optional[str] = Header(None)):
    if not re.fullmatch(r"[0-9a-f-]{36}", request_id):
        raise HTTPException(404, "request not found")
    result = MAINTENANCE_RESULTS / (request_id + ".json")
    if not result.is_file():
        return {"status": "pending"}
    try:
        payload = json.loads(result.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(503, "result unavailable")
    if not secrets.compare_digest(payload.get("token_hash", ""), sha256s(bearer(authorization))):
        raise HTTPException(401, "invalid request token")
    return {key: value for key, value in payload.items() if key != "token_hash"}


@app.post("/api/v2/account/register")
def register(body: RegisterBody):
    email = valid_email(body.email)
    password_ok(body.password)
    account_id = str(uuid.uuid4())
    try:
        with engine.begin() as con:
            con.execute(
                text("""INSERT INTO accounts(id,email,password_hash,created_at,status)
                        VALUES(:i,:e,:p,:c,'active')"""),
                {"i": account_id, "e": email, "p": ph.hash(body.password), "c": now()},
            )
    except Exception:
        raise HTTPException(409, "account already exists")
    return issue_sessions(account_id)


@app.post("/api/v2/account/login")
def login(body: LoginBody):
    email = valid_email(body.email)
    with engine.begin() as con:
        row = con.execute(
            text("SELECT id,password_hash,status FROM accounts WHERE email=:e"),
            {"e": email},
        ).mappings().first()
    # Same generic error for unknown account and bad password.
    if not row or row["status"] != "active":
        raise HTTPException(401, "invalid credentials")
    try:
        ph.verify(row["password_hash"], body.password)
    except VerifyMismatchError:
        raise HTTPException(401, "invalid credentials")
    return issue_sessions(row["id"])


@app.post("/api/v2/account/refresh")
def refresh(body: RefreshBody):
    h = sha256s(body.refresh_token)
    t = now()
    with engine.begin() as con:
        row = con.execute(
            text("""SELECT account_id,family_id FROM refresh_sessions
                    WHERE token_hash=:h AND expires_at>:t
                    AND revoked_at IS NULL AND rotated_at IS NULL"""),
            {"h": h, "t": t},
        ).mappings().first()
        if not row:
            raise HTTPException(401, "invalid refresh token")
        con.execute(
            text("UPDATE refresh_sessions SET rotated_at=:t WHERE token_hash=:h"),
            {"t": t, "h": h},
        )
    return issue_sessions(row["account_id"], row["family_id"])


@app.get("/api/v2/account/devices")
def list_devices(authorization: Optional[str] = Header(default=None)):
    aid = account_from_access(bearer(authorization))
    with engine.begin() as con:
        rows = con.execute(
            text("""SELECT id,name,hardware_guid,created_at,last_seen,revoked_at
                    FROM devices WHERE account_id=:a ORDER BY created_at DESC"""),
            {"a": aid},
        ).mappings().all()
    return {
        "devices": [
            {
                **dict(r),
                "online": r["id"] in device_sockets and r["revoked_at"] is None,
            }
            for r in rows
        ]
    }


@app.post("/api/v2/device/authorize")
def device_authorize(body: PairStart):
    if len(body.hardware_guid.strip()) < 16 or len(body.hardware_guid) > 255:
        raise HTTPException(400, "invalid hardware GUID")
    if len(body.name.strip()) < 1 or len(body.name) > 120:
        raise HTTPException(400, "invalid device name")

    # Validate Ed25519 public key as raw 32 bytes in URL-safe/base64 form.
    try:
        raw = base64.urlsafe_b64decode(body.public_key + "=" * (-len(body.public_key) % 4))
        if len(raw) != 32:
            raise ValueError()
        Ed25519PublicKey.from_public_bytes(raw)
    except Exception:
        raise HTTPException(400, "invalid Ed25519 public key")

    device_code = token(384)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    user_code = "-".join(
        "".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2)
    )
    t = now()
    with engine.begin() as con:
        con.execute(
            text("""INSERT INTO pairings(
                    device_code_hash,user_code,hardware_guid,public_key,name,
                    created_at,expires_at,approved_account_id,consumed_at)
                    VALUES(:h,:u,:g,:p,:n,:c,:e,NULL,NULL)"""),
            {
                "h": sha256s(device_code), "u": user_code,
                "g": body.hardware_guid.strip(), "p": body.public_key,
                "n": body.name.strip(), "c": t, "e": t + PAIR_TTL
            },
        )
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": PUBLIC_URL + "/pair",
        "verification_uri_complete": PUBLIC_URL + "/pair?code=" + user_code,
        "expires_in": PAIR_TTL,
        "interval": 5,
    }


@app.post("/api/v2/device/pair-status")
def pair_status(body: PairPoll):
    t = now()
    h = sha256s(body.device_code)
    with engine.begin() as con:
        row = con.execute(
            text("SELECT * FROM pairings WHERE device_code_hash=:h"),
            {"h": h},
        ).mappings().first()
        if not row or row["expires_at"] < t:
            raise HTTPException(400, "expired_token")
        if not row["approved_account_id"]:
            return JSONResponse({"status": "authorization_pending"}, status_code=202)
        if row["consumed_at"]:
            raise HTTPException(400, "already_consumed")

        # Reuse an existing non-revoked identical identity if present.
        existing = con.execute(
            text("""SELECT id FROM devices
                    WHERE hardware_guid=:g AND public_key=:p AND revoked_at IS NULL"""),
            {"g": row["hardware_guid"], "p": row["public_key"]},
        ).mappings().first()

        if existing:
            device_id = existing["id"]
            con.execute(
                text("""UPDATE devices SET account_id=:a,name=:n WHERE id=:d"""),
                {"a": row["approved_account_id"], "n": row["name"], "d": device_id},
            )
        else:
            device_id = str(uuid.uuid4())
            con.execute(
                text("""INSERT INTO devices(
                        id,account_id,hardware_guid,public_key,name,created_at,last_seen,revoked_at)
                        VALUES(:d,:a,:g,:p,:n,:c,NULL,NULL)"""),
                {
                    "d": device_id, "a": row["approved_account_id"],
                    "g": row["hardware_guid"], "p": row["public_key"],
                    "n": row["name"], "c": t,
                },
            )
        con.execute(
            text("UPDATE pairings SET consumed_at=:t WHERE device_code_hash=:h"),
            {"t": t, "h": h},
        )
    return {"status": "approved", "device_id": device_id}


@app.get("/pair", response_class=HTMLResponse)
def pair_page(code: str = ""):
    code = html.escape(code.upper().strip())
    return HTMLResponse(f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>135er GrowCentral Cloud – Gerät verbinden</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:540px;margin:3rem auto;padding:0 1rem;background:#0e1116;color:#f3f5f7}}
.card{{background:#171c24;padding:1.4rem;border-radius:18px}}input,button{{width:100%;box-sizing:border-box;padding:.85rem;margin:.35rem 0;border-radius:10px;border:1px solid #394150}}
input{{background:#0e1116;color:#fff}}button{{background:#fff;color:#111;font-weight:700;cursor:pointer}}
small{{color:#aeb7c2}}code{{font-size:1.1rem}}</style></head>
<body><div class="card"><h1>135er GrowCentral Cloud</h1>
<p>GrowCentral-Gerät einem Konto zuordnen.</p>
<form method="post" action="/pair">
<label>Pairing-Code</label><input name="code" value="{code}" required maxlength="20" autocomplete="one-time-code">
<label>E-Mail</label><input type="email" name="email" required autocomplete="username">
<label>Passwort</label><input type="password" name="password" required minlength="12" autocomplete="current-password">
<button type="submit" name="mode" value="login">Anmelden & Gerät verbinden</button>
<button type="submit" name="mode" value="register">Neues Konto erstellen & verbinden</button>
</form>
<p><small>Der Code ist nur 10 Minuten gültig. Die Pi-GUID ist keine Authentifizierung;
das Gerät wird später kryptografisch über seinen Ed25519-Schlüssel geprüft.</small></p>
</div></body></html>""")


@app.post("/pair", response_class=HTMLResponse)
def pair_submit(
    code: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    mode: str = Form(...),
):
    ucode = code.upper().strip()
    email = valid_email(email)
    password_ok(password)
    t = now()

    with engine.begin() as con:
        pairing = con.execute(
            text("""SELECT * FROM pairings WHERE user_code=:u
                    AND expires_at>:t AND consumed_at IS NULL"""),
            {"u": ucode, "t": t},
        ).mappings().first()
    if not pairing:
        return HTMLResponse("<h2>Pairing-Code ungültig oder abgelaufen.</h2>", status_code=400)

    account_id = None
    if mode == "register":
        account_id = str(uuid.uuid4())
        try:
            with engine.begin() as con:
                con.execute(
                    text("""INSERT INTO accounts(id,email,password_hash,created_at,status)
                            VALUES(:i,:e,:p,:c,'active')"""),
                    {"i": account_id, "e": email, "p": ph.hash(password), "c": t},
                )
        except Exception:
            return HTMLResponse("<h2>Konto existiert bereits. Bitte anmelden.</h2>", status_code=409)
    else:
        with engine.begin() as con:
            account = con.execute(
                text("SELECT id,password_hash,status FROM accounts WHERE email=:e"),
                {"e": email},
            ).mappings().first()
        if not account or account["status"] != "active":
            return HTMLResponse("<h2>Anmeldung fehlgeschlagen.</h2>", status_code=401)
        try:
            ph.verify(account["password_hash"], password)
        except VerifyMismatchError:
            return HTMLResponse("<h2>Anmeldung fehlgeschlagen.</h2>", status_code=401)
        account_id = account["id"]

    with engine.begin() as con:
        con.execute(
            text("""UPDATE pairings SET approved_account_id=:a
                    WHERE user_code=:u AND expires_at>:t AND consumed_at IS NULL"""),
            {"a": account_id, "u": ucode, "t": t},
        )

    return HTMLResponse("""<!doctype html><meta charset="utf-8">
    <h2>✓ GrowCentral wurde bestätigt.</h2>
    <p>Du kannst dieses Fenster schließen. Der Pi schließt die Registrierung automatisch ab.</p>""")


@app.post("/api/v2/device/challenge")
def device_challenge(body: ChallengeBody):
    t = now()
    with engine.begin() as con:
        row = con.execute(
            text("""SELECT id FROM devices WHERE id=:d
                    AND account_id IS NOT NULL AND revoked_at IS NULL"""),
            {"d": body.device_id},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "device not found")
        nonce = token(256)
        con.execute(
            text("""INSERT INTO device_nonces(nonce_hash,device_id,created_at,expires_at,used_at)
                    VALUES(:h,:d,:c,:e,NULL)"""),
            {"h": sha256s(nonce), "d": body.device_id, "c": t, "e": t + 60},
        )
    return {"nonce": nonce, "expires_in": 60}


def verify_device_ws_auth(msg: dict):
    try:
        device_id = str(msg["device_id"])
        nonce = str(msg["nonce"])
        timestamp = int(msg["timestamp"])
        signature = str(msg["signature"])
    except Exception:
        return None

    t = now()
    if abs(t - timestamp) > 60:
        return None

    nh = sha256s(nonce)
    with engine.begin() as con:
        nr = con.execute(
            text("""SELECT device_id FROM device_nonces
                    WHERE nonce_hash=:h AND device_id=:d
                    AND expires_at>:t AND used_at IS NULL"""),
            {"h": nh, "d": device_id, "t": t},
        ).mappings().first()
        if not nr:
            return None

        dr = con.execute(
            text("""SELECT public_key,revoked_at FROM devices
                    WHERE id=:d AND account_id IS NOT NULL"""),
            {"d": device_id},
        ).mappings().first()
        if not dr or dr["revoked_at"] is not None:
            return None

        signed = f"GCLOUD2\n{device_id}\n{nonce}\n{timestamp}".encode("utf-8")
        try:
            pub_raw = base64.urlsafe_b64decode(dr["public_key"] + "=" * (-len(dr["public_key"]) % 4))
            sig_raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
            Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig_raw, signed)
        except Exception:
            return None

        # Atomic replay prevention: consume nonce exactly once.
        con.execute(
            text("UPDATE device_nonces SET used_at=:t WHERE nonce_hash=:h AND used_at IS NULL"),
            {"t": t, "h": nh},
        )
        con.execute(
            text("UPDATE devices SET last_seen=:t WHERE id=:d"),
            {"t": t, "d": device_id},
        )
    return device_id


async def broadcast_to_clients(device_id: str, payload: str):
    dead = []
    async with socket_lock:
        targets = list(client_sockets.get(device_id, set()))
    for ws in targets:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    if dead:
        async with socket_lock:
            for ws in dead:
                client_sockets[device_id].discard(ws)


@app.websocket("/api/v2/device/connect")
async def device_connect(ws: WebSocket):
    await ws.accept()
    device_id = None
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=10)
        msg = json.loads(raw)
        if msg.get("type") != "auth":
            await ws.close(code=4401)
            return
        device_id = verify_device_ws_auth(msg)
        if not device_id:
            await ws.close(code=4403)
            return

        async with socket_lock:
            old = device_sockets.get(device_id)
            device_sockets[device_id] = ws
        if old and old is not ws:
            try:
                await old.close(code=4000)
            except Exception:
                pass

        await ws.send_json({"type": "auth_ok", "device_id": device_id})

        while True:
            payload = await ws.receive_text()
            with engine.begin() as con:
                con.execute(
                    text("UPDATE devices SET last_seen=:t WHERE id=:d"),
                    {"t": now(), "d": device_id},
                )
            await broadcast_to_clients(device_id, payload)

    except (WebSocketDisconnect, asyncio.TimeoutError, json.JSONDecodeError):
        pass
    finally:
        if device_id:
            async with socket_lock:
                if device_sockets.get(device_id) is ws:
                    device_sockets.pop(device_id, None)


@app.websocket("/api/v2/remote/connect")
async def remote_connect(ws: WebSocket):
    await ws.accept()
    device_id = None
    try:
        # Token is deliberately sent as the first WebSocket message,
        # not in the URL/query string.
        raw = await asyncio.wait_for(ws.receive_text(), timeout=10)
        msg = json.loads(raw)
        if msg.get("type") != "auth":
            await ws.close(code=4401)
            return
        try:
            account_id = account_from_access(str(msg.get("access_token", "")))
        except HTTPException:
            await ws.close(code=4401)
            return

        device_id = str(msg.get("device_id", ""))
        try:
            get_device_for_account(device_id, account_id)
        except HTTPException:
            await ws.close(code=4403)
            return

        async with socket_lock:
            client_sockets[device_id].add(ws)

        await ws.send_json({
            "type": "auth_ok",
            "device_id": device_id,
            "device_online": device_id in device_sockets,
        })

        while True:
            payload = await ws.receive_text()
            # Require JSON and cap semantic command envelope.
            if len(payload) > 262144:
                await ws.close(code=4400)
                return
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "error": "json_required"})
                continue
            if not isinstance(data, dict) or "type" not in data:
                await ws.send_json({"type": "error", "error": "invalid_envelope"})
                continue

            async with socket_lock:
                dws = device_sockets.get(device_id)
            if not dws:
                await ws.send_json({"type": "error", "error": "device_offline"})
                continue
            try:
                await dws.send_text(payload)
            except Exception:
                await ws.send_json({"type": "error", "error": "device_transport_failed"})

    except (WebSocketDisconnect, asyncio.TimeoutError, json.JSONDecodeError):
        pass
    finally:
        if device_id:
            async with socket_lock:
                client_sockets[device_id].discard(ws)


@app.delete("/api/v2/account/devices/{device_id}")
async def revoke_device(device_id: str, authorization: Optional[str] = Header(default=None)):
    aid = account_from_access(bearer(authorization))
    get_device_for_account(device_id, aid)
    with engine.begin() as con:
        con.execute(
            text("UPDATE devices SET revoked_at=:t WHERE id=:d AND account_id=:a"),
            {"t": now(), "d": device_id, "a": aid},
        )
    async with socket_lock:
        dws = device_sockets.pop(device_id, None)
    if dws:
        try:
            await dws.close(code=4403)
        except Exception:
            pass
    return {"ok": True, "device_id": device_id, "revoked": True}
PY

  chown root:root "$APP_DIR/app.py"
  chmod 0644 "$APP_DIR/app.py"
}

write_maintenance_enrollment() {
  local tunnel_user="growcentral-tunnel" maintenance_dir="$DATA_DIR/maintenance"
  id "$tunnel_user" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$tunnel_user"
  usermod --password "$(openssl passwd -6 "$(openssl rand -hex 32)")" "$tunnel_user"
  install -d -o "$APP_USER" -g "$APP_USER" -m 0700 "$maintenance_dir/spool"
  install -d -o root -g "$APP_USER" -m 0750 "$maintenance_dir/results"
  install -d -o root -g root -m 0700 "$CONF_DIR/maintenance-codes"
  install -d -o "$tunnel_user" -g "$tunnel_user" -m 0700 "/home/$tunnel_user/.ssh"
  touch "/home/$tunnel_user/.ssh/authorized_keys"
  chown "$tunnel_user:$tunnel_user" "/home/$tunnel_user/.ssh/authorized_keys"
  chmod 0600 "/home/$tunnel_user/.ssh/authorized_keys"

  cat > /usr/local/sbin/growcentral-maintenance-code <<'PY'
#!/usr/bin/env python3
import fcntl, hashlib, json, os, secrets, socket, sys, time
from pathlib import Path
STORE = Path("/etc/135er-growcentral-cloud/maintenance-codes/codes.json")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
def load(handle):
    handle.seek(0)
    try: return json.load(handle)
    except (ValueError, json.JSONDecodeError): return {}
def main():
    if os.geteuid() != 0: raise SystemExit("Bitte als root ausführen.")
    STORE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(STORE, "a+", encoding="utf-8") as handle:
        os.chmod(STORE, 0o600); fcntl.flock(handle, fcntl.LOCK_EX); records = load(handle)
        now = int(time.time()); records = {k:v for k,v in records.items() if not v.get("used") and v.get("expires_at",0) > now}
        used_ports = {v["port"] for v in records.values()}
        port = int(sys.argv[2]) if len(sys.argv) > 2 else next((p for p in range(22000,23000) if p not in used_ports), 0)
        if len(sys.argv) < 2 or sys.argv[1] != "create" or not 22000 <= port < 23000: raise SystemExit("Verwendung: growcentral-maintenance-code create [PORT]")
        code = "GC-" + "".join(secrets.choice(ALPHABET) for _ in range(6)) + "-" + "".join(secrets.choice(ALPHABET) for _ in range(6))
        records[hashlib.sha256(code.encode()).hexdigest()] = {"port":port,"expires_at":now+86400,"used":False}
        handle.seek(0); handle.truncate(); json.dump(records, handle); handle.flush(); os.fsync(handle.fileno())
    print(code); print(f"Port: {port}\nGültig: 24 Stunden; nur einmal verwendbar.", file=sys.stderr)
if __name__ == "__main__": main()
PY

  cat > /usr/local/sbin/growcentral-maintenance-worker <<'PY'
#!/usr/bin/env python3
import fcntl, hashlib, json, os, re, subprocess, time
from pathlib import Path
BASE=Path("/var/lib/135er-growcentral-cloud/maintenance"); SPOOL=BASE/"spool"; RESULTS=BASE/"results"
STORE=Path("/etc/135er-growcentral-cloud/maintenance-codes/codes.json")
AUTH=Path("/home/growcentral-tunnel/.ssh/authorized_keys")
HOST=os.environ.get("MAINTENANCE_SSH_HOST","87.106.119.187")
def result(req, status, **extra):
    payload={"status":status,"token_hash":req.get("token_hash","")}; payload.update(extra)
    tmp=RESULTS/(req["request_id"]+".tmp"); final=RESULTS/(req["request_id"]+".json")
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as h: json.dump(payload,h); h.flush(); os.fsync(h.fileno())
    os.chown(tmp, 0, int(os.environ["APP_GID"])); os.chmod(tmp,0o640); os.replace(tmp,final)
def main():
  RESULTS.mkdir(parents=True,exist_ok=True)
  for source in sorted(SPOOL.glob("*.json")):
    claimed=source.with_suffix(".processing")
    try: source.rename(claimed)
    except OSError: continue
    req={}
    try:
      req=json.loads(claimed.read_text()); code=req.pop("activation_code","").upper(); key=req.get("public_key","").strip()
      if not re.fullmatch(r"[0-9a-f-]{36}",req.get("request_id","")) or not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]{40,120}(?: [^\r\n]{1,100})?",key): raise ValueError()
      digest=hashlib.sha256(code.encode()).hexdigest()
      with open(STORE,"r+",encoding="utf-8") as h:
        fcntl.flock(h,fcntl.LOCK_EX); records=json.load(h); record=records.get(digest)
        if not record or record.get("used") or record.get("expires_at",0)<int(time.time()): raise ValueError()
        record["used"]=True; record["used_at"]=int(time.time()); h.seek(0);h.truncate();json.dump(records,h);h.flush();os.fsync(h.fileno())
      port=int(record["port"])
      line=f'restrict,port-forwarding,permitlisten="127.0.0.1:{port}" {key}\n'
      with open(AUTH,"a",encoding="utf-8") as h: fcntl.flock(h,fcntl.LOCK_EX); h.write(line); h.flush(); os.fsync(h.fileno())
      fingerprint=subprocess.check_output(["ssh-keygen","-E","sha256","-lf","/etc/ssh/ssh_host_ed25519_key.pub"],text=True).split()[1]
      result(req,"approved",host=HOST,user="growcentral-tunnel",port=port,fingerprint=fingerprint)
    except Exception:
      if req.get("request_id") and req.get("token_hash"): result(req,"rejected")
    finally: claimed.unlink(missing_ok=True)
if __name__ == "__main__": main()
PY
  chmod 0755 /usr/local/sbin/growcentral-maintenance-code /usr/local/sbin/growcentral-maintenance-worker

  cat > /etc/systemd/system/growcentral-maintenance-enrollment.service <<EOF
[Unit]
Description=Process one-time GrowCentral maintenance enrollment
[Service]
Type=oneshot
Environment=APP_UID=$(id -u "$APP_USER")
Environment=APP_GID=$(id -g "$APP_USER")
Environment=MAINTENANCE_SSH_HOST=${MAINTENANCE_SSH_HOST:-87.106.119.187}
ExecStart=/usr/local/sbin/growcentral-maintenance-worker
PrivateTmp=true
NoNewPrivileges=true
EOF
  cat > /etc/systemd/system/growcentral-maintenance-enrollment.path <<EOF
[Unit]
Description=Watch GrowCentral maintenance enrollment queue
[Path]
PathExistsGlob=$maintenance_dir/spool/*.json
Unit=growcentral-maintenance-enrollment.service
[Install]
WantedBy=multi-user.target
EOF
  install -d -m 0755 /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/90-growcentral-tunnel.conf <<'EOF'
Match User growcentral-tunnel
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    AuthenticationMethods publickey
    AllowTcpForwarding remote
    GatewayPorts no
    X11Forwarding no
    AllowAgentForwarding no
    PermitTTY no
EOF
  sshd -t
  systemctl daemon-reload
  systemctl enable --now growcentral-maintenance-enrollment.path
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
}

write_systemd() {
  cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=135er GrowCentral Cloud V6
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
EnvironmentFile=$ENV_FILE
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port $APP_PORT --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
TimeoutStopSec=20

NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectKernelLogs=true
ProtectControlGroups=true
ProtectClock=true
RestrictSUIDSGID=true
LockPersonality=true
RestrictRealtime=true
SystemCallArchitectures=native
UMask=0077

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable "$SERVICE" >/dev/null
}


get_admin_email() {
  local email=""
  email="$(plesk bin admin --info 2>/dev/null | awk -F': *' '/^Email:/ {print $2; exit}' || true)"
  [[ -n "$email" ]] || email="$(plesk db -Ne "SELECT email FROM clients WHERE login='admin' LIMIT 1" 2>/dev/null || true)"
  echo "$email"
}

tls_valid() {
  echo | openssl s_client -connect "${CLOUD_HOST}:443" -servername "${CLOUD_HOST}" 2>/dev/null \
    | openssl x509 -noout -checkend 86400 >/dev/null 2>&1 \
  && echo | openssl s_client -connect "${CLOUD_HOST}:443" -servername "${CLOUD_HOST}" 2>/dev/null \
    | openssl x509 -noout -ext subjectAltName 2>/dev/null | grep -Fq "DNS:${CLOUD_HOST}"
}

ensure_tls_certificate() {
  if tls_valid; then
    return 0
  fi

  local email cert_name
  email="$(get_admin_email)"
  [[ -n "$email" ]] || return 2

  if ! plesk bin extension --exec letsencrypt cli.php -d "$CLOUD_HOST" -m "$email"; then
    return 2
  fi

  cert_name="Lets Encrypt ${CLOUD_HOST}"
  if plesk bin certificate --list -domain "$CLOUD_HOST" 2>/dev/null | grep -Fq "$cert_name"; then
    plesk bin site -u "$CLOUD_HOST" -certificate-name "$cert_name" >/dev/null 2>&1 || true
  fi
  plesk sbin httpdmng --reconfigure-domain "$CLOUD_HOST" >/dev/null 2>&1 || true
  systemctl reload nginx >/dev/null 2>&1 || true
  sleep 1
  tls_valid
}

configure_apt_repo_client() {
  # The official repo is optional during first bootstrap; failure is a warning.
  if ! curl -fsS --connect-timeout 8 "$APT_REPO_KEY_URL" -o "${APT_KEYRING}.tmp"; then
    rm -f "${APT_KEYRING}.tmp"
    return 2
  fi
  install -m 0644 "${APT_KEYRING}.tmp" "$APT_KEYRING"
  rm -f "${APT_KEYRING}.tmp"

  cat > "$APT_SOURCE" <<EOF
Types: deb
URIs: $APT_REPO_URL
Suites: stable
Components: main
Signed-By: $APT_KEYRING
EOF

  if [[ "$PACKAGE_MODE" -eq 0 ]]; then
    apt-get update -y >/dev/null
  fi
  return 0
}

configure_plesk() {
  log "Konfiguriere ausschließlich die Plesk-Subdomain $CLOUD_HOST ..."
  local sub vhost_dir vhost backup=""
  sub="${CLOUD_HOST%.$ROOT_DOMAIN}"

  if [[ "$sub" == "$CLOUD_HOST" || -z "$sub" ]]; then
    die "CLOUD_HOST=$CLOUD_HOST ist keine Subdomain von ROOT_DOMAIN=$ROOT_DOMAIN."
  fi

  if ! plesk bin subdomain --info "$CLOUD_HOST" >/dev/null 2>&1; then
    plesk bin subdomain --create "$sub" \
      -domain "$ROOT_DOMAIN" -php false -ssi false -cgi false -fastcgi false -ssl true
  fi

  vhost_dir="/var/www/vhosts/system/$CLOUD_HOST/conf"
  vhost="$vhost_dir/vhost_nginx.conf"
  [[ -d "$vhost_dir" ]] || die "Plesk-vHost-Verzeichnis fehlt: $vhost_dir"

  if [[ -f "$vhost" ]]; then
    backup="$BACKUP_DIR/vhost_nginx.conf.$(date +%Y%m%d-%H%M%S)"
    cp -a "$vhost" "$backup"
  fi

  cat > "$vhost" <<EOF
# 135er GrowCentral Cloud V6 - Plesk-isolated reverse proxy
location ~ ^/.* {
    proxy_pass http://127.0.0.1:$APP_PORT;
    proxy_http_version 1.1;

    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;

    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_connect_timeout 15s;
    proxy_send_timeout 180s;
    proxy_read_timeout 180s;

    client_max_body_size 16m;
    proxy_buffering off;
}
EOF
  chmod 0644 "$vhost"

  if ! plesk sbin httpdmng --reconfigure-domain "$CLOUD_HOST"; then
    rollback_vhost "$vhost" "$backup"
    die "Plesk-Reconfigure fehlgeschlagen; vHost wurde zurückgerollt."
  fi

  if command -v nginx >/dev/null 2>&1 && ! nginx -t; then
    rollback_vhost "$vhost" "$backup"
    die "nginx-Konfiguration ungültig; vHost wurde zurückgerollt."
  fi

  systemctl reload nginx 2>/dev/null || true
}

start_and_smoke_test() {
  log "Starte Dienst und führe lokale Smoke-Checks aus ..."
  if ! runuser -u "$APP_USER" -- "$APP_DIR/venv/bin/python" -c 'import sys' >/dev/null 2>&1; then
    die "Runtime-Rechteprüfung fehlgeschlagen: $APP_USER kann das venv nicht ausführen."
  fi
  systemctl restart "$SERVICE"
  sleep 2

  if ! systemctl is-active --quiet "$SERVICE"; then
    journalctl -u "$SERVICE" -n 80 --no-pager || true
    die "GrowCentral Cloud Dienst ist nicht aktiv."
  fi

  curl -fsS "http://127.0.0.1:$APP_PORT/health" >/dev/null \
    || die "Health-Check fehlgeschlagen."
  curl -fsS "http://127.0.0.1:$APP_PORT/.well-known/growcentral-cloud" >/dev/null \
    || die "Discovery-Check fehlgeschlagen."

  ok "Lokale API- und Discovery-Smoke-Checks erfolgreich."
}

check_dns_tls() {
  local server_ip dns_ip
  server_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  dns_ip="$(getent ahostsv4 "$CLOUD_HOST" 2>/dev/null | awk 'NR==1{print $1}' || true)"

  if [[ -z "$dns_ip" ]]; then
    warn "DNS für $CLOUD_HOST ist noch nicht auflösbar."
  elif [[ -n "$server_ip" && "$dns_ip" != "$server_ip" ]]; then
    warn "DNS zeigt auf $dns_ip; erste lokale Server-IP ist $server_ip. Bitte prüfen."
  else
    ok "DNS-Auflösung sieht plausibel aus."
  fi

  if curl -fsS --connect-timeout 8 "https://$CLOUD_HOST/health" >/dev/null 2>&1; then
    ok "Öffentlicher HTTPS-Healthcheck erfolgreich."
  else
    warn "HTTPS ist noch nicht vollständig erreichbar. DNS + Plesk-Let's-Encrypt für $CLOUD_HOST prüfen."
  fi
}

print_summary() {
  cat <<EOF

==============================================================================
  135er GrowCentral Cloud V6 installiert
==============================================================================
  Bestehende Website : https://$ROOT_DOMAIN       (nicht ersetzt)
  Offizielle Cloud   : https://$CLOUD_HOST
  Discovery          : https://$CLOUD_HOST/.well-known/growcentral-cloud
  Pairing            : https://$CLOUD_HOST/pair
  Device WSS         : wss://$CLOUD_HOST/api/v2/device/connect
  Remote WSS         : wss://$CLOUD_HOST/api/v2/remote/connect
  Interner Backend   : 127.0.0.1:$APP_PORT
  Datenbank          : $DB_KIND
  Service            : $SERVICE

  Status:
    systemctl status $SERVICE

  Logs:
    journalctl -u $SERVICE -f

  Lokaler Healthcheck:
    curl http://127.0.0.1:$APP_PORT/health

  WICHTIG FÜR PRODUKTION:
    - DNS A/AAAA für $CLOUD_HOST muss auf diesen Server zeigen.
    - In Plesk ein gültiges TLS-Zertifikat für $CLOUD_HOST aktivieren.
    - Port 80/443 bleiben ausschließlich bei Plesk/nginx.
    - Auf dem Heimrouter des Pi ist KEINE Portfreigabe erforderlich.
==============================================================================

EOF
}

status_mode() {
  systemctl --no-pager --full status "$SERVICE" || true
  echo
  if [[ -f "$ENV_FILE" ]]; then
    local p
    p="$(grep '^APP_PORT=' "$ENV_FILE" | cut -d= -f2- || true)"
    [[ -z "$p" ]] || curl -fsS "http://127.0.0.1:$p/health" || true
    echo
  fi
}

main() {
  require_root

  if [[ "${1:-}" == "--status" ]]; then
    status_mode
    exit 0
  fi

  echo
  echo "=============================================================================="
  echo "  135er GrowCentral Cloud V6 - VISUELLER SETUP-ASSISTENT"
  echo "=============================================================================="
  echo "  Cloud        : https://$CLOUD_HOST"
  echo "  APT-Repo     : $APT_REPO_URL"
  echo "  Root-Domain  : $ROOT_DOMAIN"
  echo "  Plesk bleibt für HTTP/HTTPS zuständig; GrowCentral läuft nur auf localhost."
  echo "=============================================================================="

  step_begin "System und Plesk prüfen"
  if detect_platform; then step_ok "Debian/Ubuntu + Plesk + $ROOT_DOMAIN erkannt"; else
    step_fail "System-/Plesk-Prüfung fehlgeschlagen"; final_status || true; exit 1; fi

  step_begin "Abhängigkeiten vorbereiten"
  if install_packages; then step_ok "Systemabhängigkeiten verfügbar"; else
    step_fail "Abhängigkeiten konnten nicht installiert werden"; final_status || true; exit 1; fi

  step_begin "Dienstbenutzer und Verzeichnisse vorbereiten"
  if prepare_user_dirs; then step_ok "$APP_USER und Datenverzeichnisse vorbereitet"; else
    step_fail "Benutzer-/Verzeichnis-Setup fehlgeschlagen"; final_status || true; exit 1; fi

  if [[ -z "$APP_PORT" ]]; then
    if [[ -f "$ENV_FILE" ]] && grep -q '^APP_PORT=' "$ENV_FILE"; then
      APP_PORT="$(grep '^APP_PORT=' "$ENV_FILE" | tail -1 | cut -d= -f2)"
    else
      APP_PORT="$(choose_port)"
    fi
  fi

  step_begin "Datenbank erkennen und vorbereiten"
  if configure_database; then step_ok "Datenbankmodus: $DB_KIND"; else
    step_fail "Datenbank-Setup fehlgeschlagen"; final_status || true; exit 1; fi

  step_begin "Secrets und Cloud-Konfiguration schreiben"
  if write_env; then step_ok "Secrets geschützt; Runtime-umask korrekt zurückgesetzt"; else
    step_fail "Konfiguration konnte nicht geschrieben werden"; final_status || true; exit 1; fi

  step_begin "Python-Runtime und GrowCentral Cloud installieren"
  if install_python_runtime && write_application; then
    step_ok "Cloud-App installiert; venv für Service-Benutzer ausführbar"
  else
    step_fail "Runtime-/App-Installation fehlgeschlagen"; final_status || true; exit 1
  fi

  step_begin "Sichere Fernwartungs-Aktivierung vorbereiten"
  if write_maintenance_enrollment; then
    step_ok "Einmalcodes, Tunnel-Benutzer und Enrollment-Worker bereit"
  else
    step_fail "Fernwartungs-Enrollment konnte nicht eingerichtet werden"; final_status || true; exit 1
  fi

  step_begin "systemd und Python validieren"
  if write_systemd \
     && "$APP_DIR/venv/bin/python" -m py_compile "$APP_DIR/app.py" \
     && runuser -u "$APP_USER" -- sh -c "cd '$APP_DIR' && set -a && . '$ENV_FILE' && set +a && '$APP_DIR/venv/bin/python' -c 'import app'" >/dev/null 2>&1; then
    step_ok "Syntax, Import und Service-Rechte OK"
  else
    step_fail "Python-/systemd-Prüfung fehlgeschlagen"; final_status || true; exit 1
  fi

  step_begin "Backend starten und lokal prüfen"
  if start_and_smoke_test; then step_ok "Backend auf 127.0.0.1:$APP_PORT erreichbar"; else
    step_fail "Backend-Start/Healthcheck fehlgeschlagen"
    journalctl -u "$SERVICE" -n 80 --no-pager || true
    final_status || true; exit 1
  fi

  step_begin "Plesk-Subdomain und Reverse Proxy konfigurieren"
  if configure_plesk; then step_ok "$CLOUD_HOST -> 127.0.0.1:$APP_PORT"; else
    step_fail "Plesk/nginx-Konfiguration fehlgeschlagen; Rollback ausgeführt"; final_status || true; exit 1
  fi

  step_begin "DNS prüfen"
  DNS_IP="$(getent ahostsv4 "$CLOUD_HOST" 2>/dev/null | awk 'NR==1{print $1}' || true)"
  SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -n "$DNS_IP" && "$DNS_IP" == "$SERVER_IP" ]]; then
    step_ok "$CLOUD_HOST -> $DNS_IP"
  elif [[ -n "$DNS_IP" ]]; then
    step_warn "$CLOUD_HOST -> $DNS_IP; Server-IP: ${SERVER_IP:-unbekannt}"
  else
    step_warn "DNS für $CLOUD_HOST noch nicht auflösbar"
  fi

  step_begin "TLS / Let's Encrypt prüfen"
  if ensure_tls_certificate; then
    CERT_DATES="$(echo | openssl s_client -connect "${CLOUD_HOST}:443" -servername "${CLOUD_HOST}" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null | tr '
' ' ')"
    step_ok "Gültiges Zertifikat für $CLOUD_HOST ($CERT_DATES)"
  else
    step_warn "TLS konnte noch nicht vollständig automatisch bestätigt werden"
  fi

  step_begin "Öffentliche Cloud-Endpunkte prüfen"
  PUBLIC_HEALTH=0
  PUBLIC_DISCOVERY=0
  curl -fsS --connect-timeout 10 "https://$CLOUD_HOST/health" >/dev/null 2>&1 && PUBLIC_HEALTH=1
  curl -fsS --connect-timeout 10 "https://$CLOUD_HOST/.well-known/growcentral-cloud" >/dev/null 2>&1 && PUBLIC_DISCOVERY=1
  if [[ "$PUBLIC_HEALTH" -eq 1 ]]; then step_ok "HTTPS-Healthcheck OK"; else step_warn "Öffentlicher Healthcheck nicht erreichbar"; fi
  if [[ "$PUBLIC_DISCOVERY" -eq 1 ]]; then step_ok "Discovery/WSS-Endpunkte OK"; else step_warn "Discovery noch nicht öffentlich erreichbar"; fi

  step_begin "Offizielles APT-Repository eintragen"
  if configure_apt_repo_client; then
    step_ok "APT-Repo mit Signed-By eingetragen: $APT_REPO_URL"
  else
    step_warn "APT-Repo noch nicht erreichbar; Cloudinstallation bleibt funktionsfähig"
  fi

  step_begin "Abschlussprüfung"
  if systemctl is-active --quiet "$SERVICE" \
     && curl -fsS "http://127.0.0.1:$APP_PORT/health" >/dev/null 2>&1; then
    step_ok "Kernsystem vollständig funktionsfähig"
  else
    step_fail "Kernsystem nicht funktionsfähig"
  fi

  echo
  echo "  Prüfmatrix"
  echo "  ---------------------------------------------------------------------------"
  printf "  %-24s %s
" "systemd" "$(systemctl is-active --quiet "$SERVICE" && echo OK || echo FAILED)"
  printf "  %-24s %s
" "Backend lokal" "$(curl -fsS "http://127.0.0.1:$APP_PORT/health" >/dev/null 2>&1 && echo OK || echo FAILED)"
  printf "  %-24s %s
" "HTTPS öffentlich" "$([[ "${PUBLIC_HEALTH:-0}" -eq 1 ]] && echo OK || echo WARN)"
  printf "  %-24s %s
" "Discovery/WSS" "$([[ "${PUBLIC_DISCOVERY:-0}" -eq 1 ]] && echo OK || echo WARN)"
  printf "  %-24s %s
" "APT Repository" "$([[ -f "$APT_SOURCE" ]] && echo OK || echo WARN)"
  echo

  final_status
}

main "$@"
