# Sicherungen werden zuerst in einem getrennten Datenbestand wiederhergestellt und geprüft, bevor sie als gültig gelten.
# Sicherungen werden unabhängig vom laufenden Datenbestand in einem privaten Staging-Verzeichnis wiederhergestellt.
import argparse,base64,hashlib,io,json,os,shutil,tempfile,threading,zipfile
from datetime import date,datetime,timedelta
from decimal import Decimal
from pathlib import Path,PurePosixPath
from uuid import uuid4
from sqlalchemy import create_engine,select,insert,inspect
from sqlalchemy.orm import Session
from .db import Base,engine
from .models import BackupRun,BackupSettings,DocumentFile,User,now_utc
from .user_directories import storage_root,ROLE_DIRECTORIES

_active=False

def encode(value):
    if isinstance(value,bytes):return {'$bytes':base64.b64encode(value).decode()}
    if isinstance(value,datetime):return {'$datetime':value.isoformat()}
    if isinstance(value,date):return {'$date':value.isoformat()}
    if isinstance(value,Decimal):return {'$decimal':str(value)}
    if value is None or isinstance(value,(str,int,float,bool)):return value
    raise ValueError('backup_type')
def decode(value):
    if not isinstance(value,dict):return value
    if set(value)=={'$bytes'}:return base64.b64decode(value['$bytes'],validate=True)
    if set(value)=={'$datetime'}:return datetime.fromisoformat(value['$datetime'])
    if set(value)=={'$date'}:return date.fromisoformat(value['$date'])
    if set(value)=={'$decimal'}:return Decimal(value['$decimal'])
    raise ValueError('backup_value')
