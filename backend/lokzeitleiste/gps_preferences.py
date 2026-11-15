"""Per-driver preferences and explicitly enabled, expiring live sharing."""
import json
from pathlib import Path
from datetime import timedelta,timezone
from typing import Literal,Annotated
from uuid import UUID,uuid4
from fastapi import APIRouter,Depends,HTTPException,Response
from fastapi.responses import FileResponse
from pydantic import BaseModel,ConfigDict,Field,StrictBool
from sqlalchemy import select,delete
from sqlalchemy.orm import Session
from .models import User,TfProfile,GpsPreference,GpsLivePosition,now_utc
from .db import database_session
from .tf_portal import driver_dependency
from .security import account_active
from .localization import source

KEYS={'title': 'gps_preferences.text_9df5067d2313', 'minutes': 'gps_preferences.text_bd2bc93d3eca', 'marker': 'gps_preferences.text_0d8c06b0a07e', 'electric': 'gps_preferences.text_252ca9f40e03', 'steam': 'gps_preferences.text_dd0d7d9feec2', 'diesel': 'gps_preferences.text_0cd2e8782ab3', 'tank': 'gps_preferences.text_328544008aa8', 'circle': 'gps_preferences.text_6726b70cca00', 'display': 'gps_preferences.text_c5889fbd9a97', 'elapsed': 'gps_preferences.text_bde7e8d129a4', 'stopped': 'gps_preferences.text_1aca2cda9203', 'speed': 'gps_preferences.text_10e298f7965c', 'train': 'gps_preferences.text_21dbeca0df82', 'first_name': 'gps_preferences.text_98a5708ca0e1', 'consent': 'gps_preferences.text_12a26cfc69c8', 'yes': 'gps_preferences.text_cb909206c316', 'no': 'gps_preferences.text_6131c17c63a5', 'save': 'gps_preferences.text_2dada0a88f25', 'saved': 'gps_preferences.text_b6cfde6d56a6', 'explain': 'gps_preferences.text_eec14759e323', 'share': 'gps_preferences.text_78dc7d937ef4', 'stop_share': 'gps_preferences.text_f8e236cd81f8', 'live': 'gps_preferences.text_a791aee039a1', 'off': 'gps_preferences.text_05c1f5939955', 'waiting': 'gps_preferences.text_e4fea0cdfff3', 'error': 'gps_preferences.text_ee6901ede6b8', 'conflict': 'gps_preferences.text_8724b030c193', 'denied': 'gps_preferences.text_fcdb8b5813ec', 'inactive': 'gps_preferences.text_9d6e26f1b435', 'stale': 'gps_preferences.text_e1a458392a9b', 'peers': 'gps_preferences.text_32a4dd2874cf', 'help': 'gps_preferences.text_4555f0787f33', 'history': 'gps_preferences.text_9534ef329eb0'}
INTERVAL=300
TTL=600
FIELDS={'elapsed_ms':'show_elapsed','stopped_ms':'show_stopped','speed':'show_speed','train_number':'show_train','first_name':'show_first_name'}


def msg(name):return source(KEYS[name])


class Preferences(BaseModel):
    model_config=ConfigDict(extra='forbid')
    stop_minutes:Literal[1,2,4,5,10,15]=2
    marker:Literal['electric','steam','diesel','tank','circle']='electric'
    show_elapsed:StrictBool=True
    show_stopped:StrictBool=True
    show_speed:StrictBool=True
    show_train:StrictBool=True
    show_first_name:StrictBool=False
    share_enabled:StrictBool=False


class SettingsWrite(Preferences):
    expected_revision:int=Field(ge=0)


class StartSharing(BaseModel):
    model_config=ConfigDict(extra='forbid')
    journey_id:UUID


Finite=Annotated[float,Field(allow_inf_nan=False)]
class LivePoint(BaseModel):
    model_config=ConfigDict(extra='forbid')
    t:int=Field(ge=946684800000,le=4133980800000)
    lat:Finite=Field(ge=-90,le=90)
    lon:Finite=Field(ge=-180,le=180)
    accuracy:Finite=Field(ge=0,le=50)
    speed:Finite|None=Field(default=None,ge=0,le=200)
    elapsed_ms:int=Field(ge=0,le=172800000)
    stopped_ms:int=Field(ge=0,le=172800000)
    train_number:str=Field(pattern=r'^[A-Za-z0-9]{1,12}$')


def preferences(db,user_id):
    row=db.get(GpsPreference,user_id)
    return Preferences.model_validate_json(row.payload_json) if row else Preferences()


