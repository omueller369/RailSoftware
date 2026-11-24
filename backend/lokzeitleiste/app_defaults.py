# Gemeinsame Verarbeitung für Grundwerte und Vorgaben.
"""Versioned app vocabulary with explicit DB-InfraGo legacy compatibility."""
from .field_errors import FieldError
from .localization import source as _text_source
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Query
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,field_validator
from sqlalchemy import select,delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import database_session
from .models import AppDefaultValue as Value,AppDefaultSeed,DutyReport,TrainGpsRecording,AppCauseReason,AppCauseReasonSeed
from .tf_portal import driver_dependency
from .default_order import ordered


def historical_values(db):
    result=set()
    for raw in db.scalars(select(DutyReport.payload_json)):
        for train in json.loads(raw).get('train_journeys',[]):
            for event in train.get('events',[]):
                for category,field in [('reason','reason'),('cause','cause')]:
                    if event.get(field):result.add((category,event[field]))
    for raw in db.scalars(select(TrainGpsRecording.payload_json)):
        for reason in json.loads(raw).get('reasons',{}).values():
            if reason.get('reason'):result.add(('reason',reason['reason']))
    if ('cause',_text_source('server_app_defaults.text_2087c99eb939')) in result:result.add(('cause','CTL'))
    return result


def ensure_defaults(db):
    _ensure_defaults(db)
    from .infra_go import migrate
    migrate(db)
    ensure_relations(db)

def _ensure_defaults(db):
    if db.get(AppDefaultSeed,1):
        if not db.get(AppDefaultSeed,2):
            value='DB-Digi-Befehl'
            if not db.scalar(select(Value).where(Value.category=='reason',Value.value==value)):
                db.add(Value(category='reason',value=value,label=value,label_key=value.casefold(),active=True,ever_used=False,revision=1))
            db.add(AppDefaultSeed(id=2))
            try:db.commit()
            except IntegrityError:
                db.rollback()
                if not db.get(AppDefaultSeed,2):raise
        return
    from .work_reports.schemas import REASONS
    used=historical_values(db)
    defaults=[('reason',value,True) for value in REASONS]+[('cause',value,True) for value in ('CTL',_text_source('server_app_defaults.text_1abed57a73e2'),_text_source('server_app_defaults.text_7fe3366aac3e'),_text_source('server_app_defaults.text_69384a6be550'))]
    known={(kind,value) for kind,value,_ in defaults}
    defaults += [(kind,value,False) for kind,value in sorted(used-known)]
    db.add_all([AppDefaultSeed(id=1),AppDefaultSeed(id=2)])
    for kind,value,active in defaults:
        db.add(Value(category=kind,value=value,label=value,label_key=value.casefold(),active=active,ever_used=(kind,value) in used,revision=1))
    try:db.commit()
    except IntegrityError:
        db.rollback()
        if not db.get(AppDefaultSeed,1):raise


def ensure_relations(db):
    if db.get(AppCauseReasonSeed,1):return
    # Der bisher freie Bestand startet mit allen Kombinationen; keine Auswahl wird gelöscht.
    rows=list(db.scalars(select(Value)));db.add(AppCauseReasonSeed(id=1))
    db.add_all([AppCauseReason(cause_id=c.id,reason_id=r.id) for c in rows if c.category=='cause' for r in rows if r.category=='reason'])
    try:db.commit()
    except IntegrityError:
        db.rollback()
        if not db.get(AppCauseReasonSeed,1):raise

def use_pair(db,cause,reason,previous=None,loc=None,context=None):
    from .infra_go import canonical,alias_map
    aliases=alias_map(db);cause=canonical(cause,aliases)
    if cause==_text_source('server_app_defaults.text_2087c99eb939'):cause='CTL'
    prior_cause=canonical((previous or {}).get('cause') or '',aliases)
    if prior_cause==_text_source('server_app_defaults.text_2087c99eb939'):prior_cause='CTL'
    if previous and prior_cause==cause and previous.get('reason')==reason:return
    c=db.scalar(select(Value).where(Value.category=='cause',Value.value==cause));r=db.scalar(select(Value).where(Value.category=='reason',Value.value==reason))
    if not c or not r or not db.get(AppCauseReason,(c.id,r.id)):
        text=_text_source('coordination.text_023ab76c7da5')
        if loc is not None:raise FieldError(text,loc,context)
        raise HTTPException(422,text)


