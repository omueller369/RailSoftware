"""Private, verbatim knowledge imports. Never manufacture GPS points or passage credits."""
import csv,hashlib,io,json,re,unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import database_session
from .models import User,TfProfile,TfEmployment,RouteKnowledgeImport,RouteKnowledgeEntry
from .tf_portal import driver_dependency
from .route_knowledge_mapping import match as map_match,match_counts
from .localization import source as _text_source

KEYS={'title': 'route_csv.text_954717c83530', 'explain': 'route_csv.text_5374ddda8b31', 'file': 'route_csv.text_644bc976c685', 'preview': 'route_csv.text_37a53c653a36', 'apply': 'route_csv.text_38f5f91b7340', 'cancel': 'route_csv.text_f7ff1178af20', 'reload': 'route_csv.text_61a85dcd9f74', 'owner': 'route_csv.text_88b8088fee39', 'tf': 'route_csv.text_b6aceed73ea2', 'rows': 'route_csv.text_b0f5ce1bc0f6', 'new': 'route_csv.text_d9b1e13f3b97', 'existing': 'route_csv.text_fe250e7c72ea', 'conflicts': 'route_csv.text_70c3b3218a55', 'duplicates': 'route_csv.text_b94a7c8d6b07', 'unknown_dates': 'route_csv.text_3728dc519b01', 'saved': 'route_csv.text_6a914910f0b8', 'saved_reload': 'route_csv.text_d8acd525c1dd', 'empty': 'route_csv.text_1b913168fd2f', 'offline': 'route_csv.text_33e8958628af', 'error': 'route_csv.text_59fdcc2e3bf6', 'cache_error': 'route_csv.text_ba504d62b659', 'search': 'route_csv.text_d4383a843f93', 'all': 'route_csv.text_23ee74c4a81b', 'section': 'route_csv.text_4415abaef531', 'route': 'route_csv.text_5bc0b1861aef', 'status': 'route_csv.text_920e413c7d41', 'until': 'route_csv.text_ad350696ac38', 'since': 'route_csv.text_4e6f3b5fcc15', 'trips': 'route_csv.text_63f8b3f7d71b', 'from': 'route_csv.text_640e86cbc244', 'to': 'route_csv.text_078a815372af', 'qualified': 'route_csv.text_202d0cda8d0e', 'expired': 'route_csv.text_842f207c8543', 'acquiring': 'route_csv.text_7751ed14bc89', 'previous': 'route_csv.text_548611ce58f7', 'next': 'route_csv.text_1e14bdf34c3b', 'page': 'route_csv.text_e45a825b2f9a', 'invalid_csv': 'route_csv.text_de6de5a05ef8', 'invalid_row': 'route_csv.text_66ef13006ceb', 'too_large': 'route_csv.text_e4d68b32d733', 'empty_csv': 'route_csv.text_00d01502c539', 'identity_error': 'route_csv.text_c46e7b5993eb', 'file_changed': 'route_csv.text_47df666bbf20', 'confirmation': 'route_csv.text_bedf834c23b7', 'profile_missing': 'route_csv.text_7bf23e81e184', 'help': 'route_csv.text_daad55ef168f', 'history': 'route_csv.text_306348eb1b4f'}
HEADERS=('Streckenabschnitt','VzG-Nummer','Status','Gültig bis','Erwerb seit','Erwerbsfahrten','Von','Bis')
FIELDS=('section','route_number','status','valid_until','acquired_since','acquisition_trips','from_code','to_code')
STATUSES={'streckenkundig','abgelaufen','wird erworben'}
MAX_BYTES=4*1024*1024
MAX_ROWS=20000

def text(key):return _text_source(KEYS[key])
def packed(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def digest(value):return hashlib.sha256(value.encode()).hexdigest()

def parse_csv(raw):
    if len(raw)>MAX_BYTES:raise ValueError(text('too_large'))
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';',strict=True)
        if tuple(reader.fieldnames or ())!=HEADERS:raise ValueError(text('invalid_csv'))
        records=[];seen={};duplicates=0;count=0;unknown_dates=0
        for line,values in enumerate(reader,2):
            count+=1
            if count>MAX_ROWS:raise ValueError(text('too_large'))
            valid=set(values)==set(HEADERS) and all(isinstance(v,str) and len(v)<=512 and not any(ord(c)<32 for c in v) for v in values.values())
            if not valid:raise ValueError(text('invalid_row')+' '+str(line))
            row=dict(zip(FIELDS,(values[k] for k in HEADERS)))
            valid=bool(row['section'].strip()) and bool(re.fullmatch(r'[0-9]{1,6}',row['route_number'])) and row['status'] in STATUSES and bool(row['from_code'].strip()) and bool(row['to_code'].strip())
            valid=valid and (row['acquisition_trips'] in {'','-'} or bool(re.fullmatch(r'[0-9]{1,6}',row['acquisition_trips'])))
            for key in ['valid_until','acquired_since']:
                value=row[key]
                if value in {'','-','0000-00-00'}:continue
                try:valid=valid and date.fromisoformat(value).isoformat()==value
                except ValueError:valid=False
            if not valid:raise ValueError(text('invalid_row')+' '+str(line))
            content=packed(row)
            identity=[str(int(row['route_number'])),unicodedata.normalize('NFC',row['from_code'].strip()).upper(),unicodedata.normalize('NFC',row['to_code'].strip()).upper()]
            key=digest(packed(identity));content_hash=digest(content)
            if key in seen:
                if seen[key]!=content_hash:raise ValueError(text('invalid_row')+' '+str(line))
                duplicates+=1;continue
            seen[key]=content_hash
            unknown_dates+=row['valid_until'] in {'','-','0000-00-00'}
            records.append(dict(section_key=key,content_sha256=content_hash,source_json=content))
        if not records:raise ValueError(text('empty_csv'))
        return dict(file_sha256=hashlib.sha256(raw).hexdigest(),source_rows=count,duplicates=duplicates,unknown_dates=unknown_dates,statuses=dict(Counter(json.loads(r['source_json'])['status'] for r in records)),records=records)
    except (UnicodeDecodeError,csv.Error):raise ValueError(text('invalid_csv')) from None