def create_router(require_account):
    def private(response:Response):response.headers['Cache-Control']='private, no-store'
    router=APIRouter(dependencies=[Depends(private)])
    driver=driver_dependency(require_account)
    def lock(db,user):db.scalar(select(User).where(User.id==user.id).with_for_update())
    def view(db,user):
        pref=preferences(db,user.id);row=db.get(GpsPreference,user.id);profile=db.get(TfProfile,user.id)
        return dict(**pref.model_dump(),owner_id=user.id,first_name=profile.first_name if profile else '',revision=row.revision if row else 0)

    @router.get('/tf/gps-marker-{kind}.png')
    def marker_image(kind:Literal['electric','steam','diesel','tank']):
        return FileResponse(Path(__file__).parent/'static'/f'gps-marker-{kind}.png',media_type='image/png')

    @router.get('/tf/gps-settings.js')
    def script():return FileResponse(Path(__file__).parent/'static'/'gps-settings.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})

    @router.get('/api/v1/tf/gps-settings')
    def read(user=Depends(driver),db:Session=Depends(database_session)):return view(db,user)

    @router.put('/api/v1/tf/gps-settings')
    def save(data:SettingsWrite,user=Depends(driver),db:Session=Depends(database_session)):
        lock(db,user);row=db.get(GpsPreference,user.id)
        if data.expected_revision!=(row.revision if row else 0):raise HTTPException(409,msg('conflict'))
        payload=Preferences.model_validate(data.model_dump(exclude={'expected_revision'})).model_dump_json()
        if row:row.payload_json=payload;row.revision+=1
        else:db.add(GpsPreference(user_id=user.id,payload_json=payload,revision=1))
        if not data.share_enabled:db.execute(delete(GpsLivePosition).where(GpsLivePosition.user_id==user.id))
        db.commit();return view(db,user)

    @router.post('/api/v1/tf/gps-sharing/start')
    def start(data:StartSharing,user=Depends(driver),db:Session=Depends(database_session)):
        lock(db,user)
        if not preferences(db,user.id).share_enabled:raise HTTPException(403,msg('denied'))
        row=db.get(GpsLivePosition,user.id)
        if not row:row=GpsLivePosition(user_id=user.id);db.add(row)
        row.session_id=str(uuid4());row.journey_id=str(data.journey_id);row.point_json=None;row.updated_at=None
        db.commit();return dict(session_id=row.session_id,interval_seconds=INTERVAL,expires_after_seconds=TTL)

    def owned(db,user,session_id):
        row=db.get(GpsLivePosition,user.id)
        if not row or row.session_id!=str(session_id):raise HTTPException(409,msg('inactive'))
        return row

    @router.put('/api/v1/tf/gps-sharing/{session_id}')
    def update(session_id:UUID,data:LivePoint,user=Depends(driver),db:Session=Depends(database_session)):
        lock(db,user)
        if not preferences(db,user.id).share_enabled:raise HTTPException(403,msg('denied'))
        row=owned(db,user,session_id);now=now_utc();stamp=int(now.replace(tzinfo=timezone.utc).timestamp()*1000)
        if not stamp-120000<=data.t<=stamp+30000:raise HTTPException(422,msg('stale'))
        if row.updated_at and (now-row.updated_at).total_seconds()<INTERVAL:return dict(accepted=False,interval_seconds=INTERVAL)
        row.point_json=data.model_dump_json();row.updated_at=now;db.commit()
        return dict(accepted=True,interval_seconds=INTERVAL)

    @router.delete('/api/v1/tf/gps-sharing/{session_id}')
    def stop(session_id:UUID,user=Depends(driver),db:Session=Depends(database_session)):
        lock(db,user);db.execute(delete(GpsLivePosition).where(GpsLivePosition.user_id==user.id,GpsLivePosition.session_id==str(session_id)));db.commit();return dict(ok=True)

    @router.get('/api/v1/tf/gps-shared-positions')
    def feed(user=Depends(driver),db:Session=Depends(database_session)):
        now=now_utc();viewer=preferences(db,user.id);rows=db.execute(select(GpsLivePosition,User,TfProfile).join(User,User.id==GpsLivePosition.user_id).join(TfProfile,TfProfile.user_id==User.id).where(GpsLivePosition.user_id!=user.id,GpsLivePosition.updated_at>=now-timedelta(seconds=TTL),User.role=='tf').limit(500))
        result=[]
        for row,sender,profile in rows:
            pref=preferences(db,sender.id)
            if not pref.share_enabled or not account_active(db,sender) or not row.point_json:continue
            point=json.loads(row.point_json)
            if point['t']<int(now.replace(tzinfo=timezone.utc).timestamp()*1000)-TTL*1000:continue
            item={key:point[key] for key in ('lat','lon','t')};item.update(id=sender.id,marker=pref.marker)
            for field,option in FIELDS.items():
                if getattr(pref,option) and getattr(viewer,option):item[field]=profile.first_name if field=='first_name' else point[field]
            result.append(item)
        return dict(positions=result,expires_after_seconds=TTL)
    return router
