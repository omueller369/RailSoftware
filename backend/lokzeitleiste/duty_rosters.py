# Excel-Inhalte werden nur gelesen. Erst die bestätigte Zuordnung veröffentlicht einzelne Zeilen.
import hashlib,io,json,re,zipfile,unicodedata
from datetime import datetime,date,time,timedelta
from pathlib import Path,PurePosixPath
from fastapi import APIRouter,Depends,File,Form,UploadFile,HTTPException,Query
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from sqlalchemy import select,delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import database_session
from .models import DutyRosterImport,DutyRosterEntry,User,TfProfile,now_utc
from .tf_portal import driver_dependency
from .localization import source

FIELDS=('sequence','shift_no','provider','activity','from_station','preparation','duty_start','departure','to_station','arrival','completion','duty_end','locomotives','work_time','rotation','reference','comment','work_hours','shift_hours','date')
DATE_FIELDS={'duty_start','departure','arrival','duty_end','date'}
MAX_FILE=10*1024*1024

def invalid(status=422):return HTTPException(status,source('coordination.text_54326bbe8493'))

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
    return dict(sheets=names,sheet=sheet,header=header,columns=columns,rows=rows)

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
        batch=db.scalar(select(DutyRosterImport).where(DutyRosterImport.id==import_id,DutyRosterImport.uploader_id==user.id).with_for_update())
        if not batch:raise invalid(404)
        preview=json.loads(batch.preview_json);mapping=data.columns
        if not mapping or not set(mapping)<=set(FIELDS) or len(set(mapping.values()))!=len(mapping) or any(c<0 or c>=len(preview['columns']) for c in mapping.values()):raise invalid()
        if not set(mapping)&{'date','duty_start','departure'}:raise invalid()
        selection={a.row:a.tf_user_id for a in data.assignments}
        if len(selection)!=len(data.assignments):raise invalid()
        eligible=set(db.scalars(select(User.id).where(User.role=='tf',User.active==True)))
        if not set(selection.values())<=eligible:raise invalid()
        fingerprint=hashlib.sha256(json.dumps([batch.source_sha256,preview['sheet'],preview['header'],sorted(mapping.items()),sorted(selection.items())],sort_keys=True).encode()).hexdigest()
        existing=db.scalar(select(DutyRosterImport).where(DutyRosterImport.confirmation_sha256==fingerprint))
        if existing:return dict(count=len(selection),already_imported=True)
        if batch.confirmation_sha256:raise invalid(409)
        available={r['row']:r['values'] for r in preview['rows']}
        if not set(selection)<=set(available):raise invalid()
        entries=[]
        for index,owner in selection.items():
            values=available[index];payload={field:values[col] for field,col in mapping.items()};dates={key:parse_date(payload.get(key)) for key in DATE_FIELDS if payload.get(key)}
            main=dates.get('duty_start') or dates.get('departure') or dates.get('date')
            if not main:raise invalid()
            if dates.get('duty_end') and dates.get('duty_start') and dates['duty_end']<dates['duty_start']:raise invalid()
            entries.append(DutyRosterEntry(import_id=batch.id,source_row=index,tf_user_id=owner,date=main.date().isoformat(),payload_json=json.dumps(payload,ensure_ascii=False)))
        db.add_all(entries);batch.confirmation_sha256=fingerprint
        try:db.commit()
        except IntegrityError:
            db.rollback()
            if db.scalar(select(DutyRosterImport.id).where(DutyRosterImport.confirmation_sha256==fingerprint)):return dict(count=len(selection),already_imported=True)
            raise invalid(409)
        return dict(count=len(entries),already_imported=False)
    @router.get('/api/v1/tf/duty-rosters')
    def own(start:str=Query(default='',max_length=10),end:str=Query(default='',max_length=10),user=Depends(driver),db:Session=Depends(database_session)):
        query=select(DutyRosterEntry).where(DutyRosterEntry.tf_user_id==user.id)
        if start:parse_date(start);query=query.where(DutyRosterEntry.date>=start)
        if end:parse_date(end);query=query.where(DutyRosterEntry.date<=end)
        rows=db.scalars(query.order_by(DutyRosterEntry.date,DutyRosterEntry.id).limit(1000))
        return [dict(id=r.id,date=r.date,values=json.loads(r.payload_json)) for r in rows]
    return router