def use_value(db,category,value,previous=None,loc=None,context=None,aliases=None):
    # Historisches CTL DE dem aktuellen Schlüssel zuordnen, ohne gespeicherte Berichtsfassungen umzuschreiben.
    from .infra_go import canonical as infra_canonical,alias_map
    if category=='cause':
        lookup=alias_map(db) if aliases is None else aliases
        value=infra_canonical(value,lookup)
        if previous:previous=infra_canonical(previous,lookup)
    canonical='CTL' if category=='cause' and value==_text_source('server_app_defaults.text_2087c99eb939') else value
    row=db.scalar(select(Value).where(Value.category==category,Value.value==canonical).with_for_update())
    if not row or (not row.active and value!=previous):
        message=_text_source('server_app_defaults.text_abc1be1d3849')
        if loc is not None:raise FieldError(message,loc,context)
        raise HTTPException(422,message)
    row.ever_used=True
    return row


def use_journeys(db,journeys,previous=()):
    ensure_defaults(db)
    from .infra_go import normalize_model,alias_map
    from types import SimpleNamespace
    aliases=alias_map(db)
    normalize_model(db,SimpleNamespace(train_journeys=journeys),aliases)
    old={(str(train['id']),str(event['id'])):event for train in previous for event in train.get('events',[])}
    # A consistent order also serializes use/deletion of shared values.
    selections=[]
    for ti,train in enumerate(journeys):
        for ei,event in enumerate(train.events):
            prior=old.get((str(train.id),str(event.id)),{})
            selections += [(category,getattr(event,category),prior.get(category),['train_journeys',ti,'events',ei,category],dict(journey_id=str(train.id),event_id=str(event.id))) for category in ('cause','reason')]
    labels={}
    for category,value,previous_value,loc,context in sorted(selections,key=lambda item:(item[0],item[1])):labels[category,value]=use_value(db,category,value,previous_value,loc,context,aliases).label
    for ti,train in enumerate(journeys):
        for ei,event in enumerate(train.events):
            use_pair(db,event.cause,event.reason,old.get((str(train.id),str(event.id))),['train_journeys',ti,'events',ei,'reason'],dict(journey_id=str(train.id),event_id=str(event.id)))
            prior=old.get((str(train.id),str(event.id)),{})
            for category in ('reason','cause'):
                label=prior.get(category+'_label') if prior.get(category)==getattr(event,category) else None
                setattr(event,category+'_label',label or labels[category,getattr(event,category)])

class ValueInput(BaseModel):
    label:str=Field(min_length=1,max_length=200)
    active:bool=True
    @field_validator('label')
    @classmethod
    def trim(cls,value):
        value=value.strip()
        if not value:raise ValueError(_text_source('server_app_defaults.text_25b9ad8f3ac8'))
        return value
class ValueUpdate(ValueInput):
    expected_revision:int=Field(ge=1)


def view(row):
    from sqlalchemy.orm import object_session
    db=object_session(row);extra={}
    if db and row.category=='cause':extra['reason_values']=list(db.scalars(select(Value.value).join(AppCauseReason,AppCauseReason.reason_id==Value.id).where(AppCauseReason.cause_id==row.id)))
    return dict(**extra,id=row.id,category=row.category,value=row.value,label=row.label,active=row.active,used=row.ever_used,revision=row.revision)

class RelationsInput(BaseModel):
    expected_revision:int=Field(ge=1)
    reason_ids:list[int]=Field(default_factory=list,max_length=2000)


