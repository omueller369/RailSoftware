"""Private, paginated map geometry derived only from the driver's measured fixes."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import database_session
from .models import TrainGpsRecording, User
from .gps_analysis import distance
from .tf_portal import driver_dependency


def route_segments(points):
    segments=[];segment=[];last=None
    def finish():
        if segment and last and segment[-1]!=[last['lat'],last['lon']]:segment.append([last['lat'],last['lon']])
        if len(segment)>1:segments.append(segment.copy())
    for point in points:
        valid=point.get('accuracy',100001)<=50 and 47<=point.get('lat',0)<=55.5 and 5<=point.get('lon',0)<=16
        if not valid or last and (point.get('break_before') or not 0<point['t']-last['t']<=30000):
            finish()
            segment=[]
        if valid:
            # Preserve endpoints while reducing dense stationary samples.
            if not segment or distance(dict(lat=segment[-1][0],lon=segment[-1][1]),point)>=30:
                segment.append([point['lat'],point['lon']])
            last=point
        else:last=None
    finish()
    return segments


def create_router(require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/tf/route-knowledge.js')
    def script():return FileResponse(Path(__file__).parent/'static'/'route-knowledge.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/route-knowledge')
    def listing(offset:int=Query(default=0,ge=0),user:User=Depends(driver),db:Session=Depends(database_session)):
        rows=list(db.scalars(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id).order_by(TrainGpsRecording.id.desc()).offset(offset).limit(21)))
        items=[]
        for row in rows[:20]:
            payload=json.loads(row.payload_json)
            items.append(dict(journey_id=row.journey_id,segments=route_segments(payload.get('points',[]))))
        return dict(owner_id=user.id,items=items,next_offset=offset+20 if len(rows)>20 else None)
    return router
