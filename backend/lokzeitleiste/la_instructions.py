"""Authenticated publication and delivery of regional La PDFs."""
import hashlib,io,json
from datetime import date
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter,Depends,HTTPException,File,Form,UploadFile
from fastapi.responses import FileResponse,Response
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session,defer
from .accounts.access import permissions
from .db import database_session
from .models import LaInstruction
from .documents.storage import MAX_FILE,clean_name
from .tf_portal import driver_dependency
from .localization import source
STATIC=Path(__file__).parent/'static'
REGIONS=('nord','ost','suedost','west','mitte','suedwest','sued')
def text(name):
    return source('la_instructions.text_'+hashlib.sha256(name.encode()).hexdigest()[:12])

def create_router(require_account,require_admin):
    router=APIRouter();driver=driver_dependency(require_account)
    vendor=STATIC/'la-vendor';manifest=json.loads((vendor/'manifest.json').read_text())
    @router.get('/tf/la-vendor/{name:path}')
    def vendor_file(name:str):
        if name not in manifest['files']:raise HTTPException(404)
        mime='text/javascript' if name.endswith('.mjs') else 'application/wasm' if name.endswith('.wasm') else 'application/octet-stream'
        return FileResponse(vendor/name,media_type=mime,headers={'Cache-Control':'no-cache'})
    @router.get('/tf/la-instructions.css')
    def css():return FileResponse(STATIC/'la-instructions.css',media_type='text/css',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/la-instructions.js')
    def script():return FileResponse(STATIC/'la-instructions.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/admin/la-admin.js')
    def admin_script():return FileResponse(STATIC/'la-admin.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/admin/la-instructions')
    def page():return FileResponse(STATIC/'la-admin.html',headers={'Cache-Control':'no-cache'})
    def listing(db,user,write=False):
        rows=db.scalars(select(LaInstruction).options(defer(LaInstruction.content)).order_by(LaInstruction.valid_from.desc(),LaInstruction.id.desc()))
        return dict(owner_id=user.id,can_write=write,items=[{key:(getattr(row,key).isoformat() if key in ('valid_from','valid_until','created_at') else getattr(row,key)) for key in ('id','region','title','edition','valid_from','valid_until','filename','content_sha256','created_at')} for row in rows])
    @router.get('/api/v1/tf/la-instructions')
    def tf_list(user=Depends(driver),db:Session=Depends(database_session)):return listing(db,user)
    @router.get('/api/v1/admin/la-instructions')
    def admin_list(user=Depends(require_admin),db:Session=Depends(database_session)):return listing(db,user,permissions(db,user)['la']>=2)
    def pdf(db,entry_id):
        row=db.get(LaInstruction,entry_id)
        if not row:raise HTTPException(404)
        return Response(row.content,media_type='application/pdf',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Disposition':"inline; filename=\"La.pdf\"; filename*=UTF-8''"+quote(row.filename,safe=''),'X-Content-SHA256':row.content_sha256})
    @router.get('/api/v1/tf/la-instructions/{entry_id}/pdf')
    def tf_pdf(entry_id:int,user=Depends(driver),db:Session=Depends(database_session)):return pdf(db,entry_id)
    @router.get('/api/v1/admin/la-instructions/{entry_id}/pdf')
    def admin_pdf(entry_id:int,user=Depends(require_admin),db:Session=Depends(database_session)):return pdf(db,entry_id)
    @router.post('/api/v1/admin/la-instructions',status_code=201)
    async def publish(region:str=Form(max_length=12),title:str=Form(min_length=1,max_length=200),edition:str=Form(min_length=1,max_length=80),valid_from:date=Form(),valid_until:date=Form(),file:UploadFile=File(),user=Depends(require_admin),db:Session=Depends(database_session)):
        try:content=await file.read(MAX_FILE+1)
        finally:await file.close()
        filename=clean_name(file.filename or '')
        if len(content)>MAX_FILE:raise HTTPException(413,text('invalid'))
        if region not in REGIONS or not title.strip() or not edition.strip() or valid_from>valid_until or not filename.lower().endswith('.pdf') or not content.startswith(b'%PDF-'):raise HTTPException(422,text('invalid'))
        try:
            reader=PdfReader(io.BytesIO(content))
            if reader.is_encrypted or not 1<=len(reader.pages)<=2000:raise ValueError()
        except Exception:raise HTTPException(422,text('invalid')) from None
        row=LaInstruction(region=region,title=title.strip(),edition=edition.strip(),valid_from=valid_from,valid_until=valid_until,filename=filename,content_sha256=hashlib.sha256(content).hexdigest(),content=content,created_by=user.id)
        db.add(row)
        try:db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,text('duplicate')) from None
        return dict(id=row.id)
    @router.delete('/api/v1/admin/la-instructions/{entry_id}')
    def remove(entry_id:int,user=Depends(require_admin),db:Session=Depends(database_session)):
        row=db.get(LaInstruction,entry_id)
        if not row:raise HTTPException(404)
        db.delete(row);db.commit();return dict(ok=True)
    return router
