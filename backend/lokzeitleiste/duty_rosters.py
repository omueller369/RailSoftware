# Excel-Inhalte werden nur gelesen. Erst die bestätigte Zuordnung veröffentlicht einzelne Zeilen.
import hashlib,io,json,re,zipfile,unicodedata
from datetime import datetime,date,time,timedelta
from pathlib import Path,PurePosixPath
from fastapi import APIRouter,Depends,File,Form,UploadFile,HTTPException,Query
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from sqlalchemy import select,delete,insert
from sqlalchemy.orm import Session
from .db import database_session
from .models import DutyRosterImport,DutyRosterEntry,DutyRosterPublication,User,TfProfile,now_utc
from .tf_portal import driver_dependency
from .localization import source

FIELDS=('sequence','shift_no','provider','activity','from_station','preparation','duty_start','departure','to_station','arrival','completion','duty_end','locomotives','work_time','rotation','reference','comment','work_hours','shift_hours','date')
DATE_FIELDS={'duty_start','departure','arrival','duty_end','date'}
MAX_FILE=10*1024*1024

def invalid(status=422):return HTTPException(status,source('coordination.text_54326bbe8493'))

def is_pause(value):
    return str(value or '').strip().casefold()=='pause'

def activity_column(columns):
    names={'typ der zugfahrt','z-art/p','zugart/pause','zugart'}
    return next((i for i,value in enumerate(columns) if str(value).strip().casefold() in names),None)

def remove_pause_entries(db):
    # Nur veröffentlichte Dienstplanzeilen löschen. Erfasste Arbeitsberichtspausen bleiben unberührt.
    ids=[]
    for entry_id,raw in db.execute(select(DutyRosterEntry.id,DutyRosterEntry.payload_json)).yield_per(200):
        try:payload=json.loads(raw)
        except (TypeError,ValueError):continue
        if isinstance(payload,dict) and is_pause(payload.get('activity')):ids.append(entry_id)
    for offset in range(0,len(ids),500):db.execute(delete(DutyRosterEntry).where(DutyRosterEntry.id.in_(ids[offset:offset+500])))
    return len(ids)

def publication(db):
    # Die einzelne Veröffentlichungszeile serialisiert Bestätigungen auch über mehrere Sachbearbeiter.
    statement=insert(DutyRosterPublication).values(id=1)
    dialect=db.get_bind().dialect.name
    if dialect=='sqlite':statement=statement.prefix_with('OR IGNORE')
    elif dialect in ('mysql','mariadb'):statement=statement.prefix_with('IGNORE')
    else:raise RuntimeError('Unsupported roster database')
    db.execute(statement)
    return db.scalar(select(DutyRosterPublication).where(DutyRosterPublication.id==1).with_for_update().execution_options(populate_existing=True))

def latest_confirmed(db):
    return db.scalar(select(DutyRosterImport.id).where(DutyRosterImport.confirmation_sha256.is_not(None)).order_by(DutyRosterImport.id.desc()).limit(1))

def remember_legacy(db,rows):
    grouped={}
    for row in rows:grouped.setdefault(row.import_id,[]).append(row)
    for import_id,entries in grouped.items():
        batch=db.get(DutyRosterImport,import_id)
        if not batch:continue
        try:preview=json.loads(batch.preview_json)
        except (TypeError,ValueError):continue
        if '_publication' in preview:continue
        preview['_publication']=dict(assignments={row.source_row:row.tf_user_id for row in entries},entries=[dict(row=row.source_row,tf_user_id=row.tf_user_id,date=row.date,values=json.loads(row.payload_json)) for row in entries])
        batch.preview_json=json.dumps(preview,ensure_ascii=False)

def migrate_publication(db):
    active=publication(db)
    # Ältere Installationen kennen noch keinen Bestätigungszeitpunkt. Der jüngste bestätigte Upload führt.
    if active.import_id is None:active.import_id=latest_confirmed(db)
    remember_legacy(db,list(db.scalars(select(DutyRosterEntry))))
    query=delete(DutyRosterEntry)
    if active.import_id is not None:query=query.where(DutyRosterEntry.import_id!=active.import_id)
    db.execute(query)

