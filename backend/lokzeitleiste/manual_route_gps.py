"""Owned GPS-to-manual links and explicitly confirmed raw-point reduction."""
import json,math
from datetime import datetime,timezone
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field,StrictBool,ConfigDict
from sqlalchemy import select,delete
from .db import database_session
from .models import ManualRouteKnowledge,TrainGpsRecording,GpsDemoShare,User
from .tf_portal import driver_dependency
from .route_knowledge_import import digest,packed,identity
from .localization import source
import hashlib

def msg(name):return source('manual_route_ops.text_'+hashlib.sha256(('manual_route_ops.'+name).encode()).hexdigest()[:12])
class GpsLink(BaseModel):
    model_config=ConfigDict(extra='forbid')
    journey_id:UUID
    expected_revision:int=Field(ge=1)
    expected_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
class CompactInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirmed:StrictBool

def gps_metadata(row,payload=None):
    payload=payload if payload is not None else json.loads(row.payload_json);points=payload.get('points',[])
    return dict(journey_id=row.journey_id,revision=row.revision,sha256=digest(row.payload_json),point_count=len(points),train_number=payload.get('train_number',''),start=points[0]['t'] if points else None,end=points[-1]['t'] if points else None,ended=bool(payload.get('ended')),from_code=payload.get('start_station'),to_code=payload.get('end_station'))

def link_payload(db,user,data,payload,previous=None):
    if data is None:
        if previous:
            for key in ['source_gps','source_gps_history']:
                if key in previous:payload[key]=previous[key]
        return
    row=db.scalar(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id,TrainGpsRecording.journey_id==str(data.journey_id)).with_for_update())
    if row is None:raise HTTPException(404,msg('gps_missing'))
    raw=json.loads(row.payload_json)
    if row.revision!=data.expected_revision or digest(row.payload_json)!=data.expected_sha256:raise HTTPException(409,msg('gps_changed'))
    if not raw.get('ended') or len(raw.get('points',[]))<2:raise HTTPException(409,msg('gps_not_finished'))
    meta=gps_metadata(row,raw);meta.update(points_removed=False,path_sha256=digest(packed([payload['waypoints'],payload['routes']])))
    payload['source_gps']=meta
    if previous:
        history=previous.get('source_gps_history',[])
        old=previous.get('source_gps')
        if old and (old.get('journey_id')!=meta['journey_id'] or old.get('points_removed')):history=[*history,old]
        if history:payload['source_gps_history']=history

def owned_manual(db,user,route_id,revision,lock=True):
    row=db.scalar(select(ManualRouteKnowledge).where(ManualRouteKnowledge.owner_id==user.id,ManualRouteKnowledge.id==route_id).with_for_update())
    if row is None:raise HTTPException(404,msg('missing'))
    if digest(row.payload_json)!=revision:raise HTTPException(409,msg('changed'))
    return row

def checked_source(db,user,item):
    from .manual_route_parallel import trace,project,nearby
    from .route_knowledge_mapping import match
    payload=json.loads(item.payload_json);meta=payload.get('source_gps')
    if not meta or meta.get('points_removed'):raise HTTPException(409,msg('gps_missing'))
    if meta.get('path_sha256')!=digest(packed([payload['waypoints'],payload['routes']])):raise HTTPException(409,msg('path_changed'))
    row=db.scalar(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id,TrainGpsRecording.journey_id==meta['journey_id']).with_for_update())
    if row is None or row.revision!=meta['revision'] or digest(row.payload_json)!=meta['sha256']:raise HTTPException(409,msg('gps_changed'))
    raw=json.loads(row.payload_json);points=raw.get('points',[])
    if not raw.get('ended') or len(points)<2:raise HTTPException(409,msg('gps_not_finished'))
    reliable=[p for p in points if p.get('accuracy',100001)<=50 and math.isfinite(p.get('lat',math.inf)) and abs(p['lat'])<85 and math.isfinite(p.get('lon',math.inf))]
    if len(reliable)<2:raise HTTPException(409,msg('coverage_incomplete'))
    target=[];seen=set()
    for leg in payload['legs']:
        mapped=match(leg)
        if mapped['status']!='mapped':raise HTTPException(409,msg('coverage_incomplete'))
        a,b=sorted([mapped['from_m'],mapped['to_m']]);key=(mapped['route'],a,b)
        if key not in seen:seen.add(key);target.extend(trace(*key))
    locations=[]
    for point in reliable:
        p=project(point['lon'],point['lat']);locations.append([p,p])
    scale=40075016.686*math.cos(math.radians(reliable[0]['lat']))
    if not nearby(locations,target,scale):raise HTTPException(409,msg('coverage_incomplete'))
    return row,raw,payload

def create_router(require_account):
    from .manual_route_knowledge import entries,saved_routes
    router=APIRouter();driver=driver_dependency(require_account)
    def response(db,user):return dict(owner_id=user.id,items=entries(db,user.id),saved_routes=saved_routes(db,user.id))
    @router.get('/api/v1/tf/route-knowledge/manual/gps-source/{journey_id}')
    def source_view(journey_id:UUID,user:User=Depends(driver),db=Depends(database_session)):
        from .route_knowledge import route_segments
        row=db.scalar(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id,TrainGpsRecording.journey_id==str(journey_id)))
        if row is None:raise HTTPException(404,msg('gps_missing'))
        raw=json.loads(row.payload_json)
        return dict(owner_id=user.id,item={**gps_metadata(row,raw),'timed_segments':route_segments(raw.get('points',[]),timed=True)})
    @router.delete('/api/v1/tf/route-knowledge/manual/{route_id}')
    def remove(route_id:int,expected_sha256:str=Query(pattern=r'^[0-9a-f]{64}$'),user:User=Depends(driver),db=Depends(database_session)):
        identity(db,user,lock=True);row=owned_manual(db,user,route_id,expected_sha256);db.delete(row);db.commit();return response(db,user)
    @router.get('/api/v1/tf/route-knowledge/manual/{route_id}/gps-compaction')
    def check(route_id:int,expected_sha256:str=Query(pattern=r'^[0-9a-f]{64}$'),user:User=Depends(driver),db=Depends(database_session)):
        identity(db,user,lock=True);item=owned_manual(db,user,route_id,expected_sha256);row,raw,payload=checked_source(db,user,item)
        return dict(owner_id=user.id,manual_revision=digest(item.payload_json),source_gps=gps_metadata(row,raw),eligible=True)
    @router.post('/api/v1/tf/route-knowledge/manual/{route_id}/gps-compaction')
    def compact(route_id:int,data:CompactInput,user:User=Depends(driver),db=Depends(database_session)):
        if not data.confirmed:raise HTTPException(422,msg('confirmation_required'))
        identity(db,user,lock=True);item=owned_manual(db,user,route_id,data.expected_sha256);row,raw,payload=checked_source(db,user,item)
        stamp=datetime.now(timezone.utc).isoformat();raw.update(points=[],compacted_manual_id=item.id,raw_points_removed_at=stamp)
        row.payload_json=packed(raw);row.revision+=1
        payload['source_gps'].update(points_removed=True,removed_at=stamp);item.payload_json=packed(payload)
        db.execute(delete(GpsDemoShare).where(GpsDemoShare.recording_id==row.id,GpsDemoShare.owner_id==user.id))
        db.commit();return response(db,user)
    return router
