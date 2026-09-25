#!/usr/bin/env python3
import argparse, base64, hashlib, hmac, json, os, re, secrets, sqlite3, sys, threading, time
from datetime import date, datetime, timedelta
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from personnel import MAX_WORKBOOK_BYTES, WorkbookImportError, brandenburg_holidays, normalize_personnel_code, parse_personnel_xlsx

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
MODULES = ('werkstattplaner','personalplaner')
PERMISSION_LEVELS = ('view','edit','manage')

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
EVENT_COND = threading.Condition()
EVENT_VERSION = 0
EVENT_KIND = 'appointments-changed'

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
    CREATE TABLE IF NOT EXISTS user_permissions (
      user_id INTEGER NOT NULL,
      module TEXT NOT NULL CHECK(module IN ('werkstattplaner','personalplaner')),
      can_view INTEGER NOT NULL DEFAULT 0,
      can_edit INTEGER NOT NULL DEFAULT 0,
      can_manage INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY(user_id,module),
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
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
    CREATE TABLE IF NOT EXISTS personnel_employees (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL COLLATE NOCASE UNIQUE,
      active INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS personnel_employee_years (
      employee_id INTEGER NOT NULL,
      year INTEGER NOT NULL,
      annual_vacation REAL NOT NULL DEFAULT 0,
      carryover_vacation REAL NOT NULL DEFAULT 0,
      source_import_id TEXT,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(employee_id,year),
      FOREIGN KEY(employee_id) REFERENCES personnel_employees(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS personnel_imports (
      id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      year INTEGER NOT NULL,
      region TEXT NOT NULL DEFAULT 'Brandenburg',
      payload_json TEXT NOT NULL,
      warnings_json TEXT NOT NULL DEFAULT '[]',
      employee_count INTEGER NOT NULL DEFAULT 0,
      entry_count INTEGER NOT NULL DEFAULT 0,
      manual_conflicts INTEGER NOT NULL DEFAULT 0,
      created_by INTEGER,
      status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','committed','cancelled')),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      committed_at TEXT,
      FOREIGN KEY(created_by) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_personnel_imports_year ON personnel_imports(year,status,created_at);
    CREATE TABLE IF NOT EXISTS personnel_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      employee_id INTEGER NOT NULL,
      date TEXT NOT NULL,
      code TEXT NOT NULL,
      category TEXT NOT NULL,
      portion REAL NOT NULL DEFAULT 1 CHECK(portion IN (0.5,1.0)),
      label TEXT NOT NULL DEFAULT '',
      note TEXT NOT NULL DEFAULT '',
      source TEXT NOT NULL DEFAULT 'manual' CHECK(source IN ('manual','excel')),
      source_import_id TEXT,
      created_by INTEGER,
      updated_by INTEGER,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(employee_id,date),
      FOREIGN KEY(employee_id) REFERENCES personnel_employees(id) ON DELETE CASCADE,
      FOREIGN KEY(source_import_id) REFERENCES personnel_imports(id),
      FOREIGN KEY(created_by) REFERENCES users(id),
      FOREIGN KEY(updated_by) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_personnel_entries_date ON personnel_entries(date);
    CREATE INDEX IF NOT EXISTS idx_personnel_entries_employee ON personnel_entries(employee_id,date);
    ''')
    rows = con.execute('SELECT id,role FROM users').fetchall()
    for row in rows:
        if row['role']=='admin':
            defaults=(1,1,1)
        elif row['role']=='editor':
            defaults=(1,1,0)
        else:
            defaults=(1,0,0)
        for module in MODULES:
            con.execute('''INSERT OR IGNORE INTO user_permissions(user_id,module,can_view,can_edit,can_manage)
                           VALUES(?,?,?,?,?)''',(row['id'],module,*defaults))
    con.commit()
    con.close()

def default_permissions_for_role(role):
    if role=='admin':
        return {m:{'view':True,'edit':True,'manage':True} for m in MODULES}
    if role=='editor':
        return {m:{'view':True,'edit':True,'manage':False} for m in MODULES}
    return {m:{'view':True,'edit':False,'manage':False} for m in MODULES}

def normalize_permissions(raw, role='viewer'):
    base=default_permissions_for_role(role)
    if not isinstance(raw,dict):
        return base
    out={}
    for module in MODULES:
        src=raw.get(module,{})
        view=bool(src.get('view',base[module]['view']))
        edit=bool(src.get('edit',base[module]['edit'])) and view
        manage=bool(src.get('manage',base[module]['manage'])) and view
        if manage:
            edit=True
        out[module]={'view':view,'edit':edit,'manage':manage}
    return out

def save_permissions(con, user_id, permissions):
    for module in MODULES:
        p=permissions[module]
        con.execute('''INSERT INTO user_permissions(user_id,module,can_view,can_edit,can_manage)
                       VALUES(?,?,?,?,?)
                       ON CONFLICT(user_id,module) DO UPDATE SET
                       can_view=excluded.can_view,can_edit=excluded.can_edit,can_manage=excluded.can_manage''',
                    (user_id,module,int(p['view']),int(p['edit']),int(p['manage'])))

def load_permissions(con, user_id):
    rows=con.execute('SELECT module,can_view,can_edit,can_manage FROM user_permissions WHERE user_id=?',(user_id,)).fetchall()
    data={r['module']:{'view':bool(r['can_view']),'edit':bool(r['can_edit']),'manage':bool(r['can_manage'])} for r in rows}
    if len(data)!=len(MODULES):
        role=con.execute('SELECT role FROM users WHERE id=?',(user_id,)).fetchone()
        perms=normalize_permissions(data, role['role'] if role else 'viewer')
        save_permissions(con,user_id,perms)
        return perms
    return data

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
        save_permissions(con,uid,default_permissions_for_role('admin'))
        con.commit()
        return {'id': uid, 'name': name, 'role': 'admin', 'permissions': default_permissions_for_role('admin')}
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
    uid=con.execute('SELECT id FROM users WHERE name=?',(name,)).fetchone()[0]
    save_permissions(con,uid,default_permissions_for_role(role))
    con.commit()
    con.close()

def notify_change(kind='appointments-changed'):
    global EVENT_VERSION, EVENT_KIND
    with EVENT_COND:
        EVENT_VERSION += 1
        EVENT_KIND = kind
        EVENT_COND.notify_all()

def valid_date(v): return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', v))
def valid_time(v): return bool(re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v))
def tmins(v):
    h,m = map(int,v.split(':'))
    return h*60+m

def parse_iso_date(value):
    value=clean(value,10)
    if not valid_date(value):
        raise ValueError('Ungültiges Datum')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError('Ungültiges Datum')

def valid_personnel_year(value):
    try: year=int(value)
    except (TypeError,ValueError): raise ValueError('Ungültiges Planungsjahr')
    if year<2000 or year>2100:
        raise ValueError('Ungültiges Planungsjahr')
    return year

def vacation_number(value,label,minimum=-100):
    try: number=float(value or 0)
    except (TypeError,ValueError): raise ValueError(label+' ist ungültig')
    if number<minimum or number>366:
        raise ValueError(label+' liegt außerhalb des zulässigen Bereichs')
    return round(number*2)/2

def validate_personnel_employee(body):
    try: sort_order=max(0,min(9999,int(body.get('sort_order') or 0)))
    except (TypeError,ValueError): raise ValueError('Sortierung ist ungültig')
    return {
      'name':validate_username(body.get('name')),
      'active':1 if bool(body.get('active',True)) else 0,
      'sort_order':sort_order,
      'year':valid_personnel_year(body.get('year')),
      'annual_vacation':vacation_number(body.get('annual_vacation'),'Urlaubsanspruch',0),
      'carryover_vacation':vacation_number(body.get('carryover_vacation'),'Resturlaub Vorjahr')
    }

def validate_personnel_entry(body,forced_id=None):
    try: employee_id=int(body.get('employee_id'))
    except (TypeError,ValueError): raise ValueError('Mitarbeiter fehlt')
    if employee_id<1: raise ValueError('Mitarbeiter fehlt')
    entry_date=parse_iso_date(body.get('date')).isoformat()
    requested=clean(body.get('code'),12)
    if requested.upper()=='CUSTOM':
        requested=clean(body.get('custom_code'),12)
    try: portion=float(body.get('portion') or 1)
    except (TypeError,ValueError): raise ValueError('Umfang ist ungültig')
    info=normalize_personnel_code(requested,portion)
    label=clean(body.get('label'),80) if info['category']=='custom' else str(info['label'])
    if not label: label='Benutzerdefiniert'
    return {
      'id':int(forced_id) if forced_id is not None else None,
      'employee_id':employee_id,'date':entry_date,'code':str(info['code']),
      'category':str(info['category']),'portion':float(info['portion']),
      'label':label,'note':clean(body.get('note'),500)
    }

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
    server_version = 'EtesWerkstattplaner/1.4'

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

    def read_xlsx_upload(self):
        content_type=self.headers.get('Content-Type','')
        match=re.search(r'boundary=(?:"([^"]+)"|([^;]+))',content_type,re.I)
        if not content_type.lower().startswith('multipart/form-data') or not match:
            raise ValueError('Excel-Datei fehlt')
        boundary=(match.group(1) or match.group(2) or '').strip().encode('ascii','ignore')
        if not boundary or len(boundary)>200:
            raise ValueError('Ungültiger Datei-Upload')
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ValueError('Ungültiger Datei-Upload')
        if length<1 or length>MAX_WORKBOOK_BYTES+131072:
            raise ValueError('Die Excel-Datei ist leer oder größer als 5 MB')
        raw=self.rfile.read(length)
        marker=b'--'+boundary
        for part in raw.split(marker):
            if b'\r\n\r\n' not in part: continue
            header_raw,body=part.split(b'\r\n\r\n',1)
            headers=header_raw.decode('iso-8859-1','replace')
            if not re.search(r'content-disposition:\s*form-data',headers,re.I): continue
            name_match=re.search(r'name="([^"]+)"',headers,re.I)
            if not name_match or name_match.group(1)!='file': continue
            filename_match=re.search(r'filename="([^"]*)"',headers,re.I)
            filename=Path((filename_match.group(1) if filename_match else 'Personalplaner.xlsx').replace('\\','/')).name
            if body.endswith(b'\r\n'): body=body[:-2]
            if not filename.lower().endswith('.xlsx'): raise ValueError('Bitte eine XLSX-Datei auswählen')
            if len(body)>MAX_WORKBOOK_BYTES: raise ValueError('Die Excel-Datei ist größer als 5 MB')
            return filename[:200],body
        raise ValueError('Excel-Datei fehlt')

    def personnel_plan(self,query):
        try:
            start=parse_iso_date(query.get('start',[''])[0])
            end=parse_iso_date(query.get('end',[''])[0])
            year=valid_personnel_year(query.get('year',[start.year])[0])
            if end<start or (end-start).days>370: raise ValueError('Zeitraum ist ungültig')
        except ValueError as exc:
            return self.json_out({'error':str(exc)},400)
        con=db_connect()
        employee_rows=con.execute('''SELECT e.id,e.name,e.active,e.sort_order,
          COALESCE(y.annual_vacation,0) annual_vacation,COALESCE(y.carryover_vacation,0) carryover_vacation
          FROM personnel_employees e LEFT JOIN personnel_employee_years y
          ON y.employee_id=e.id AND y.year=? WHERE e.active=1 ORDER BY e.sort_order,e.name COLLATE NOCASE''',(year,)).fetchall()
        entry_rows=con.execute('''SELECT pe.*,e.name employee_name,u.name updated_by_name
          FROM personnel_entries pe JOIN personnel_employees e ON e.id=pe.employee_id
          LEFT JOIN users u ON u.id=pe.updated_by
          WHERE pe.date BETWEEN ? AND ? AND e.active=1
          ORDER BY e.sort_order,e.name COLLATE NOCASE,pe.date''',(start.isoformat(),end.isoformat())).fetchall()
        usage_rows=con.execute('''SELECT employee_id,
          COALESCE(SUM(CASE WHEN category='vacation' THEN portion ELSE 0 END),0) vacation_used,
          COALESCE(SUM(CASE WHEN category='sick' THEN portion ELSE 0 END),0) sick_days
          FROM personnel_entries WHERE date BETWEEN ? AND ? GROUP BY employee_id''',
          (f'{year:04d}-01-01',f'{year:04d}-12-31')).fetchall()
        usage={r['employee_id']:r for r in usage_rows}
        last_import=con.execute("SELECT filename,year,committed_at FROM personnel_imports WHERE status='committed' ORDER BY committed_at DESC LIMIT 1").fetchone()
        con.close()
        employees=[]
        for row in employee_rows:
            used=float((usage.get(row['id']) or {'vacation_used':0})['vacation_used'] or 0)
            sick=float((usage.get(row['id']) or {'sick_days':0})['sick_days'] or 0)
            total=float(row['annual_vacation'] or 0)+float(row['carryover_vacation'] or 0)
            employees.append({**dict(row),'vacation_total':total,'vacation_used':used,'vacation_remaining':total-used,'sick_days':sick})
        holidays=[h for h in brandenburg_holidays(year) if start.isoformat()<=h['date']<=end.isoformat()]
        return self.json_out({'year':year,'region':'Brandenburg','region_code':'BB','start':start.isoformat(),'end':end.isoformat(),
          'employees':employees,'entries':[dict(r) for r in entry_rows],'holidays':holidays,
          'last_import':dict(last_import) if last_import else None,
          'codes':[{'code':'U','half_code':'UH','category':'vacation','label':'Urlaub'},
                   {'code':'K','half_code':'KH','category':'sick','label':'Krankheit'},
                   {'code':'A','half_code':'AH','category':'work','label':'Arbeit'},
                   {'code':'I','half_code':'IH','category':'individual','label':'Individuell'},
                   {'code':'P','half_code':'ph','category':'extra','label':'Zusatzspalte'},
                   {'code':'CUSTOM','half_code':'CUSTOM','category':'custom','label':'Benutzerdefiniert'}]})

    def personnel_import_preview(self,user):
        try:
            filename,data=self.read_xlsx_upload()
            payload=parse_personnel_xlsx(data,filename)
        except (ValueError,WorkbookImportError) as exc:
            return self.json_out({'error':str(exc)},400)
        year=payload['year']
        imported_keys={(e['name'].casefold(),entry['date']) for e in payload['employees'] for entry in e['entries']}
        con=db_connect()
        manual=con.execute('''SELECT e.name,pe.date FROM personnel_entries pe JOIN personnel_employees e ON e.id=pe.employee_id
          WHERE pe.source='manual' AND pe.date BETWEEN ? AND ?''',(f'{year:04d}-01-01',f'{year:04d}-12-31')).fetchall()
        manual_conflicts=sum(1 for r in manual if (r['name'].casefold(),r['date']) in imported_keys)
        import_id=secrets.token_urlsafe(18)
        warnings=list(payload.get('warnings') or [])
        if manual_conflicts: warnings.append(f'{manual_conflicts} manuelle Einträge haben Vorrang und werden nicht überschrieben.')
        con.execute("DELETE FROM personnel_imports WHERE status='draft' AND created_at<datetime('now','-2 days')")
        con.execute('''INSERT INTO personnel_imports(id,filename,sha256,year,region,payload_json,warnings_json,employee_count,entry_count,manual_conflicts,created_by)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(import_id,payload['filename'],payload['sha256'],year,'Brandenburg',
          json.dumps(payload,ensure_ascii=False,separators=(',',':')),json.dumps(warnings,ensure_ascii=False),
          payload['employee_count'],payload['entry_count'],manual_conflicts,user['id']))
        con.commit();con.close()
        employees=[{'name':e['name'],'annual_vacation':e['annual_vacation'],'carryover_vacation':e['carryover_vacation'],'entry_count':len(e['entries'])} for e in payload['employees']]
        return self.json_out({'preview':{'id':import_id,'filename':payload['filename'],'year':year,'region':'Brandenburg',
          'employee_count':payload['employee_count'],'entry_count':payload['entry_count'],'code_counts':payload['code_counts'],
          'warnings':warnings,'manual_conflicts':manual_conflicts,'employees':employees}},201)

    def personnel_import_commit(self,user,body):
        import_id=clean(body.get('import_id'),80)
        if not import_id: return self.json_out({'error':'Import-Vorschau fehlt'},400)
        con=db_connect()
        row=con.execute("SELECT * FROM personnel_imports WHERE id=? AND status='draft'",(import_id,)).fetchone()
        if not row:
            con.close();return self.json_out({'error':'Import-Vorschau nicht gefunden oder bereits verwendet'},404)
        payload=json.loads(row['payload_json']);year=int(row['year'])
        inserted=0;preserved=0
        try:
            con.execute('BEGIN IMMEDIATE')
            con.execute("DELETE FROM personnel_entries WHERE source='excel' AND date BETWEEN ? AND ?",(f'{year:04d}-01-01',f'{year:04d}-12-31'))
            for emp in payload['employees']:
                existing=con.execute('SELECT id FROM personnel_employees WHERE name=? COLLATE NOCASE',(emp['name'],)).fetchone()
                if existing: eid=existing['id'];con.execute('UPDATE personnel_employees SET active=1,sort_order=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(emp['sort_order'],eid))
                else:
                    cur=con.execute('INSERT INTO personnel_employees(name,active,sort_order) VALUES(?,1,?)',(emp['name'],emp['sort_order']));eid=cur.lastrowid
                yearrow=con.execute('SELECT source_import_id FROM personnel_employee_years WHERE employee_id=? AND year=?',(eid,year)).fetchone()
                if yearrow and yearrow['source_import_id'] is None:
                    preserved+=1
                else:
                    con.execute('''INSERT INTO personnel_employee_years(employee_id,year,annual_vacation,carryover_vacation,source_import_id)
                      VALUES(?,?,?,?,?) ON CONFLICT(employee_id,year) DO UPDATE SET annual_vacation=excluded.annual_vacation,
                      carryover_vacation=excluded.carryover_vacation,source_import_id=excluded.source_import_id,updated_at=CURRENT_TIMESTAMP''',
                      (eid,year,emp['annual_vacation'],emp['carryover_vacation'],import_id))
                for entry in emp['entries']:
                    conflict=con.execute("SELECT id FROM personnel_entries WHERE employee_id=? AND date=? AND source='manual'",(eid,entry['date'])).fetchone()
                    if conflict: continue
                    con.execute('''INSERT OR REPLACE INTO personnel_entries(employee_id,date,code,category,portion,label,note,source,source_import_id,created_by,updated_by)
                      VALUES(?,?,?,?,?,?,?,'excel',?,?,?)''',(eid,entry['date'],entry['code'],entry['category'],entry['portion'],entry['label'],'',import_id,user['id'],user['id']))
                    inserted+=1
            con.execute("UPDATE personnel_imports SET status='committed',committed_at=CURRENT_TIMESTAMP WHERE id=?",(import_id,))
            con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',(user['id'],'personnel-import',f'{year}: {inserted} Einträge'))
            con.commit()
        except Exception:
            con.rollback();con.close();raise
        con.close();notify_change('personnel-changed')
        return self.json_out({'ok':True,'inserted':inserted,'manual_conflicts':row['manual_conflicts'],'manual_allowances_preserved':preserved})

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
        perms=load_permissions(con,uid) if row else {}
        con.close()
        if not row or not row['active']:
            with SESSIONS_LOCK:
                SESSIONS.pop(token,None)
            return None
        return {'id':row['id'],'name':row['name'],'role':row['role'],'permissions':perms}

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

    def require_perm(self,module,level='view'):
        u=self.require()
        if not u:
            return None
        if u['role']=='admin':
            return u
        perms=u.get('permissions',{}).get(module,{})
        key={'view':'view','edit':'edit','manage':'manage'}.get(level,'view')
        if not perms.get(key,False):
            self.json_out({'error':'Keine Berechtigung für '+module},403)
            return None
        return u

    def safe_origin(self):
        origin=self.headers.get('Origin')
        host=self.headers.get('Host')
        return not origin or urlparse(origin).netloc==host

    def do_GET(self):
        p=urlparse(self.path)
        if p.path=='/health':
            return self.json_out({'ok':True,'service':'etes-werkstattplaner','version':'1.4.0','configured':users_exist()})
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
                return None if not u else self.json_out({'resources':RESOURCES,'statuses':STATUSES,'mechanics':MECHANICS,'parts':PARTS,'loaner':LOANER,'modules':list(MODULES)})
            if p.path=='/api/appointments':
                u=self.require_perm('werkstattplaner','view')
                if not u:return
                date=clean(parse_qs(p.query).get('date',[''])[0],10)
                if not valid_date(date):
                    return self.json_out({'error':'Ungültiges Datum'},400)
                con=db_connect()
                rows=con.execute('''SELECT a.*,cu.name created_by_name,uu.name updated_by_name FROM appointments a LEFT JOIN users cu ON a.created_by=cu.id LEFT JOIN users uu ON a.updated_by=uu.id WHERE a.date=? ORDER BY a.start,a.resource''',(date,)).fetchall()
                con.close()
                return self.json_out({'appointments':[dict(r) for r in rows]})
            if p.path=='/api/personnel/plan':
                u=self.require_perm('personalplaner','view')
                if not u:return
                return self.personnel_plan(parse_qs(p.query))
            if p.path=='/api/personnel/employees':
                u=self.require_perm('personalplaner','manage')
                if not u:return
                try: year=valid_personnel_year(parse_qs(p.query).get('year',[datetime.now().year])[0])
                except ValueError as e:return self.json_out({'error':str(e)},400)
                con=db_connect()
                rows=con.execute('''SELECT e.id,e.name,e.active,e.sort_order,
                    COALESCE(y.annual_vacation,0) annual_vacation,
                    COALESCE(y.carryover_vacation,0) carryover_vacation,
                    CASE WHEN y.employee_id IS NULL THEN 'unset' WHEN y.source_import_id IS NULL THEN 'manual' ELSE 'excel' END allowance_source
                    FROM personnel_employees e LEFT JOIN personnel_employee_years y
                    ON y.employee_id=e.id AND y.year=? ORDER BY e.sort_order,e.name COLLATE NOCASE''',(year,)).fetchall()
                usage=con.execute('''SELECT employee_id,
                    COALESCE(SUM(CASE WHEN category='vacation' THEN portion ELSE 0 END),0) vacation_used,
                    COALESCE(SUM(CASE WHEN category='sick' THEN portion ELSE 0 END),0) sick_days
                    FROM personnel_entries WHERE date BETWEEN ? AND ? GROUP BY employee_id''',
                    (f'{year:04d}-01-01',f'{year:04d}-12-31')).fetchall()
                usemap={r['employee_id']:r for r in usage}
                employees=[]
                for r in rows:
                    d=dict(r);used=float((usemap.get(r['id']) or {'vacation_used':0})['vacation_used'] or 0)
                    sick=float((usemap.get(r['id']) or {'sick_days':0})['sick_days'] or 0)
                    total=float(r['annual_vacation'] or 0)+float(r['carryover_vacation'] or 0)
                    d.update(vacation_total=total,vacation_used=used,vacation_remaining=total-used,sick_days=sick)
                    employees.append(d)
                con.close()
                return self.json_out({'year':year,'region':'Brandenburg','region_code':'BB','employees':employees})
            if p.path=='/api/personnel/imports':
                u=self.require_perm('personalplaner','manage')
                if not u:return
                con=db_connect()
                rows=con.execute("SELECT id,filename,sha256,year,region,employee_count,entry_count,manual_conflicts,status,created_at,committed_at FROM personnel_imports ORDER BY created_at DESC LIMIT 30").fetchall()
                con.close()
                return self.json_out({'imports':[dict(r) for r in rows]})
            if p.path=='/api/personnel/import/preview':
            u=self.require_perm('personalplaner','manage')
            if not u:return
            return self.personnel_import_preview(u)

        if p.path=='/api/personnel/import/commit':
            u=self.require_perm('personalplaner','manage')
            if not u:return
            try:b=self.read_json()
            except ValueError as e:return self.json_out({'error':str(e)},400)
            return self.personnel_import_commit(u,b)

        if p.path=='/api/personnel/employees':
            u=self.require_perm('personalplaner','manage')
            if not u:return
            con=None
            try:
                b=self.read_json();emp=validate_personnel_employee(b)
                con=db_connect()
                cur=con.execute('INSERT INTO personnel_employees(name,active,sort_order) VALUES(?,?,?)',(emp['name'],emp['active'],emp['sort_order']))
                eid=cur.lastrowid
                con.execute('''INSERT INTO personnel_employee_years(employee_id,year,annual_vacation,carryover_vacation,source_import_id)
                  VALUES(?,?,?,?,NULL)''',(eid,emp['year'],emp['annual_vacation'],emp['carryover_vacation']))
                con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',(u['id'],'personnel-employee-create',emp['name']))
                con.commit();con.close();notify_change('personnel-changed')
                return self.json_out({'ok':True,'id':eid},201)
            except sqlite3.IntegrityError:
                if con:con.rollback();con.close()
                return self.json_out({'error':'Mitarbeiter ist bereits vorhanden'},409)
            except ValueError as e:
                if con:con.rollback();con.close()
                return self.json_out({'error':str(e)},400)

        if p.path=='/api/personnel/entries':
            u=self.require_perm('personalplaner','edit')
            if not u:return
            try:
                b=self.read_json();entry=validate_personnel_entry(b)
                start_date=parse_iso_date(entry['date'])
                end_raw=clean(b.get('end_date'),10)
                end_date=parse_iso_date(end_raw) if end_raw else start_date
                if end_date<start_date or (end_date-start_date).days>366: raise ValueError('Zeitraum ist ungültig')
            except ValueError as e:return self.json_out({'error':str(e)},400)
            con=db_connect();ids=[]
            try:
                emp=con.execute('SELECT id FROM personnel_employees WHERE id=?',(entry['employee_id'],)).fetchone()
                if not emp: raise ValueError('Mitarbeiter nicht gefunden')
                day=start_date
                while day<=end_date:
                    iso=day.isoformat()
                    existing=con.execute('SELECT id FROM personnel_entries WHERE employee_id=? AND date=?',(entry['employee_id'],iso)).fetchone()
                    if existing: raise ValueError('Für diesen Mitarbeiter existiert am '+iso+' bereits ein Eintrag')
                    cur=con.execute('''INSERT INTO personnel_entries(employee_id,date,code,category,portion,label,note,source,created_by,updated_by)
                      VALUES(?,?,?,?,?,?,?,'manual',?,?)''',(entry['employee_id'],iso,entry['code'],entry['category'],entry['portion'],entry['label'],entry['note'],u['id'],u['id']))
                    ids.append(cur.lastrowid);day+=timedelta(days=1)
                con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',(u['id'],'personnel-entry-create',f"{entry['employee_id']} {start_date} bis {end_date}"))
                con.commit()
            except (ValueError,sqlite3.IntegrityError) as e:
                con.rollback();con.close()
                return self.json_out({'error':str(e)},409 if isinstance(e,sqlite3.IntegrityError) else 400)
            con.close();notify_change('personnel-changed')
            return self.json_out({'ok':True,'id':ids[0] if ids else None,'count':len(ids),'from':start_date.isoformat(),'to':end_date.isoformat()},201)

        if p.path=='/api/users':
                u=self.require(('admin',))
                if not u:return
                con=db_connect()
                rows=con.execute('SELECT id,name,role,active,created_at,updated_at FROM users ORDER BY active DESC,role,name').fetchall()
                users=[]
                for r in rows:
                    d=dict(r)
                    d['permissions']=load_permissions(con,r['id'])
                    users.append(d)
                con.close()
                return self.json_out({'users':users,'modules':list(MODULES)})
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
            con=db_connect()
            perms=load_permissions(con,row['id'])
            con.close()
            user={'id':row['id'],'name':row['name'],'role':row['role'],'permissions':perms}
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
                if pw != str(b.get('password_confirm') or pw):
                    raise ValueError('Passwörter stimmen nicht überein')
                permissions=normalize_permissions(b.get('permissions'),role)
                if role not in ('admin','editor','viewer'):
                    raise ValueError('Ungültige Rolle')
                con=db_connect()
                con.execute('INSERT INTO users(name,password_hash,role,active) VALUES(?,?,?,1)',(name,hash_password(pw),role))
                uid=con.execute('SELECT id FROM users WHERE name=?',(name,)).fetchone()[0]
                save_permissions(con,uid,permissions)
                con.commit(); con.close()
                return self.json_out({'ok':True,'id':uid},201)
            except sqlite3.IntegrityError:
                return self.json_out({'error':'Benutzername ist bereits vorhanden'},409)
            except ValueError as e:
                return self.json_out({'error':str(e)},400)

        if p.path=='/api/appointments':
            u=self.require_perm('werkstattplaner','edit')
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

        pem=re.fullmatch(r'/api/personnel/employees/(\d+)',p.path)
        if pem:
            u=self.require_perm('personalplaner','manage')
            if not u:return
            eid=int(pem.group(1))
            try:b=self.read_json();emp=validate_personnel_employee(b)
            except ValueError as e:return self.json_out({'error':str(e)},400)
            con=db_connect()
            if not con.execute('SELECT id FROM personnel_employees WHERE id=?',(eid,)).fetchone():
                con.close();return self.json_out({'error':'Mitarbeiter nicht gefunden'},404)
            try:
                con.execute('UPDATE personnel_employees SET name=?,active=?,sort_order=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(emp['name'],emp['active'],emp['sort_order'],eid))
                con.execute('''INSERT INTO personnel_employee_years(employee_id,year,annual_vacation,carryover_vacation,source_import_id)
                  VALUES(?,?,?,?,NULL) ON CONFLICT(employee_id,year) DO UPDATE SET annual_vacation=excluded.annual_vacation,
                  carryover_vacation=excluded.carryover_vacation,source_import_id=NULL,updated_at=CURRENT_TIMESTAMP''',
                  (eid,emp['year'],emp['annual_vacation'],emp['carryover_vacation']))
                con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',(u['id'],'personnel-employee-update',f"{eid} {emp['name']}"))
                con.commit()
            except sqlite3.IntegrityError:
                con.rollback();con.close();return self.json_out({'error':'Mitarbeiter ist bereits vorhanden'},409)
            con.close();notify_change('personnel-changed')
            return self.json_out({'ok':True,'year':emp['year'],'allowance_source':'manual'})

        pen=re.fullmatch(r'/api/personnel/entries/(\d+)',p.path)
        if pen:
            u=self.require_perm('personalplaner','edit')
            if not u:return
            entry_id=int(pen.group(1))
            try:b=self.read_json();entry=validate_personnel_entry(b,entry_id)
            except ValueError as e:return self.json_out({'error':str(e)},400)
            con=db_connect()
            old=con.execute('SELECT * FROM personnel_entries WHERE id=?',(entry_id,)).fetchone()
            if not old:con.close();return self.json_out({'error':'Personaleintrag nicht gefunden'},404)
            try:
                con.execute('''UPDATE personnel_entries SET employee_id=?,date=?,code=?,category=?,portion=?,label=?,note=?,
                  source='manual',source_import_id=NULL,updated_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                  (entry['employee_id'],entry['date'],entry['code'],entry['category'],entry['portion'],entry['label'],entry['note'],u['id'],entry_id))
                con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',(u['id'],'personnel-entry-update',str(entry_id)))
                con.commit()
            except sqlite3.IntegrityError:
                con.rollback();con.close();return self.json_out({'error':'Für diesen Mitarbeiter existiert an dem Tag bereits ein Eintrag'},409)
            con.close();notify_change('personnel-changed')
            return self.json_out({'ok':True})

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
                pw2=str(b.get('password_confirm') or '')
                permissions=normalize_permissions(b.get('permissions'),role)
                if role not in ('admin','editor','viewer'):
                    raise ValueError('Ungültige Rolle')
                if pw:
                    validate_password(pw)
                    if pw2 and pw!=pw2:
                        raise ValueError('Passwörter stimmen nicht überein')
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
                save_permissions(con,uid,permissions)
                con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',
                            (u['id'],'user-update',json.dumps({'target_user':uid,'role':role,'active':bool(active),'permissions':permissions},ensure_ascii=False)))
                con.commit()
            except sqlite3.IntegrityError:
                con.close()
                return self.json_out({'error':'Benutzername ist bereits vorhanden'},409)
            con.close()
            return self.json_out({'ok':True})

        m=re.fullmatch(r'/api/appointments/([^/]+)',p.path)
        if not m:
            return self.json_out({'error':'Nicht gefunden'},404)
        u=self.require_perm('werkstattplaner','edit')
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
        path=urlparse(self.path).path
        personnel_match=re.fullmatch(r'/api/personnel/entries/(\d+)',path)
        if personnel_match:
            u=self.require_perm('personalplaner','edit')
            if not u:return
            entry_id=int(personnel_match.group(1))
            con=db_connect()
            old=con.execute('SELECT * FROM personnel_entries WHERE id=?',(entry_id,)).fetchone()
            if not old:con.close();return self.json_out({'error':'Personaleintrag nicht gefunden'},404)
            con.execute('DELETE FROM personnel_entries WHERE id=?',(entry_id,))
            con.execute('INSERT INTO audit_log(user_id,action,appointment_id,details) VALUES(?,?,NULL,?)',(u['id'],'personnel-entry-delete',f"{old['date']} / Mitarbeiter {old['employee_id']} / {old['code']}"))
            con.commit();con.close();notify_change('personnel-changed')
            return self.json_out({'ok':True})
        m=re.fullmatch(r'/api/appointments/([^/]+)',urlparse(self.path).path)
        if not m:
            return self.json_out({'error':'Nicht gefunden'},404)
        u=self.require_perm('werkstattplaner','edit')
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
                    kind=EVENT_KIND if EVENT_KIND in ('appointments-changed','personnel-changed') else 'appointments-changed'
                    self.wfile.write(('event: '+kind+'\ndata: {}\n\n').encode())
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
    print(f"Ete's Werkstattplaner 1.4 auf http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

if __name__=='__main__':
    main()
