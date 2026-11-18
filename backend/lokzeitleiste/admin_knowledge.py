"""Staff-scoped knowledge views using the same services as the TF portal."""
import json,hashlib,unicodedata
from datetime import date
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException,Request,Response,Query
from fastapi.responses import HTMLResponse,FileResponse
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from .db import database_session
from .models import User,TfProfile,TfEmployment,EmployeeCategory,TfRollingStockKnowledge
from .accounts.access import permissions
from .localization import source
from .route_knowledge_import import identity,digest,packed
from .tf_knowledge import SCHEMAS
STATIC=Path(__file__).parent/'static'

# Shared translation keys; no personal source files are bundled.
KEYS={'title': 'admin_knowledge.text_64d055aab207', 'intro': 'admin_knowledge.text_d8540198fe92', 'find': 'admin_knowledge.text_97ad4bce6620', 'choose': 'admin_knowledge.text_11584457e67f', 'empty': 'admin_knowledge.text_a00deeebd72a', 'loading': 'admin_knowledge.text_58570aaa3dd7', 'forbidden': 'admin_knowledge.text_0946d5917273', 'readonly': 'admin_knowledge.text_6b9a4ba09b16', 'failure': 'admin_knowledge.text_4393bd057e8a', 'new_series': 'admin_knowledge.text_96453327a4fc', 'save_series': 'admin_knowledge.text_455faa1eea5c', 'bad_series': 'admin_knowledge.text_7d8b71e08aef', 'duplicate_series': 'admin_knowledge.text_9db33041272a', 'help': 'admin_knowledge.text_284bc2a831a1', 'history': 'admin_knowledge.text_06452a53499d'}
def text(key):return source(KEYS[key])
class SeriesInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    series:str=Field(min_length=1,max_length=80)
    valid_until:str=Field(min_length=10,max_length=10)
    expected_revision:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')

def series_values(data):
    if not data.series.strip() or any(ord(c)<32 for c in data.series):raise HTTPException(422,text('bad_series'))
    try:
        if date.fromisoformat(data.valid_until).isoformat()!=data.valid_until:raise ValueError()
    except ValueError:raise HTTPException(422,text('bad_series')) from None
    values=dict(series=data.series,valid_until=data.valid_until)
    return values,digest(unicodedata.normalize('NFC',data.series.strip()).upper()),digest(packed(values))

def create_router(require_admin):
    def private(response:Response):response.headers['Cache-Control']='private, no-store'
    router=APIRouter(dependencies=[Depends(private)])
    @router.get('/admin/knowledge')
    def page():
        template=(STATIC/'admin-knowledge.html').read_text()
        tf=(STATIC/'tf-portal.html').read_text();section='<section id="routeKnowledge"'+tf.split('<section id="routeKnowledge"',1)[1].split('<section id="updatesModule"',1)[0]
        section=section.replace('id="routeKnowledge" hidden','id="routeKnowledge"').replace('<h1>{{knowledge_tabs.text_ffad8a8eb545}}</h1>','').replace('<p>{{knowledge_tabs.text_1308485034f1}}</p>','').replace('<p>{{portal_beta60.text_a6fd4b95ede8}}</p>','')
        return HTMLResponse(template.replace('<!-- KNOWLEDGE -->',section))
    @router.get('/admin/knowledge.js')
    def script():return FileResponse(STATIC/'admin-knowledge.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/admin/knowledge/drivers')
    def drivers(actor=Depends(require_admin),db:Session=Depends(database_session)):
        rows=db.execute(select(User,TfProfile,TfEmployment).join(TfProfile,TfProfile.user_id==User.id).outerjoin(TfEmployment,TfEmployment.user_id==User.id).outerjoin(EmployeeCategory,EmployeeCategory.user_id==User.id).where(User.role=='tf',func.coalesce(EmployeeCategory.category,'tf')=='tf').order_by(TfProfile.last_name,TfProfile.first_name,User.id))
        return dict(items=[dict(id=user.id,first_name=profile.first_name,last_name=profile.last_name,tf_number=str(employment.tf_number) if employment else user.username,personnel_number=profile.personnel_number,active=user.active) for user,profile,employment in rows],can_write=permissions(db,actor)['knowledge']>=2)
    @router.get('/api/v1/admin/knowledge/stations')
    def stations(q:str=Query(default='',max_length=255),actor=Depends(require_admin),db:Session=Depends(database_session)):
        from .models import RailwayStation
        query=q.strip()
        if not query:return []
        escaped=query.replace('!','!!').replace('%','!%').replace('_','!_')
        rows=db.scalars(select(RailwayStation).where((RailwayStation.code.ilike(escaped+'%',escape='!'))|(RailwayStation.name.ilike('%'+escaped+'%',escape='!'))).order_by(RailwayStation.code).limit(30))
        return [dict(code=r.code,name=r.name) for r in rows]
    def target(tf_id:int,actor=Depends(require_admin),db:Session=Depends(database_session)):
        user=db.get(User,tf_id);category=db.get(EmployeeCategory,tf_id)
        if not user or user.role!='tf' or (category and category.category!='tf') or not db.get(TfProfile,tf_id):raise HTTPException(404)
        return user
    # Only remapped administrative API routes are included; public assets keep their original routes.
    from .route_knowledge import create_router as shared_router
    shared=shared_router(require_admin,target_dependency=target,api_prefix='/api/v1/admin/knowledge/{tf_id}')
    router.include_router(shared)
    @router.post('/api/v1/admin/knowledge/{tf_id}/series')
    def add_series(data:SeriesInput,user=Depends(target),db:Session=Depends(database_session)):
        db.scalar(select(User).where(User.id==user.id).with_for_update())
        values,key,content=series_values(data)
        if db.scalar(select(TfRollingStockKnowledge).where(TfRollingStockKnowledge.owner_id==user.id,TfRollingStockKnowledge.identity_key==key).with_for_update()):raise HTTPException(409,text('duplicate_series'))
        row=TfRollingStockKnowledge(owner_id=user.id,identity_key=key,content_sha256=content,**values);db.add(row);db.commit();return dict(identity=identity(db,user),id=row.id)
    @router.patch('/api/v1/admin/knowledge/{tf_id}/series/{entry_id}')
    def edit_series(entry_id:int,data:SeriesInput,user=Depends(target),db:Session=Depends(database_session)):
        db.scalar(select(User).where(User.id==user.id).with_for_update())
        row=db.scalar(select(TfRollingStockKnowledge).where(TfRollingStockKnowledge.owner_id==user.id,TfRollingStockKnowledge.id==entry_id).with_for_update())
        if not row:raise HTTPException(404)
        if data.expected_revision!=row.content_sha256:raise HTTPException(409,text('failure'))
        values,key,content=series_values(data)
        other=db.scalar(select(TfRollingStockKnowledge).where(TfRollingStockKnowledge.owner_id==user.id,TfRollingStockKnowledge.identity_key==key,TfRollingStockKnowledge.id!=row.id).with_for_update())
        if other:raise HTTPException(409,text('duplicate_series'))
        row.series=values['series'];row.valid_until=values['valid_until'];row.identity_key=key;row.content_sha256=content;db.commit();return dict(identity=identity(db,user),id=row.id)
    return router
