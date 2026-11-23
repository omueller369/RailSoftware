# Gemeinsame Verarbeitung für GPS-Erfassung und Kartendarstellung.
"""Opt-in recording snapshots for read-only TF and administrative playback."""
import json
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import database_session
from .models import GpsDemoShare, GpsDemoPreference, TrainGpsRecording, User
from .tf_portal import driver_dependency
from .security import account_active
from .gps import read_payload, nearest_station
from .localization import source

STATIC=Path(__file__).parent/'static'
class ShareInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    shared:StrictBool
    expected_revision:int=Field(ge=1)
class ShareChange(ShareInput):
    journey_id:UUID
class ShareBatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    changes:list[ShareChange]=Field(min_length=1,max_length=1000)
class PreferenceInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    hidden:StrictBool
class Location(BaseModel):
    lat:float=Field(ge=-90,le=90,allow_inf_nan=False)
    lon:float=Field(ge=-180,le=180,allow_inf_nan=False)
class Locations(BaseModel):
    points:list[Location]=Field(max_length=100)

def metadata(row,payload):
    points=payload['points']
    return dict(id=row.recording_id,train_number=payload.get('train_number',''),start=points[0]['t'],end=points[-1]['t'])

def create_router(require_account,require_admin):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/tf/gps-demo-visibility.js')
    def visibility_script():return FileResponse(STATIC/'gps-demo-visibility.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/admin/gps-demo.js')
    def admin_script():return FileResponse(STATIC/'admin-gps-demo.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/admin/gps-demo')
    def page():return FileResponse(STATIC/'admin-gps-demo.html')
    @router.get('/api/v1/tf/gps-demo/preferences')
    def preference(user=Depends(driver),db:Session=Depends(database_session)):
        row=db.get(GpsDemoPreference,user.id);return dict(owner_id=user.id,hidden=bool(row and row.hidden))
    @router.put('/api/v1/tf/gps-demo/preferences')
    def save_preference(data:PreferenceInput,user=Depends(driver),db:Session=Depends(database_session)):
        db.scalar(select(User).where(User.id==user.id).with_for_update())
        row=db.get(GpsDemoPreference,user.id)
        if not row:row=GpsDemoPreference(user_id=user.id);db.add(row)
        row.hidden=data.hidden;db.commit();return dict(owner_id=user.id,hidden=row.hidden)
    def apply_share(db,row,user,data):
        if data.shared and row.revision!=data.expected_revision:raise HTTPException(409,source('portal_gps_demo.text_cb1011064bf5'))
        shared=db.get(GpsDemoShare,row.id)
        if data.shared and not shared:
            payload=read_payload(row)
            if not payload.get('ended',True) or len(payload.get('points',[]))<2:raise HTTPException(422)
            db.add(GpsDemoShare(recording_id=row.id,owner_id=user.id,payload_json=json.dumps(payload,ensure_ascii=False),source_revision=row.revision))
        elif not data.shared and shared:db.delete(shared)

    @router.post('/api/v1/tf/gps-demo/shares')
    def share_selection(data:ShareBatch,user=Depends(driver),db:Session=Depends(database_session)):
        db.scalar(select(User).where(User.id==user.id).with_for_update())
        keys=[str(change.journey_id) for change in data.changes]
        if len(set(keys))!=len(keys):raise HTTPException(422)
        rows={row.journey_id:row for row in db.scalars(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id,TrainGpsRecording.journey_id.in_(keys)).order_by(TrainGpsRecording.id).with_for_update())}
        if len(rows)!=len(keys):raise HTTPException(404)
        for change in data.changes:apply_share(db,rows[str(change.journey_id)],user,change)
        db.commit();return dict(items=[dict(journey_id=str(change.journey_id),shared=change.shared) for change in data.changes])

    @router.put('/api/v1/tf/gps-demo/recordings/{journey_id}/share')
    def share(journey_id:UUID,data:ShareInput,user=Depends(driver),db:Session=Depends(database_session)):
        db.scalar(select(User).where(User.id==user.id).with_for_update())
        row=db.scalar(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id,TrainGpsRecording.journey_id==str(journey_id)).with_for_update())
        if not row:raise HTTPException(404)
        apply_share(db,row,user,data)
        db.commit();return dict(shared=data.shared)
    def available(db,entry_id):
        row=db.get(GpsDemoShare,entry_id)
        owner=db.get(User,row.owner_id) if row else None
        if not owner or owner.role!='tf' or not account_active(db,owner):raise HTTPException(404)
        return row
    # Gemeinsame schreibgeschützte Dienste; die Verwaltungsrechte werden weiterhin je Modul geprüft.
    for prefix,dependency in [('/api/v1/tf/gps-demo',driver),('/api/v1/admin/gps-demo',require_admin)]:
        def listing(offset:int=Query(default=0,ge=0),user=Depends(dependency),db:Session=Depends(database_session)):
            rows=list(db.scalars(select(GpsDemoShare).order_by(GpsDemoShare.recording_id.desc()).offset(offset).limit(101)))
            items=[]
            for row in rows[:100]:
                try:available(db,row.recording_id)
                except HTTPException:continue
                item=metadata(row,json.loads(row.payload_json))
                if row.owner_id==user.id and user.role=='tf':
                    original=db.get(TrainGpsRecording,row.recording_id)
                    item.update(journey_id=original.journey_id,revision=original.revision,shared=True)
                items.append(item)
            return dict(items=items,next_offset=offset+100 if len(rows)>100 else None)
        def detail(entry_id:int,user=Depends(dependency),db:Session=Depends(database_session)):
            row=available(db,entry_id);return read_payload(row)
        def access(entry_id:int,user=Depends(dependency),db:Session=Depends(database_session)):
            available(db,entry_id);return dict(available=True)
        def stations(data:Locations,user=Depends(dependency),db:Session=Depends(database_session)):
            return dict(items=[nearest_station(db,p.lat,p.lon) for p in data.points])
        router.add_api_route(prefix+'/shared',listing,methods=['GET'])
        router.add_api_route(prefix+'/shared/{entry_id}',detail,methods=['GET'])
        router.add_api_route(prefix+'/shared/{entry_id}/access',access,methods=['GET'])
        router.add_api_route(prefix+'/stations',stations,methods=['POST'])
    return router