def cell_text(value):
    if value is None:return ''
    if isinstance(value,(datetime,date,time)):return value.isoformat()
    if isinstance(value,float) and value.is_integer():return str(int(value))
    return str(value)[:2000]

def workbook(content,filename,sheet,header):
    # Formeln werden weder ausgewertet noch an Office weitergereicht. ZIP-Größen begrenzen.
    if filename.lower().endswith('.xlsx'):
        import openpyxl
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(row.file_size for row in archive.infolist())>50*1024*1024:raise invalid(413)
        book=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True,keep_links=False)
        try:
            names=book.sheetnames
            if not 0<=sheet<len(names):raise invalid()
            tab=book[names[sheet]]
            if tab.max_row>3000 or tab.max_column>60:raise invalid(413)
            cells=[[cell_text(c) for c in row] for row in tab.iter_rows(values_only=True)]
        finally:book.close()
    elif filename.lower().endswith('.xls'):
        import xlrd
        book=xlrd.open_workbook(file_contents=content,on_demand=True)
        try:
            names=book.sheet_names()
            if not 0<=sheet<len(names):raise invalid()
            tab=book.sheet_by_index(sheet)
            if tab.nrows>3000 or tab.ncols>60:raise invalid(413)
            cells=[]
            for row in range(tab.nrows):
                values=[]
                for col in range(tab.ncols):
                    c=tab.cell(row,col)
                    if c.ctype==xlrd.XL_CELL_ERROR:values.append('');continue
                    value=xlrd.xldate_as_datetime(c.value,book.datemode) if c.ctype==xlrd.XL_CELL_DATE else c.value
                    values.append(cell_text(value))
                cells.append(values)
        finally:book.release_resources()
    else:raise invalid()
    if header==0:
        header=next((i+1 for i,row in enumerate(cells) if 'Tf' in row and 'Dienstbeginn' in row),1)
    if not 1<=header<=len(cells):raise invalid()
    width=max(map(len,cells),default=0)
    columns=[cells[header-1][i] if i<len(cells[header-1]) else '' for i in range(width)]
    rows=[dict(row=i+1,values=row+['']*(width-len(row))) for i,row in enumerate(cells) if i>=header and any(v.strip() for v in row)]
    # Wiederholte Druckkopfzeilen sind keine geplanten Dienste.
    header_columns=[i for i,value in enumerate(columns) if value.strip()]
    if len(header_columns)>=2:rows=[r for r in rows if not all(r['values'][i].strip()==columns[i].strip() for i in header_columns)]
    column=activity_column(columns);skipped=0
    if column is not None:
        kept=[row for row in rows if not is_pause(row['values'][column])];skipped=len(rows)-len(kept);rows=kept
    return dict(sheets=names,sheet=sheet,header=header,columns=columns,rows=rows,skipped_pauses=skipped)

def parse_date(value):
    if not value:return None
    value=value.strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S','%Y-%m-%dT%H:%M','%Y-%m-%d','%d.%m.%Y %H:%M','%d.%m.%Y %H:%M:%S','%d.%m.%Y'):
        try:
            parsed=datetime.strptime(value,fmt)
            if not 2000<=parsed.year<=2100:raise invalid()
            return parsed
        except ValueError:pass
    raise invalid()

class Assignment(BaseModel):
    row:int=Field(ge=1,le=3000)
    tf_user_id:int=Field(ge=1)
class Confirm(BaseModel):
    columns:dict[str,int]=Field(max_length=20)
    assignments:list[Assignment]=Field(min_length=1,max_length=3000)


