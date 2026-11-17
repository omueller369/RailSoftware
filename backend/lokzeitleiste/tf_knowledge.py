"""Private per-TF location and rolling-stock CSV inventories, with explicit confirmation."""
import csv,io,hashlib,re,unicodedata
from datetime import date
from pathlib import Path
from fastapi import APIRouter,Depends,File,Form,UploadFile,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import database_session
from .models import User,TfLocationKnowledge,TfRollingStockKnowledge
from .tf_portal import driver_dependency
from .route_knowledge_import import identity,token,text,packed,digest,MAX_BYTES,MAX_ROWS
SCHEMAS={
 'places':(TfLocationKnowledge,('Bahnhof','DS100','Kundig bis'),('station_name','ds100','known_until')),
 'classes':(TfRollingStockKnowledge,('Baureihe','Gültig bis'),('series','valid_until'))}

def schema(kind):
    if kind not in SCHEMAS:raise HTTPException(404)
    return SCHEMAS[kind]

def parse(raw,kind):
    _,headers,fields=schema(kind)
    if len(raw)>MAX_BYTES:raise ValueError(text('too_large'))
    try:
        reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';',strict=True)
        actual=next(reader,[]);trailing=actual==list(headers)+['']
        if actual!=list(headers) and not trailing:raise ValueError(text('invalid_csv'))
        records=[];seen={};duplicates=0;count=0
        for line,values in enumerate(reader,2):
            if not values:continue
            count+=1
            if count>MAX_ROWS:raise ValueError(text('too_large'))
            if trailing:
                if len(values)!=len(headers)+1 or values[-1]!='':raise ValueError(text('invalid_row')+' '+str(line))
                values=values[:-1]
            if len(values)!=len(headers) or any(not isinstance(v,str) or any(ord(c)<32 for c in v) for v in values):raise ValueError(text('invalid_row')+' '+str(line))
            row=dict(zip(fields,values));last=values[-1]
            if last not in {'','-','0000-00-00'}:
                try:
                    if date.fromisoformat(last).isoformat()!=last:raise ValueError()
                except ValueError:raise ValueError(text('invalid_row')+' '+str(line)) from None
            if kind=='places':valid=bool(row['station_name'].strip()) and len(row['station_name'])<=200 and bool(row['ds100'].strip()) and len(row['ds100'])<=10;key=row['ds100']
            else:valid=bool(row['series'].strip()) and len(row['series'])<=80;key=row['series']
            if not valid:raise ValueError(text('invalid_row')+' '+str(line))
            identity_key=digest(unicodedata.normalize('NFC',key.strip()).upper());content=digest(packed(row))
            if identity_key in seen:
                if seen[identity_key]!=content:raise ValueError(text('invalid_row')+' '+str(line))
                duplicates+=1;continue
            seen[identity_key]=content;records.append(dict(identity_key=identity_key,content_sha256=content,**row))
        if not records:raise ValueError(text('empty_csv'))
        return dict(records=records,file_sha256=hashlib.sha256(raw).hexdigest(),source_rows=count,duplicates=duplicates)
    except (UnicodeDecodeError,csv.Error):raise ValueError(text('invalid_csv')) from None

def existing(db,model,owner,lock=False):
    query=select(model).where(model.owner_id==owner)
    if lock:query=query.with_for_update()
    return {r.identity_key:r.content_sha256 for r in db.scalars(query)}

def summary(data,old):
    result={k:data[k] for k in ['file_sha256','source_rows','duplicates']};result.update(added=0,existing=0,conflicts=0)
    for row in data['records']:
        previous=old.get(row['identity_key']);result['added' if previous is None else 'existing' if previous==row['content_sha256'] else 'conflicts']+=1
    return result

def public_items(data,fields):return [{k:row[k] for k in fields} for row in data['records']]

def create_router(require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/tf/knowledge-inventory.js')
    def script():
        from fastapi.responses import FileResponse
        return FileResponse(Path(__file__).parent/'static'/'knowledge-inventory.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/knowledge/{kind}')
    def listing(kind:str,user:User=Depends(driver),db:Session=Depends(database_session)):
        model,_,fields=schema(kind);target=identity(db,user)
        return dict(identity=target,items=[dict(id=r.id,**{k:getattr(r,k) for k in fields}) for r in db.scalars(select(model).where(model.owner_id==user.id).order_by(model.id))])
    def read(file,kind):
        raw=file.file.read(MAX_BYTES+1)
        try:return parse(raw,kind)
        except ValueError as exc:raise HTTPException(413 if len(raw)>MAX_BYTES else 422,str(exc)) from None
    @router.post('/api/v1/tf/knowledge/{kind}/preview')
    def preview(kind:str,file:UploadFile=File(...),user:User=Depends(driver),db:Session=Depends(database_session)):
        model,_,fields=schema(kind);data=read(file,kind);target=identity(db,user)
        return dict(identity=target,owner_token=token(target),summary=summary(data,existing(db,model,user.id)),items=public_items(data,fields))
    @router.post('/api/v1/tf/knowledge/{kind}')
    def apply(kind:str,file:UploadFile=File(...),owner_token:str=Form(...),expected_sha256:str=Form(...),confirmed:bool=Form(False),user:User=Depends(driver),db:Session=Depends(database_session)):
        model,_,fields=schema(kind)
        if not confirmed:raise HTTPException(422,text('confirmation'))
        data=read(file,kind)
        if data['file_sha256']!=expected_sha256:raise HTTPException(409,text('file_changed'))
        current=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
        if current is None or not current.active or current.role!='tf':raise HTTPException(403,text('identity_error'))
        target=identity(db,current,lock=True)
        if token(target)!=owner_token:raise HTTPException(409,text('identity_error'))
        old=existing(db,model,user.id,lock=True);result=summary(data,old)
        for row in data['records']:
            if row['identity_key'] not in old:db.add(model(owner_id=user.id,**row))
        db.commit();return dict(identity=target,summary=result)
    return router
