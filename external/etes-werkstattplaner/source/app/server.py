#!/usr/bin/env python3
import argparse, base64, hashlib, hmac, json, os, re, secrets, sqlite3, sys, threading, time
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parent
PUBLIC = BASE / 'public'
DATA_DIR = Path(os.environ.get('DATA_DIR', str(BASE / 'data')))
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '3080'))
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', '1') == '1'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'werkstattplaner.sqlite'

RESOURCES = ['Bühne 1','Bühne 2','Bühne 3','Bühne 4','Bühne 5','Achsmessplatz']
STATUSES = ['Termin bestätigt','Fahrzeug da','In Arbeit','Wartet auf Teile','Rückfrage Kunde','Fertig','Abgeholt']
MECHANICS = ['—','Uwe','Torsten','Metin','Scheissnie','Jan','Leon']
PARTS = ['offen','bestellt','vorhanden','nicht erforderlich']
LOANER = ['Nein','Ja']

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
EVENT_COND = threading.Condition()
EVENT_VERSION = 0

def db_connect():
    con = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    return con

def init_db():
    con = db_connect()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('admin','editor','viewer')),
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS appointments (
      id TEXT PRIMARY KEY,date TEXT NOT NULL,resource TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,
      plate TEXT NOT NULL,vehicle TEXT DEFAULT '',customer TEXT DEFAULT '',phone TEXT DEFAULT '',mechanic TEXT DEFAULT '—',
      status TEXT NOT NULL DEFAULT 'Termin bestätigt',job TEXT DEFAULT '',parts TEXT DEFAULT 'offen',loaner TEXT DEFAULT 'Nein',note TEXT DEFAULT '',
      created_by INTEGER,updated_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(created_by) REFERENCES users(id),FOREIGN KEY(updated_by) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(date);
    CREATE TABLE IF NOT EXISTS audit_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT NOT NULL,appointment_id TEXT,details TEXT,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id)
    );
    ''')
    con.commit()
    con.close()

def hash_password(password):
    salt = secrets.token_bytes(16)
    iterations = 310000
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    return 'pbkdf2_sha256$%d$%s$%s' % (iterations, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())

def verify_password(password, stored):
    try:
        alg, it, salt64, dig64 = stored.split('$', 3)
        if alg != 'pbkdf2_sha256':
            return False
        salt = base64.b64decode(salt64)
        expected = base64.b64decode(dig64)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, int(it))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def clean(v, n=500):
    return str(v or '').strip()[:n]

def validate_username(name):
    name = clean(name, 80)
    if len(name) < 2:
        raise ValueError('Benutzername muss mindestens 2 Zeichen haben')
    if not re.fullmatch(r"[A-Za-zÄÖÜäöüß0-9 ._@'\-]+", name):
        raise ValueError('Benutzername enthält ungültige Zeichen')
    return name

def validate_password(password):
    password = str(password or '')
    if len(password) < 10:
        raise ValueError('Passwort muss mindestens 10 Zeichen haben')
    return password

def users_exist():
    con = db_connect()
    n = con.execute('SELECT COUNT(*) FROM users WHERE active=1').fetchone()[0]
    con.close()
    return n > 0

def active_admin_count(con):
    return con.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]

def create_initial_admin(name, password):
    name = validate_username(name)
    password = validate_password(password)
    con = db_connect()
    try:
        con.execute('BEGIN IMMEDIATE')
        if con.execute('SELECT COUNT(*) FROM users').fetchone()[0] != 0:
            raise ValueError('Ersteinrichtung wurde bereits abgeschlossen')
        con.execute('INSERT INTO users(name,password_hash,role,active) VALUES(?,?,?,1)', (name, hash_password(password), 'admin'))
        uid = con.execute('SELECT id FROM users WHERE name=?', (name,)).fetchone()[0]
        con.commit()
        return {'id': uid, 'name': name, 'role': 'admin'}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def upsert_user(name, role, password):
    name = validate_username(name)
    password = validate_password(password)
    if role not in ('admin','editor','viewer'):
        raise ValueError('Ungültige Rolle')
    con = db_connect()
    con.execute('''INSERT INTO users(name,password_hash,role,active) VALUES(?,?,?,1)
      ON CONFLICT(name) DO UPDATE SET password_hash=excluded.password_hash,role=excluded.role,active=1,updated_at=CURRENT_TIMESTAMP''',
      (name, hash_password(password), role))
    con.commit()
    con.close()

def notify_change():
    global EVENT_VERSION
    with EVENT_COND:
        EVENT_VERSION += 1
        EVENT_COND.notify_all()

def valid_date(v): return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', v))
def valid_time(v): return bool(re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v))
def tmins(v):
    h,m = map(int,v.split(':'))
    return h*60+m

def validate_appt(b, forced_id=None):
    a = {
      'id': clean(forced_id or b.get('id'),80),'date':clean(b.get('date'),10),'resource':clean(b.get('resource'),40),
      'start':clean(b.get('start'),5),'end':clean(b.get('end'),5),'plate':clean(b.get('plate'),32),'vehicle':clean(b.get('vehicle'),120),
      'customer':clean(b.get('customer'),120),'phone':clean(b.get('phone'),50),'mechanic':clean(b.get('mechanic'),40),
      'status':clean(b.get('status'),40),'job':clean(b.get('job'),2000),'parts':clean(b.get('parts'),40),'loaner':clean(b.get('loaner'),10),'note':clean(b.get('note'),2000)
    }
    if not a['id'] or not valid_date(a['date']) or a['resource'] not in RESOURCES or not valid_time(a['start']) or not valid_time(a['end']) or not a['plate']:
        raise ValueError('Ungültige Pflichtfelder')
    if tmins(a['end']) <= tmins(a['start']):
        raise ValueError('Endzeit muss nach Startzeit liegen')
    if a['status'] not in STATUSES or a['mechanic'] not in MECHANICS or a['parts'] not in PARTS or a['loaner'] not in LOANER:
        raise ValueError('Ungültiger Auswahlwert')
    return a

class Handler(SimpleHTTPRequestHandler):
    server_version = 'EtesWerkstattplaner/1.2'

    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(PUBLIC),**kwargs)

    def log_message(self, fmt,*args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt%args))

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; manifest-src 'self'; worker-src 'self'")
        super().end_headers()

    def json_out(self,obj,status=200,extra=None):
        raw=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        if extra:
            for k,v in extra:
                self.send_header(k,v)
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>262144:
                raise ValueError('Anfrage zu groß')
            return json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            raise
        except Exception:
            raise ValueError('Ungültiges JSON')

    def session_user(self):
        c=SimpleCookie(self.headers.get('Cookie',''))
        morsel=c.get('etes_session')
        if not morsel:
            return None
        token=morsel.value
        with SESSIONS_LOCK:
            s=SESSIONS.get(token)
            if not s or s['expires']<time.time():
                SESSIONS.pop(token,None)
                return None
            uid=s['user_id']
            s['expires']=time.time()+12*3600
        con=db_connect()
        row=con.execute('SELECT id,name,role,active FROM users WHERE id=?',(uid,)).fetchone()
        con.close()
        if not row or not row['active']:
            with SESSIONS_LOCK:
                SESSIONS.pop(token,None)
            return None
        return {'id':row['id'],'name':row['name'],'role':row['role']}

    def create_session(self, user):
        token=secrets.token_urlsafe(32)
        with SESSIONS_LOCK:
            SESSIONS[token]={'user_id':user['id'],'expires':time.time()+12*3600}
        cookie=f'etes_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200' + ('; Secure' if COOKIE_SECURE else '')
        return cookie

    def require(self,roles=None):
        u=self.session_user()
        if not u:
            self.json_out({'error':'Nicht angemeldet'},401)
            return None
        if roles and u['role'] not in roles:
            self.json_out({'error':'Keine Berechtigung'},403)
            return None
        return u

    def safe_origin(self):
        origin=self.headers.get('Origin')
        host=self.headers.get('Host')
        return not origin or urlparse(origin).netloc==host

    def do_GET(self):
        p=urlparse(self.path)
        if p.path=='/health':
            return self.json_out({'ok':True,'service':'etes-werkstattplaner','version':'1.2.0','configured':users_exist()})
        if p.path=='/api/setup-status':
            return self.json_out({'needs_setup':not users_exist()})
        if p.path.startswith('/api/'):
            if not users_exist():
                return self.json_out({'error':'Ersteinrichtung erforderlich','needs_setup':True},428)
            if p.path=='/api/me':
                u=self.require()
                return None if not u else self.json_out({'user':u})
            if p.path=='/api/config':
                u=self.require()
                return None if not u else self.json_out({'resources':RESOURCES,'statuses':STATUSES,'mechanics':MECHANICS,'parts':PARTS,'loaner':LOANER})
            if p.path=='/api/appointments':
                u=self.require()
                if not u:return
                date=clean(parse_qs(p.query).get('date',[''])[0],10)
                if not valid_date(date):
                    return self.json_out({'error':'Ungültiges Datum'},400)
                con=db_connect()
                rows=con.execute('''SELECT a.*,cu.name created_by_name,uu.name updated_by_name FROM appointments a LEFT JOIN users cu ON a.created_by=cu.id LEFT JOIN users uu ON a.updated_by=uu.id WHERE a.date=? ORDER BY a.start,a.resource''',(date,)).fetchall()
                con.close()
                return self.json_out({'appointments':[dict(r) for r in rows]})
            if p.path=='/api/users':
                u=self.require(('admin',))
                if not u:return
                con=db_connect()
                rows=con.execute('SELECT id,name,role,active,created_at,updated_at FROM users ORDER BY active DESC,role,name').fetchall()
                con.close()
                return self.json_out({'users':[dict(r) for r in rows]})
            if p.path=='/api/events':
                return self.handle_events()
            return self.json_out({'error':'Nicht gefunden'},404)
        if p.path=='/':
            self.path='/index.html'
        return super().do_GET()

    def do_POST(self):
        if not self.safe_origin():
            return self.json_out({'error':'Ungültiger Origin'},403)
        p=urlparse(self.path)

        if p.path=='/api/setup':
            if users_exist():
                return self.json_out({'error':'Ersteinrichtung wurde bereits abgeschlossen'},409)
            try:
                b=self.read_json()
                name=validate_username(b.get('name'))
                pw=validate_password(b.get('password'))
                if pw != str(b.get('password_confirm') or ''):
                    raise ValueError('Passwörter stimmen nicht überein')
                user=create_initial_admin(name,pw)
            except ValueError as e:
                return self.json_out({'error':str(e)},400)
            cookie=self.create_session(user)
            return self.json_out({'ok':True,'user':user},201,[('Set-Cookie',cookie)])

        if not users_exist():
            return self.json_out({'error':'Ersteinrichtung erforderlich','needs_setup':True},428)

        if p.path=='/api/login':
            try:b=self.read_json()
            except ValueError as e:return self.json_out({'error':str(e)},400)
            name=clean(b.get('name'),80)
            pw=str(b.get('password') or '')
            con=db_connect()
            row=con.execute('SELECT * FROM users WHERE name=? AND active=1',(name,)).fetchone()
            con.close()
            if not row or not verify_password(pw,row['password_hash']):
                return self.json_out({'error':'Name oder Passwort falsch'},401)
            user={'id':row['id'],'name':row['name'],'role':row['role']}
            cookie=self.create_session(user)
            return self.json_out({'user':user},200,[('Set-Cookie',cookie)])

        if p.path=='/api/logout':
            u=self.require()
            if not u:return
            c=SimpleCookie(self.headers.get('Cookie',''))
            m=c.get('etes_session')
            if m:
                with SESSIONS_LOCK:
                    SESSIONS.pop(m.value,None)
            return self.json_out({'ok':True},200,[('Set-Cookie','etes_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax')])

        if p.path=='/api/users':
            u=self.require(('admin',))
            if not u:return
            try:
                b=self.read_json()
                name=validate_username(b.get('name'))
                role=clean(b.get('role'),20)
                pw=validate_password(b.get('password'))
                if role not in ('admin','editor','viewer'):
                    raise ValueError('Ungültige Rolle')
                con=db_connect()
                con.execute('INSERT INTO users(name,password_hash,role,active) VALUES(?,?,?,1)',(name,hash_password(pw),role))
                uid=con.execute('SELECT id FROM users WHERE name=?',(name,)).fetchone()[0]
                con.commit(); con.close()
                return self.json_out({'ok':True,'id':uid},201)
            except sqlite3.IntegrityError:
                return self.json_out({'error':'Benutzername ist bereits vorhanden'},409)
            except ValueError as e:
                return self.json_out({'error':str(e)},400)

        if p.path=='/api/appointments':
            u=self.require(('admin','editor'))
            if not u:return
            try:b=self.read_json(); a=validate_appt(b)
            except ValueError as e:return self.json_out({'error':str(e)},400)
            con=db_connect()
            conflict=con.execute('SELECT id,plate FROM appointments WHERE id<>? AND date=? AND resource=? AND start<? AND end>? LIMIT 1',(a['id'],a['date'],a['resource'],a['end'],a['start'])).fetchone()
            if conflict and not b.get('force'):
                con.close()
                return self.json_out({'error':'Arbeitsplatz bereits belegt','conflict':dict(conflict)},409)
            cols=('id','date','resource','start','end','plate','vehicle','customer','phone','mechanic','status','job','parts','loaner','note')
            con.execute(f"INSERT INTO appointments({','.join(cols)},created_by,updated_by) VALUES({','.join('?' for _ in cols)},?,?)", tuple(a[k] for k in cols)+(u['id'],u['id']))
            con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,?,?)',(u['id'],'create',a['id'],f"{a['date']} {a['start']}-{a['end']} {a['resource']}"))
            con.commit(); con.close(); notify_change()
            return self.json_out({'ok':True},201)
        return self.json_out({'error':'Nicht gefunden'},404)

    def do_PUT(self):
        if not self.safe_origin():
            return self.json_out({'error':'Ungültiger Origin'},403)
        p=urlparse(self.path)

        um=re.fullmatch(r'/api/users/(\d+)',p.path)
        if um:
            u=self.require(('admin',))
            if not u:return
            uid=int(um.group(1))
            try:
                b=self.read_json()
                name=validate_username(b.get('name'))
                role=clean(b.get('role'),20)
                active=1 if bool(b.get('active',True)) else 0
                pw=str(b.get('password') or '')
                if role not in ('admin','editor','viewer'):
                    raise ValueError('Ungültige Rolle')
                if pw:
                    validate_password(pw)
            except ValueError as e:
                return self.json_out({'error':str(e)},400)

            con=db_connect()
            row=con.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            if not row:
                con.close()
                return self.json_out({'error':'Benutzer nicht gefunden'},404)
            if uid==u['id'] and not active:
                con.close()
                return self.json_out({'error':'Eigenes Konto kann nicht deaktiviert werden'},400)
            if row['role']=='admin' and row['active'] and (role!='admin' or not active) and active_admin_count(con)<=1:
                con.close()
                return self.json_out({'error':'Der letzte aktive Administrator kann nicht entfernt werden'},400)
            try:
                if pw:
                    con.execute('UPDATE users SET name=?,role=?,active=?,password_hash=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(name,role,active,hash_password(pw),uid))
                else:
                    con.execute('UPDATE users SET name=?,role=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(name,role,active,uid))
                con.commit()
            except sqlite3.IntegrityError:
                con.close()
                return self.json_out({'error':'Benutzername ist bereits vorhanden'},409)
            con.close()
            return self.json_out({'ok':True})

        m=re.fullmatch(r'/api/appointments/([^/]+)',p.path)
        if not m:
            return self.json_out({'error':'Nicht gefunden'},404)
        u=self.require(('admin','editor'))
        if not u:return
        try:b=self.read_json(); aid=m.group(1); a=validate_appt(b,aid)
        except ValueError as e:return self.json_out({'error':str(e)},400)
        con=db_connect()
        old=con.execute('SELECT * FROM appointments WHERE id=?',(aid,)).fetchone()
        if not old:
            con.close()
            return self.json_out({'error':'Termin nicht gefunden'},404)
        conflict=con.execute('SELECT id,plate FROM appointments WHERE id<>? AND date=? AND resource=? AND start<? AND end>? LIMIT 1',(aid,a['date'],a['resource'],a['end'],a['start'])).fetchone()
        if conflict and not b.get('force'):
            con.close()
            return self.json_out({'error':'Arbeitsplatz bereits belegt','conflict':dict(conflict)},409)
        fields=['date','resource','start','end','plate','vehicle','customer','phone','mechanic','status','job','parts','loaner','note']
        con.execute('UPDATE appointments SET '+','.join(f'{k}=?' for k in fields)+',updated_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',tuple(a[k] for k in fields)+(u['id'],aid))
        con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,?,?)',(u['id'],'update',aid,f"{old['date']}/{old['resource']}/{old['start']} -> {a['date']}/{a['resource']}/{a['start']}"))
        con.commit(); con.close(); notify_change()
        return self.json_out({'ok':True})

    def do_DELETE(self):
        if not self.safe_origin():
            return self.json_out({'error':'Ungültiger Origin'},403)
        m=re.fullmatch(r'/api/appointments/([^/]+)',urlparse(self.path).path)
        if not m:
            return self.json_out({'error':'Nicht gefunden'},404)
        u=self.require(('admin','editor'))
        if not u:return
        aid=m.group(1)
        con=db_connect()
        old=con.execute('SELECT * FROM appointments WHERE id=?',(aid,)).fetchone()
        if not old:
            con.close()
            return self.json_out({'error':'Termin nicht gefunden'},404)
        con.execute('DELETE FROM appointments WHERE id=?',(aid,))
        con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,?,?)',(u['id'],'delete',aid,f"{old['date']} {old['start']}-{old['end']} {old['plate']}"))
        con.commit(); con.close(); notify_change()
        return self.json_out({'ok':True})

    def handle_events(self):
        u=self.session_user()
        if not u:
            return self.json_out({'error':'Nicht angemeldet'},401)
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream')
        self.send_header('Cache-Control','no-cache')
        self.send_header('Connection','keep-alive')
        self.end_headers()
        seen=EVENT_VERSION
        try:
            self.wfile.write(b'event: ready\ndata: {}\n\n')
            self.wfile.flush()
            while True:
                with EVENT_COND:
                    EVENT_COND.wait(timeout=20)
                    current=EVENT_VERSION
                if current!=seen:
                    seen=current
                    self.wfile.write(b'event: appointments-changed\ndata: {}\n\n')
                else:
                    self.wfile.write(b': ping\n\n')
                self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError):
            return

def main():
    init_db()
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd')
    u=sub.add_parser('user')
    u.add_argument('name')
    u.add_argument('role',choices=['admin','editor','viewer'])
    u.add_argument('password',nargs='?')
    args=ap.parse_args()
    if args.cmd=='user':
        import getpass
        pw=args.password or getpass.getpass(f'Passwort für {args.name}: ')
        try:
            upsert_user(args.name,args.role,pw)
            print(f'Benutzer {args.name} als {args.role} angelegt/aktualisiert.')
        except ValueError as e:
            print(e,file=sys.stderr)
            sys.exit(2)
        return
    print(f"Ete's Werkstattplaner 1.2 auf http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

if __name__=='__main__':
    main()