def create_router(require_admin,require_account):
    router=APIRouter();driver=driver_dependency(require_account);static=Path(__file__).parent/'static'
    @router.get('/admin/dienstplan')
    @router.get('/tf/dienstplan')
    def page():return FileResponse(static/'duty-rosters.html')
    @router.get('/tf/duty-rosters.js')
    def script():return FileResponse(static/'duty-rosters.js',media_type='text/javascript')
    @router.get('/api/v1/admin/duty-rosters/recipients')
    def recipients(user=Depends(require_admin),db:Session=Depends(database_session)):
        return [dict(id=u.id,name=(p.first_name+' '+p.last_name).strip(),number=u.username) for u,p in db.execute(select(User,TfProfile).join(TfProfile,TfProfile.user_id==User.id).where(User.role=='tf',User.active==True).order_by(TfProfile.last_name,TfProfile.first_name))]
    @router.post('/api/v1/admin/duty-rosters/preview')
    async def preview(file:UploadFile=File(),sheet:int=Form(default=0,ge=0,le=100),header:int=Form(default=0,ge=0,le=3000),user=Depends(require_admin),db:Session=Depends(database_session)):
        try:content=await file.read(MAX_FILE+1)
        finally:await file.close()
        if not content or len(content)>MAX_FILE:raise invalid(413)
        filename=PurePosixPath((file.filename or '').replace('\\','/')).name[:200]
        try:value=workbook(content,filename,sheet,header)
        except HTTPException:raise
        except Exception as error:raise invalid() from error
        # Beim nächsten Upload werden unbestätigte Vorschauen entfernt, die älter als sieben Tage sind.
        cutoff=now_utc()-timedelta(days=7)
        db.execute(delete(DutyRosterImport).where(DutyRosterImport.confirmation_sha256.is_(None),DutyRosterImport.created_at<cutoff))
        row=DutyRosterImport(uploader_id=user.id,filename=filename,source_sha256=hashlib.sha256(content).hexdigest(),preview_json=json.dumps(value,ensure_ascii=False));db.add(row);db.commit()
        suggestions={}
        if 'Tf' in value['columns']:
            column=value['columns'].index('Tf')
            def normalized(name):
                name=re.sub(r'[0-9,;./\-]+',' ',name)
                return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',name).casefold() if not unicodedata.combining(c)).split())
            profiles=list(db.execute(select(User,TfProfile).join(TfProfile,TfProfile.user_id==User.id).where(User.role=='tf',User.active==True)))
            for item in value['rows']:
                matches=[u.id for u,p in profiles if normalized(item['values'][column])==normalized(p.last_name+' '+p.first_name)]
                if len(matches)==1:suggestions[str(item['row'])]=matches[0]
        return dict(id=row.id,suggestions=suggestions,**value)
    @router.post('/api/v1/admin/duty-rosters/{import_id}/confirm')
    def confirm(import_id:int,data:Confirm,user=Depends(require_admin),db:Session=Depends(database_session)):
        active=publication(db)
        batch=db.scalar(select(DutyRosterImport).where(DutyRosterImport.id==import_id,DutyRosterImport.uploader_id==user.id).with_for_update())
        if not batch:raise invalid(404)
        preview=json.loads(batch.preview_json);mapping=data.columns
        if not mapping or not set(mapping)<=set(FIELDS) or len(set(mapping.values()))!=len(mapping) or any(c<0 or c>=len(preview['columns']) for c in mapping.values()):raise invalid()
        if not set(mapping)&{'date','duty_start','departure'}:raise invalid()
        selection={a.row:a.tf_user_id for a in data.assignments}
        if len(selection)!=len(data.assignments):raise invalid()
        available={r['row']:r['values'] for r in preview['rows']}
        if not set(selection)<=set(available):raise invalid()
        original_selection=dict(selection);column=mapping.get('activity',activity_column(preview['columns']))
        if column is not None:selection={row:owner for row,owner in selection.items() if not is_pause(available[row][column])}
        skipped=int(preview.get('skipped_pauses',0))+len(original_selection)-len(selection)
        eligible=set(db.scalars(select(User.id).where(User.role=='tf',User.active==True)))
        if not set(selection.values())<=eligible:raise invalid()
        def fingerprint_for(assignments):return hashlib.sha256(json.dumps([batch.source_sha256,preview['sheet'],preview['header'],sorted(mapping.items()),sorted(assignments.items())],sort_keys=True).encode()).hexdigest()
        fingerprint=fingerprint_for(selection);legacy_fingerprint=fingerprint_for(original_selection)
        confirmed=preview.get('_publication',{})
        if batch.confirmation_sha256:
            expected=confirmed.get('fingerprint') or batch.confirmation_sha256
            if expected not in (fingerprint,legacy_fingerprint):raise invalid(409)
            current=active.import_id if active.import_id is not None else latest_confirmed(db)
            return dict(count=len(selection),skipped_pauses=skipped,already_imported=True,superseded=current!=batch.id)
        if not selection:raise invalid()
        entries=[]
        for index,owner in selection.items():
            values=available[index];payload={field:values[col] for field,col in mapping.items()};dates={key:parse_date(payload.get(key)) for key in DATE_FIELDS if payload.get(key)}
            main=dates.get('duty_start') or dates.get('departure') or dates.get('date')
            if not main:raise invalid()
            if dates.get('duty_end') and dates.get('duty_start') and dates['duty_end']<dates['duty_start']:raise invalid()
            entries.append(DutyRosterEntry(import_id=batch.id,source_row=index,tf_user_id=owner,date=main.date().isoformat(),payload_json=json.dumps(payload,ensure_ascii=False)))
        def equivalent(row):return (row.source_row,row.tf_user_id,row.date,json.dumps(json.loads(row.payload_json),sort_keys=True,ensure_ascii=False))
        old=list(db.scalars(select(DutyRosterEntry).with_for_update()));remember_legacy(db,old)
        unchanged=sorted(equivalent(row) for row in old)==sorted(equivalent(row) for row in entries)
        # Erst nach vollständiger Prüfung ersetzen. Arbeitsberichte und deren Ist-Zeiten sind unberührt.
        db.execute(delete(DutyRosterEntry));db.add_all(entries)
        preview['_publication']=dict(fingerprint=fingerprint,columns=mapping,assignments=selection,published_at=now_utc().isoformat())
        batch.preview_json=json.dumps(preview,ensure_ascii=False)
        # Derselbe Dateiinhalt darf später ausdrücklich erneut zur letzten Version werden.
        # Die Bestätigung derselben Vorschau bleibt dagegen idempotent und reaktiviert nichts.
        batch.confirmation_sha256=hashlib.sha256((str(batch.id)+':'+fingerprint).encode()).hexdigest()
        active.import_id=batch.id;active.published_at=now_utc();db.commit()
        return dict(count=len(selection),skipped_pauses=skipped,already_imported=unchanged,superseded=False,replaced=len(old))
    @router.get('/api/v1/tf/duty-rosters/version')
    def version(user=Depends(driver),db:Session=Depends(database_session)):
        active=db.get(DutyRosterPublication,1)
        return dict(import_id=active.import_id if active else latest_confirmed(db))
    @router.get('/api/v1/tf/duty-rosters')
    def own(start:str=Query(default='',max_length=10),end:str=Query(default='',max_length=10),user=Depends(driver),db:Session=Depends(database_session)):
        if start:parse_date(start)
        if end:parse_date(end)
        active=db.get(DutyRosterPublication,1);current=active.import_id if active else latest_confirmed(db)
        if current is None:return []
        query=select(DutyRosterEntry).where(DutyRosterEntry.tf_user_id==user.id,DutyRosterEntry.import_id==current)
        if start:parse_date(start);query=query.where(DutyRosterEntry.date>=start)
        if end:parse_date(end);query=query.where(DutyRosterEntry.date<=end)
        rows=db.scalars(query.order_by(DutyRosterEntry.date,DutyRosterEntry.id).limit(1000))
        return [dict(id=r.id,import_id=r.import_id,date=r.date,values=json.loads(r.payload_json)) for r in rows]
    return router