def create_router(require_admin,require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/admin/app-defaults')
    def page():return FileResponse(Path(__file__).parent/'static'/'app-defaults.html')
    @router.get('/admin/app-defaults.js')
    def script():return FileResponse(Path(__file__).parent/'static'/'app-defaults.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/app-defaults')
    def choices(user=Depends(driver),db:Session=Depends(database_session)):
        ensure_defaults(db)
        from .infra_go import alias_map,CANONICAL
        aliases=list(alias_map(db))
        return [dict(view(row),**({'aliases':aliases} if row.category=='cause' and row.value==CANONICAL else {})) for category in ('reason','cause') for row in ordered(db,category,db.scalars(select(Value).where(Value.category==category).order_by(Value.id)))]
    @router.get('/api/v1/admin/app-defaults',dependencies=[Depends(require_admin)])
    def listing(db:Session=Depends(database_session)):
        ensure_defaults(db)
        from .infra_go import alias_map,CANONICAL
        aliases=list(alias_map(db))
        return [dict(view(row),**({'aliases':aliases} if row.category=='cause' and row.value==CANONICAL else {})) for category in ('reason','cause') for row in ordered(db,category,db.scalars(select(Value).where(Value.category==category).order_by(Value.id)))]
    @router.put('/api/v1/admin/app-defaults/cause/{cause_id}/reasons',dependencies=[Depends(require_admin)])
    def relations(cause_id:int,data:RelationsInput,db:Session=Depends(database_session)):
        ensure_defaults(db);cause=db.scalar(select(Value).where(Value.id==cause_id,Value.category=='cause').with_for_update())
        if not cause:raise HTTPException(404,_text_source('coordination.text_90823a0948b5'))
        if cause.revision!=data.expected_revision:raise HTTPException(409,_text_source('coordination.text_fbf634cb29dd'))
        wanted=set(data.reason_ids);found=set(db.scalars(select(Value.id).where(Value.category=='reason',Value.id.in_(wanted)))) if wanted else set()
        if wanted!=found:raise HTTPException(422,_text_source('coordination.text_90823a0948b5'))
        db.execute(delete(AppCauseReason).where(AppCauseReason.cause_id==cause.id))
        db.add_all([AppCauseReason(cause_id=cause.id,reason_id=i) for i in sorted(wanted)]);cause.revision+=1;db.commit();return view(cause)
    def commit(db,row):
        try:db.commit()
        except IntegrityError as exc:
            db.rollback();raise HTTPException(409,_text_source('server_app_defaults.text_49d3623ea7be')) from exc
        return view(row)
    @router.post('/api/v1/admin/app-defaults/{category}',status_code=201,dependencies=[Depends(require_admin)])
    def create(category:Literal['reason','cause'],data:ValueInput,db:Session=Depends(database_session)):
        ensure_defaults(db)
        from .infra_go import named,CANONICAL
        if category=='cause' and named(data.label):data.label=CANONICAL
        row=Value(category=category,value='custom-'+uuid4().hex[:24],label=data.label,label_key=data.label.casefold(),active=data.active,ever_used=False,revision=1);db.add(row)
        return commit(db,row)
    @router.put('/api/v1/admin/app-defaults/value/{value_id}',dependencies=[Depends(require_admin)])
    def update(value_id:int,data:ValueUpdate,db:Session=Depends(database_session)):
        row=db.scalar(select(Value).where(Value.id==value_id).with_for_update())
        if not row:raise HTTPException(404,_text_source('server_app_defaults.text_5c5fa14fef76'))
        if row.revision!=data.expected_revision:raise HTTPException(409,_text_source('server_app_defaults.text_60fe685fe99d'))
        from .infra_go import named,CANONICAL
        if row.category=='cause' and (named(data.label) or row.value==CANONICAL):data.label=CANONICAL
        row.label=data.label;row.label_key=data.label.casefold();row.active=data.active;row.revision+=1
        return commit(db,row)
    @router.delete('/api/v1/admin/app-defaults/value/{value_id}',dependencies=[Depends(require_admin)])
    def remove(value_id:int,expected_revision:int=Query(ge=1),db:Session=Depends(database_session)):
        row=db.scalar(select(Value).where(Value.id==value_id).with_for_update())
        if not row:raise HTTPException(404,_text_source('server_app_defaults.text_5c5fa14fef76'))
        if row.revision!=expected_revision:raise HTTPException(409,_text_source('server_app_defaults.text_60fe685fe99d'))
        if row.ever_used or (row.category,row.value) in historical_values(db):
            raise HTTPException(409,_text_source('server_app_defaults.text_94ee479e3ac2'))
        db.delete(row);db.commit();return {'ok':True}
    return router