def packed(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
def private_root(root):
    target=root/'_rail_backups'
    if target.is_symlink():raise ValueError('backup_path')
    target.mkdir(mode=0o700,exist_ok=True);target.chmod(0o700);return target

def build(path,database,root):
    from .version import SOFTWARE_VERSION
    if set(inspect(database).get_table_names())!=set(Base.metadata.tables):raise ValueError('backup_schema')
    manifest=dict(schema=1,software_version=SOFTWARE_VERSION,created_at=now_utc().isoformat(),tables={},files={})
    # Eine wiederholbare Lesetransaktion hält die Tabellen während des Exports auf demselben Stand.
    with database.connect() as connection:
        if database.dialect.name=='mysql':connection=connection.execution_options(isolation_level='REPEATABLE READ')
        with connection.begin(),zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
            for table in Base.metadata.sorted_tables:
                name='tables/'+table.name+'.jsonl';digest=hashlib.sha256();count=0
                with archive.open(name,'w',force_zip64=True) as target:
                    result=connection.execution_options(stream_results=True).execute(select(table))
                    for row in result.mappings():
                        raw=packed({k:encode(v) for k,v in row.items()})+b'\n';target.write(raw);digest.update(raw);count+=1
                    result.close()
                manifest['tables'][table.name]=dict(count=count,sha256=digest.hexdigest())
            for folder in sorted(set(ROLE_DIRECTORIES.values())):
                base=root/folder
                if not base.exists():continue
                if base.is_symlink():raise ValueError('backup_symlink')
                for source in sorted(base.rglob('*')):
                    if source.is_symlink():raise ValueError('backup_symlink')
                    if not source.is_file():continue
                    name='files/'+source.relative_to(root).as_posix();digest=hashlib.sha256();size=0
                    with source.open('rb') as incoming,archive.open(name,'w',force_zip64=True) as target:
                        for raw in iter(lambda:incoming.read(1024*1024),b''):target.write(raw);digest.update(raw);size+=len(raw)
                    manifest['files'][name]=dict(size=size,sha256=digest.hexdigest())
            archive.writestr('manifest.json',packed(manifest))
    return manifest

def verify(path):
    # Kein Produktionspfad wird beschrieben. Auch beschädigte Archive dürfen den Zielordner nicht verlassen.
    with tempfile.TemporaryDirectory(prefix='rail-restore-') as directory,zipfile.ZipFile(path) as archive:
        root=Path(directory);manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('schema')!=1 or set(manifest['tables'])!=set(Base.metadata.tables):raise ValueError('backup_schema')
        names=archive.namelist();expected={'manifest.json'}|{'tables/'+name+'.jsonl' for name in manifest['tables']}|set(manifest['files'])
        if len(names)!=len(set(names)) or set(names)!=expected:raise ValueError('backup_members')
        restored=create_engine('sqlite+pysqlite:///'+str(root/'restored.sqlite'))
        try:
            Base.metadata.create_all(restored)
            with restored.begin() as db:
                for name,info in manifest['tables'].items():
                    table=Base.metadata.tables[name];digest=hashlib.sha256();count=0;batch=[]
                    with archive.open('tables/'+name+'.jsonl') as stream:
                        for raw in stream:
                            digest.update(raw);row=json.loads(raw)
                            if set(row)!=set(table.columns.keys()):raise ValueError('backup_columns')
                            batch.append({k:decode(v) for k,v in row.items()});count+=1
                            if len(batch)>=200:db.execute(insert(table),batch);batch=[]
                    if batch:db.execute(insert(table),batch)
                    if count!=info['count'] or digest.hexdigest()!=info['sha256']:raise ValueError('backup_rows')
                if db.exec_driver_sql('PRAGMA foreign_key_check').first():raise ValueError('backup_references')
                for name,info in manifest['files'].items():
                    rel=PurePosixPath(name)
                    if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='files' or '\\' in name:raise ValueError('backup_path')
                    target=root.joinpath(*rel.parts);target.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
                    with archive.open(name) as source,target.open('wb') as output:
                        for raw in iter(lambda:source.read(1024*1024),b''):output.write(raw);digest.update(raw);size+=len(raw)
                    if size!=info['size'] or digest.hexdigest()!=info['sha256']:raise ValueError('backup_files')
                users={r.id:r for r in db.execute(select(User.id,User.username,User.role))}
                for doc in db.execute(select(DocumentFile.owner_id,DocumentFile.relative_path,DocumentFile.sha256,DocumentFile.byte_size)):
                    user=users.get(doc.owner_id)
                    if not user:raise ValueError('backup_owner')
                    name='files/'+ROLE_DIRECTORIES[user.role]+'/'+user.username+'/'+doc.relative_path;info=manifest['files'].get(name)
                    if not info or info['sha256']!=doc.sha256 or info['size']!=doc.byte_size:raise ValueError('backup_document')
            return dict(tables=len(manifest['tables']),rows=sum(v['count'] for v in manifest['tables'].values()),files=len(manifest['files']),verification='isolated-sqlite-and-files')
        finally:restored.dispose()

def execute(run_id,database=None,root=None):
    database=database or engine();root=Path(root or storage_root());partial=None
    try:
        folder=private_root(root);partial=folder/(run_id+'.partial');target=folder/(run_id+'.zip')
        with partial.open('xb'):pass
        partial.chmod(0o600);build(partial,database,root);summary=verify(partial);partial.replace(target)
        digest=hashlib.sha256()
        with target.open('rb') as file:
            for raw in iter(lambda:file.read(1024*1024),b''):digest.update(raw)
        summary['sha256']=digest.hexdigest();summary['bytes']=target.stat().st_size
        with Session(database) as db:
            row=db.get(BackupRun,run_id)
            if row:row.state='verified';row.completed_at=now_utc();row.summary_json=json.dumps(summary);db.commit()
            retained=list(db.scalars(select(BackupRun).where(BackupRun.state=='verified').order_by(BackupRun.created_at.desc())))
            for old in retained[7:]:
                file=folder/(old.id+'.zip')
                if file.is_file() and not file.is_symlink():file.unlink()
                old.state='retired'
            db.commit()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error('Sicherungsprüfung fehlgeschlagen: %s',str(exc) if isinstance(exc,ValueError) and str(exc).startswith('backup_') else type(exc).__name__)
        if partial and partial.exists():partial.unlink()
        with Session(database) as db:
            row=db.get(BackupRun,run_id)
            if row:row.state='failed';row.completed_at=now_utc();row.summary_json=json.dumps(dict(code='backup_verification_failed',error_type=type(exc).__name__));db.commit()
    finally:
        global _active
        _active=False

def tick():
    global _active
    if _active:return
    database=engine()
    with Session(database) as db:
        settings=db.scalar(select(BackupSettings).where(BackupSettings.id==1).with_for_update())
        if not settings:settings=BackupSettings(id=1,enabled=True,requested=False);db.add(settings);db.flush()
        now=now_utc();running=db.scalar(select(BackupRun).where(BackupRun.state=='running').order_by(BackupRun.created_at.desc()).limit(1))
        if running:
            if now-running.created_at<timedelta(hours=6):return
            running.state='failed';running.completed_at=now;running.summary_json='{"code":"backup_interrupted"}'
        if not settings.requested and (not settings.enabled or settings.last_started and now-settings.last_started<timedelta(days=1)):return
        settings.last_started=now;settings.requested=False;ident=uuid4().hex;db.add(BackupRun(id=ident,state='running'));db.commit();_active=True
    job=threading.Thread(target=execute,args=(ident,database,storage_root()),daemon=True,name='rail-backup');job.start();return job

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',type=Path,required=True);args=parser.parse_args();print(json.dumps(verify(args.verify)))
if __name__=='__main__':main()