def identity(db,user,lock=False):
    profile=db.scalar(select(TfProfile).where(TfProfile.user_id==user.id).with_for_update()) if lock else db.get(TfProfile,user.id)
    employment=db.scalar(select(TfEmployment).where(TfEmployment.user_id==user.id).with_for_update()) if lock else db.get(TfEmployment,user.id)
    if not profile:raise HTTPException(409,text('profile_missing'))
    return dict(owner_id=user.id,tf_number=str(employment.tf_number) if employment else user.username,first_name=profile.first_name,last_name=profile.last_name)

def token(target):return digest(packed(target))

def summary(db,owner_id,data,lock=False):
    query=select(RouteKnowledgeEntry).where(RouteKnowledgeEntry.owner_id==owner_id)
    if lock:query=query.with_for_update()
    existing={row.section_key:row.content_sha256 for row in db.scalars(query)}
    result={k:data[k] for k in ['file_sha256','source_rows','duplicates','unknown_dates','statuses']}
    result.update(added=0,existing=0,conflicts=0,map_matches=match_counts(data['records']))
    for row in data['records']:
        old=existing.get(row['section_key'])
        result['added' if old is None else 'existing' if old==row['content_sha256'] else 'conflicts']+=1
    return result,existing

def apply_import(db,user,data,filename,expected_token):
    current=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if current is None or not current.active or current.role!='tf':raise HTTPException(403,text('identity_error'))
    target=identity(db,current,lock=True)
    if token(target)!=expected_token:raise HTTPException(409,text('identity_error'))
    result,existing=summary(db,user.id,data,lock=True)
    for row in data['records']:
        if row['section_key'] not in existing:db.add(RouteKnowledgeEntry(owner_id=user.id,source_sha256=data['file_sha256'],**row))
    batch=db.scalar(select(RouteKnowledgeImport).where(RouteKnowledgeImport.owner_id==user.id,RouteKnowledgeImport.file_sha256==data['file_sha256']).with_for_update())
    if batch is None:db.add(RouteKnowledgeImport(owner_id=user.id,file_sha256=data['file_sha256'],filename=filename,summary_json=packed(result)))
    db.commit()
    return dict(identity=target,summary=result)


def create_router(require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/tf/route-csv.js')
    def script():
        from fastapi.responses import FileResponse
        return FileResponse(Path(__file__).parent/'static'/'route-csv.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/route-knowledge/operating-points')
    def references(route:str, user:User=Depends(driver),db:Session=Depends(database_session)):
        if not re.fullmatch(r'[0-9]{1,6}',route):raise HTTPException(422,text('invalid_csv'))
        from .models import RailwayOperatingPoint
        rows=db.scalars(select(RailwayOperatingPoint).where(RailwayOperatingPoint.route_number==str(int(route))).order_by(RailwayOperatingPoint.code))
        return dict(owner_id=user.id,items=[json.loads(row.payload_json) for row in rows])
    @router.get('/api/v1/tf/route-knowledge/imports')
    def listing(user:User=Depends(driver),db:Session=Depends(database_session)):
        target=identity(db,user)
        rows=list(db.scalars(select(RouteKnowledgeEntry).where(RouteKnowledgeEntry.owner_id==user.id).order_by(RouteKnowledgeEntry.id)))
        return dict(identity=target,items=[dict(id=row.id,**json.loads(row.source_json),map_match=map_match(json.loads(row.source_json))) for row in rows])
    def read(file):
        raw=file.file.read(MAX_BYTES+1)
        try:return parse_csv(raw)
        except ValueError as exc:raise HTTPException(413 if len(raw)>MAX_BYTES else 422,str(exc)) from None
    @router.post('/api/v1/tf/route-knowledge/imports/preview')
    def preview(file:UploadFile=File(...),user:User=Depends(driver),db:Session=Depends(database_session)):
        data=read(file);target=identity(db,user);result,_=summary(db,user.id,data)
        return dict(identity=target,owner_token=token(target),summary=result,items=[dict(**json.loads(row['source_json']),map_match=map_match(json.loads(row['source_json']))) for row in data['records']])
    @router.post('/api/v1/tf/route-knowledge/imports')
    def apply(file:UploadFile=File(...),owner_token:str=Form(...),expected_sha256:str=Form(...),confirmed:bool=Form(False),user:User=Depends(driver),db:Session=Depends(database_session)):
        if not confirmed:raise HTTPException(422,text('confirmation'))
        data=read(file)
        if data['file_sha256']!=expected_sha256:raise HTTPException(409,text('file_changed'))
        filename=Path((file.filename or 'Kenntnisse.csv').replace('\\','/')).name
        filename=''.join(c for c in filename if ord(c)>=32)[:180] or 'Kenntnisse.csv'
        return apply_import(db,user,data,filename,owner_token)
    return router
