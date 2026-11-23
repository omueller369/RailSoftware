# Gemeinsame Verarbeitung für Betriebsstellen und Ortszuordnungen.
"""Confirmed TF GPS coordinates: parent-row locking, compare-and-set and idempotent audit."""
import hashlib
import json
from datetime import timezone
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query,Response
from fastapi.responses import JSONResponse
from .i18n import translate
from pydantic import BaseModel,Field,model_validator
from typing import Literal
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from .db import database_session
from .models import RailwayStation,RailwayStationCoordinates,StationCoordinateContribution,User,now_utc
from .gps_analysis import distance
from .tf_portal import driver_dependency
from .localization import source

KEYS={'offer': 'station_contributions.text_7a5424e22744', 'far': 'station_contributions.text_d32c0afc6290', 'yes': 'station_contributions.text_baffedd06c2e', 'no': 'station_contributions.text_500ec634e9d7', 'queued': 'station_contributions.text_32bd8fa8f72a', 'saved': 'station_contributions.text_95b68f502613', 'discarded': 'station_contributions.text_3b8229600b1f', 'no_fix': 'station_contributions.text_a03343f6b968', 'failed': 'station_contributions.text_3ac85241b51a', 'retry': 'station_contributions.text_118cfc015f2f', 'owner': 'station_contributions.text_209262112731', 'unknown': 'station_contributions.text_e5d2a953eccc', 'invalid': 'station_contributions.text_508fd1c00940', 'conflict': 'station_contributions.text_8d88d1bfad6b', 'idempotency': 'station_contributions.text_d4430353d852', 'help': 'station_contributions.text_5c892618829a', 'history': 'station_contributions.text_114c9b1151de'}

def message(name):return source(KEYS[name])
def conflict_response(code,current=None):
    detail=dict(code=code,message=translate(message('idempotency' if code=='request_reused' else 'conflict')))
    if current is not None:detail['current']=current
    return JSONResponse(dict(detail=detail),status_code=409)

def coordinate_revision(db):return db.scalar(select(func.max(StationCoordinateContribution.id))) or 0

def current(station,point):
    value=None if point is None else dict(latitude=point.latitude,longitude=point.longitude,source_name=point.source_name,source_url=point.source_url,source_date=point.source_date,catalog_name=point.catalog_name)
    token=hashlib.sha256(json.dumps(dict(code=station.code,name=station.name,coordinate=value),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return dict(code=station.code,name=station.name,coordinate=value,token=token)

def plan(station,point,lat,lon):
    result=current(station,point)
    meters=distance(dict(lat=lat,lon=lon),dict(lat=point.latitude,lon=point.longitude)) if point else None
    return dict(**result,distance_m=meters,confirmation_required=meters is not None and meters>1000+1e-6)

class CoordinateWrite(BaseModel):
    request_id:UUID
    owner_id:int=Field(ge=1)
    latitude:float=Field(ge=-90,le=90,allow_inf_nan=False)
    longitude:float=Field(ge=-180,le=180,allow_inf_nan=False)
    accuracy_m:float=Field(ge=0,le=50,allow_inf_nan=False)
    observed_at:int=Field(ge=946684800000,le=4133980800000)
    expected_token:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirmed:Literal[True]
    confirm_overwrite:bool=False
    @model_validator(mode='after')
    def actual_position(self):
        if (self.latitude,self.longitude)==(0,0):raise ValueError(message('invalid'))
        return self
    def proposal(self):return dict(latitude=self.latitude,longitude=self.longitude,accuracy_m=self.accuracy_m,observed_at=self.observed_at)

def create_router(require_account):
    def private(response:Response):response.headers['Cache-Control']='private, no-store'
    router=APIRouter(dependencies=[Depends(private)])
    driver=driver_dependency(require_account)
    def station_row(db,code,lock=False):
        query=select(RailwayStation).where(RailwayStation.code==code)
        if lock:query=query.with_for_update()
        station=db.scalar(query)
        if not station:raise HTTPException(404,message('unknown'))
        return station
    @router.get('/api/v1/tf/stations/coordinate-revision')
    def revision(user:User=Depends(driver),db:Session=Depends(database_session)):
        return dict(revision=coordinate_revision(db))
    @router.get('/api/v1/tf/stations/{station_code}/coordinates')
    def check(station_code:str,owner_id:int=Query(ge=1),latitude:float=Query(ge=-90,le=90,allow_inf_nan=False),longitude:float=Query(ge=-180,le=180,allow_inf_nan=False),request_id:UUID|None=None,user:User=Depends(driver),db:Session=Depends(database_session)):
        if owner_id!=user.id:raise HTTPException(403,message('owner'))
        if (latitude,longitude)==(0,0):raise HTTPException(422,message('invalid'))
        station=station_row(db,station_code)
        result=plan(station,db.get(RailwayStationCoordinates,station.code),latitude,longitude)
        if request_id:
            previous=db.scalar(select(StationCoordinateContribution).where(StationCoordinateContribution.request_id==str(request_id)))
            if previous:
                saved=json.loads(previous.proposal_json)
                if previous.owner_id!=user.id or previous.code!=station.code or saved['latitude']!=latitude or saved['longitude']!=longitude:return conflict_response('request_reused')
                result['already_applied']=True
        return result
    @router.put('/api/v1/tf/stations/{station_code}/coordinates')
    def write(station_code:str,data:CoordinateWrite,user:User=Depends(driver),db:Session=Depends(database_session)):
        if data.owner_id!=user.id:raise HTTPException(403,message('owner'))
        if data.observed_at>int(now_utc().replace(tzinfo=timezone.utc).timestamp()*1000)+300000:raise HTTPException(422,message('invalid'))
        station=station_row(db,station_code,True)
        previous=db.scalar(select(StationCoordinateContribution).where(StationCoordinateContribution.request_id==str(data.request_id)))
        point=db.get(RailwayStationCoordinates,station.code)
        if previous:
            if previous.owner_id!=user.id or previous.code!=station.code or json.loads(previous.proposal_json)!=data.proposal():return conflict_response('request_reused')
            return dict(**current(station,point),revision=coordinate_revision(db),already_applied=True)
        result=plan(station,point,data.latitude,data.longitude)
        if data.expected_token!=result['token']:return conflict_response('coordinate_changed',result)
        if result['confirmation_required'] and not data.confirm_overwrite:return conflict_response('confirmation_required',result)
        before=json.dumps(result['coordinate'],ensure_ascii=False) if point else None
        if point is None:point=RailwayStationCoordinates(code=station.code);db.add(point)
        point.catalog_name=station.name;point.latitude=data.latitude;point.longitude=data.longitude
        point.source_name='TF-GPS';point.source_url='/tf/arbeitsbericht';point.source_date=now_utc().strftime('%Y-%m');point.max_spread_m=0
        applied=current(station,point)
        db.add(StationCoordinateContribution(request_id=str(data.request_id),owner_id=user.id,code=station.code,proposal_json=json.dumps(data.proposal(),sort_keys=True),before_json=before,after_json=json.dumps(applied['coordinate'],ensure_ascii=False)))
        db.commit()
        return dict(**applied,revision=coordinate_revision(db),already_applied=False)
    return router
