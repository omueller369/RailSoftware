# Gemeinsame Verarbeitung für Streckenkenntnisse und Referenzgeometrie.
"""Private, paginated map geometry derived only from the driver's measured fixes."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request, HTTPException
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
            # Die Endpunkte erhalten und nur dichte Messungen im Stillstand reduzieren.
            if not segment or distance(dict(lat=segment[-1][0],lon=segment[-1][1]),point)>=30:
                segment.append(coordinate(point))
            last=point
        else:last=None
    finish()
    return segments


def create_router(require_account,*,target_dependency=None,api_prefix='/api/v1/tf'):
    router=APIRouter();driver=target_dependency or driver_dependency(require_account)
    from .route_knowledge_import import create_router as import_router
    router.include_router(import_router(require_account,target_dependency=target_dependency,api_prefix=api_prefix))
    from .tf_knowledge import create_router as inventory_router
    router.include_router(inventory_router(require_account,target_dependency=target_dependency,api_prefix=api_prefix))
    @router.get('/tf/rail-network-data.js')
    def network_data(request:Request):
        compressed=any(part.split(';')[0].strip().lower()=='gzip' and not any(option.strip() in {'q=0','q=0.0','q=0.00','q=0.000'} for option in part.split(';')[1:]) for part in request.headers.get('accept-encoding','').split(','))
        headers={'Cache-Control':'public, max-age=31536000, immutable','Vary':'Accept-Encoding'}
        if compressed:headers['Content-Encoding']='gzip'
        name='rail-network-data.js'+('.gz' if compressed else '')
        return FileResponse(Path(__file__).parent/'static'/name,media_type='text/javascript',headers=headers)
    @router.get('/tf/poland-rail.js')
    def poland_script():return FileResponse(Path(__file__).parent/'static'/'poland-rail.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/poland-rail-data/{tile}.js')
    def poland_tile(tile:str):
        import re
        if not re.fullmatch(r'(overview|tile-\d{1,3}-\d{1,3})',tile):raise HTTPException(404)
        path=Path(__file__).parent/'static'/'poland-rail-data'/(tile+'.js')
        if not path.is_file():raise HTTPException(404)
        return FileResponse(path,media_type='text/javascript',headers={'Cache-Control':'public, max-age=86400'})
    @router.get('/tf/route-imports.js')
    def import_script():return FileResponse(Path(__file__).parent/'static'/'route-imports.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/route-coverage.js')
    def coverage_script():return FileResponse(Path(__file__).parent/'static'/'route-coverage.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/m1-basemap-data.js')
    def basemap_script():return FileResponse(Path(__file__).parent/'static'/'m1-basemap-data.js',media_type='text/javascript',headers={'Cache-Control':'public, max-age=86400'})
    @router.get('/tf/m1-map.js')
    def m1_script():return FileResponse(Path(__file__).parent/'static'/'m1-map.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/gps-route-tools.js')
    def gps_tools_script():return FileResponse(Path(__file__).parent/'static'/'gps-route-tools.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/route-table.js')
    def route_table_script():return FileResponse(Path(__file__).parent/'static'/'route-table.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/route-editor.js')
    def editor_script():return FileResponse(Path(__file__).parent/'static'/'route-editor.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/rail-network.js')
    def network_script():return FileResponse(Path(__file__).parent/'static'/'rail-network.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/route-knowledge.js')
    def script():return FileResponse(Path(__file__).parent/'static'/'route-knowledge.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get(api_prefix+'/route-knowledge')
    def listing(offset:int=Query(default=0,ge=0),dates:bool=Query(default=False),user:User=Depends(driver),db:Session=Depends(database_session)):
        rows=list(db.scalars(select(TrainGpsRecording).where(TrainGpsRecording.owner_id==user.id).order_by(TrainGpsRecording.id.desc()).offset(offset).limit(21)))
        items=[]
        for row in rows[:20]:
            payload=json.loads(row.payload_json)
            field='timed_segments' if dates else 'segments'
            from .manual_route_gps import gps_metadata
            items.append({**gps_metadata(row,payload),field:route_segments(payload.get('points',[]),timed=dates)})
        return dict(owner_id=user.id,items=items,next_offset=offset+20 if len(rows)>20 else None)
    if target_dependency is not None:router.routes[:]=[route for route in router.routes if not getattr(route,'path',None) or route.path.startswith(api_prefix)]
    return router
