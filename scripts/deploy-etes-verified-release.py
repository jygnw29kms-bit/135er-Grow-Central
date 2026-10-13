"""Root-only deployment on the existing Grow-Central planner host."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

SERVICE='etes-werkstattplaner'
APP=Path('/opt/etes-werkstattplaner')
DATA=Path('/var/lib/etes-werkstattplaner')
DB=DATA/'werkstattplaner.sqlite'

def run(*args,**kwargs):
    return subprocess.run(args,check=True,**kwargs)

def output(*args):
    return subprocess.check_output(args,text=True).strip()

def counts(db):
    with sqlite3.connect(db) as con:
        return {table:con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                for table in ('users','appointments','personnel_employees','personnel_entries','vacation_requests','work_time_entries')}

def backup_db(target):
    source=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
    destination=sqlite3.connect(target)
    try:source.backup(destination)
    finally:destination.close();source.close()

def health(url,version):
    for attempt in range(30):
        try:
            with urllib.request.urlopen(url,timeout=5) as response:
                status=json.load(response)
            if status.get('ok') and status.get('version')==version and status.get('configured'):
                return
        except (OSError,ValueError):pass
        time.sleep(.3)
    raise RuntimeError('Health/version verification failed: '+url)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--package',required=True,type=Path)
    ap.add_argument('--sha256',required=True)
    ap.add_argument('--version',required=True)
    args=ap.parse_args()
    if os.geteuid()!=0:raise RuntimeError('Root permission required')
    if hashlib.sha256(args.package.read_bytes()).hexdigest()!=args.sha256:raise RuntimeError('Package checksum mismatch')
    if output('dpkg-deb','-f',str(args.package),'Package')!=SERVICE:raise RuntimeError('Unexpected package')
    if output('dpkg-deb','-f',str(args.package),'Version')!=args.version+'-1':raise RuntimeError('Unexpected version')
    if APP.resolve()!=APP or not DB.is_file():raise RuntimeError('Canonical application/database missing')
    if output('systemctl','show',SERVICE,'-p','WorkingDirectory','--value')!=str(APP):raise RuntimeError('Unexpected service path')
    pid=output('systemctl','show',SERVICE,'-p','MainPID','--value')
    selected={}
    for item in Path('/proc/'+pid+'/environ').read_bytes().split(b'\0'):
        key,separator,value=item.partition(b'=')
        if separator and key in (b'DATA_DIR',b'PORT',b'COOKIE_SECURE'):
            selected[key.decode()]=value.decode()
    if selected.get('DATA_DIR')!=str(DATA) or selected.get('PORT','3080')!='3080' or selected.get('COOKIE_SECURE','1')!='1':
        raise RuntimeError('Unexpected production runtime configuration')
    lock=Path('/run/lock/etes-werkstattplaner-release.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.umask(0o077)
    stamp=datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y%m%d-%H%M%S')
    backup=Path('/var/backups/etes-werkstattplaner')/(stamp+'-'+args.version)
    backup.mkdir(parents=True,mode=0o700)
    rollback=backup/'rollback-package'
    (rollback/'DEBIAN').mkdir(parents=True)
    old_version=output('dpkg-query','-W','-f=${Version}',SERVICE)
    for name in ('control','postinst','prerm','postrm','conffiles'):
        if name=='control':
            (rollback/'DEBIAN/control').write_text('Package: '+SERVICE+'\nVersion: '+old_version+'\nArchitecture: all\nMaintainer: Etes Autoservice\nDescription: Verified rollback of existing planner installation\n')
        else:
            existing=Path('/var/lib/dpkg/info')/(SERVICE+'.'+name)
            if existing.is_file():shutil.copy2(existing,rollback/'DEBIAN'/name)
    for name in (APP,Path('/lib/systemd/system/'+SERVICE+'.service'),Path('/usr/sbin/'+SERVICE+'-user'),Path('/etc/default/'+SERVICE)):
        target=rollback/str(name).lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True)
        if name.is_dir():shutil.copytree(name,target,symlinks=True)
        elif name.exists():shutil.copy2(name,target)
    # Keep backup parent private, but preserve installed directory modes in the package.
    (rollback/'DEBIAN').chmod(0o755)
    (rollback/'DEBIAN/control').chmod(0o644)
    for directory in rollback.rglob('*'):
        if directory.is_dir() and not directory.is_symlink() and 'DEBIAN' not in directory.relative_to(rollback).parts:
            original=Path('/')/directory.relative_to(rollback)
            directory.chmod(stat.S_IMODE(original.stat().st_mode) if original.is_dir() else 0o755)
    old_deb=backup/'rollback.deb'
    run('dpkg-deb','--build','--root-owner-group',str(rollback),str(old_deb),stdout=subprocess.DEVNULL)
    timezone_file=Path('/etc/systemd/system/'+SERVICE+'.service.d/99-etes-berlin.conf')
    previous_timezone=timezone_file.read_bytes() if timezone_file.exists() else None
    old_health=json.load(urllib.request.urlopen('http://127.0.0.1:3080/health',timeout=5))
    run('systemctl','stop',SERVICE)
    try:
        backup_db(backup/'database.sqlite')
        original_counts=counts(backup/'database.sqlite')
        with tempfile.TemporaryDirectory(prefix='etes-release-migration-') as folder:
            staging=Path(folder)
            run('dpkg-deb','-x',str(args.package),str(staging))
            migration_data=staging/'migration-data';migration_data.mkdir()
            shutil.copy2(backup/'database.sqlite',migration_data/'werkstattplaner.sqlite')
            runtime=os.environ.copy();runtime['DATA_DIR']=str(migration_data)
            run('python3','-c','import server; server.init_db()',cwd=staging/'opt/etes-werkstattplaner',env=runtime)
            if counts(migration_data/'werkstattplaner.sqlite')!=original_counts:raise RuntimeError('Migration changed record counts')
        timezone_file.parent.mkdir(parents=True,exist_ok=True)
        timezone_file.write_text('[Service]\nEnvironment=TZ=Europe/Berlin\n')
        run('dpkg','--force-confold','-i',str(args.package))
        run('systemctl','daemon-reload');run('systemctl','restart',SERVICE)
        health('http://127.0.0.1:3080/health',args.version)
        health('https://werkstattplaner.grow-central.de/health',args.version)
        run('systemctl','is-active','--quiet',SERVICE)
        print('Deployment verified:',args.version,'timezone Europe/Berlin; backup:',backup)
    except Exception:
        run('systemctl','stop',SERVICE)
        if (backup/'database.sqlite').exists():
            for suffix in ('-wal','-shm'):Path(str(DB)+suffix).unlink(missing_ok=True)
            shutil.copyfile(backup/'database.sqlite',DB)
            shutil.chown(DB,user='werkstattplaner',group='werkstattplaner')
        if previous_timezone is None:timezone_file.unlink(missing_ok=True)
        else:timezone_file.write_bytes(previous_timezone)
        run('dpkg','--force-confold','-i',str(old_deb))
        run('systemctl','daemon-reload');run('systemctl','restart',SERVICE)
        health('http://127.0.0.1:3080/health',old_health['version'])
        raise

if __name__=='__main__':main()
