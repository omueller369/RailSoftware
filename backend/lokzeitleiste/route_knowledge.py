"""Private, paginated map geometry derived only from the driver's measured fixes."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import database_session
from .models import TrainGpsRecording, User
from .gps_analysis import distance
from .tf_portal import driver_dependency


def route_segments(points,timed=False):
    segments=[];segment=[];last=None
    def coordinate(point):return [point['lat'],point['lon'],point.get('t')] if timed else [point['lat'],point['lon']]
    def finish():
        if segment and last and segment[-1][:2]!=[last['lat'],last['lon']]:segment.append(coordinate(last))
        if len(segment)>1:segments.append(segment.copy())
    for point in points:
        valid=point.get('accuracy',100001)<=50 and 47<=point.get('lat',0)<=55.5 and 5<=point.get('lon',0)<=16
        if not valid or last and (point.get('break_before') or not 0<point['t']-last['t']<=30000):
            finish()
            segment=[]
        if valid:
            # Preserve endpoints while reducing dense stationary samples.
            if not segment or distance(dict(lat=segment[-1][0],lon=segment[-1][1]),point)>=30:
                segment.append(coordinate(point))
            last=point
        else:last=None
    finish()
    return segments


def create_router(require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    from .route_knowledge_import import create_router as import_router
    router.include_router(import_router(require_account))
    from .tf_knowledge import create_router as inventory_router
    router.include_router(inventory_router(require_account))
    @router.get('/tf/rail-network-data.js')
    def network_data(request:Request):
        compressed=any(part.split(';')[0].strip().lower()=='gzip' and not any(option.strip() in {'q=0','q=0.0','q=0.00','q=0.000'} for option in part.split(';')[1:]) for part in request.headers.get('accept-encoding','').split(','))
        headers={'Cache-Control':'public, max-age=31536000, immutable','Vary':'Accept-Encoding'}
        if compressed:headers['Content-Encoding']='gzip'
        name='rail-network-data.js'+('.gz' if compressed else '')
        return FileResponse(Path(__file__).parent/'static'/name,media_type='text/javascript',headers=headers)
    @router.get('/tf/route-imports.js')
    def import_script():return FileResponse(Path(__file__).parent/'static'/'route-imports.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/route-coverage.js')
    def coverage_script():return FileResponse(Path(__file__).parent/'static'/'route-coverage.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/rail-network.js')
    def network_script():return FileResponse(Path(__file__).parent/'static'/'rail-network.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/route-knowledge.js')
    def script():return FileResponse(Path(__file__).parent/'static'/'route-knowledge.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/route-knowledge')
    def listing(offset:int=Query(default=0,ge=0),dates:bool=Query(default=False),user:User=Depends(driver),db:Session=Depends(database_session)):
        rows=list(db.scalars(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id).order_by(TrainGpsRecording.id.desc()).offset(offset).limit(21)))
        items=[]
        for row in rows[:20]:
            payload=json.loads(row.payload_json)
            field='timed_segments' if dates else 'segments'
            items.append({'journey_id':row.journey_id,field:route_segments(payload.get('points',[]),timed=dates)})
        return dict(owner_id=user.id,items=items,next_offset=offset+20 if len(rows)>20 else None)
    return router
