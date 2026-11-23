"""Owned manual Polish paths validated against the separate OSM reference graph."""
import gzip,hashlib,json,math,re
from functools import lru_cache
from pathlib import Path
from datetime import date
from fastapi import APIRouter,Depends,HTTPException,Query
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict,StrictInt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import database_session
from .models import PolandRouteKnowledge,User,TfProfile,EmployeeCategory
from .tf_portal import driver_dependency
from .route_knowledge_import import digest,packed,identity
from .manual_route_knowledge import today,maximum
from .localization import source
REF=Path(__file__).parent/'reference/poland-stk';STATIC=Path(__file__).parent/'static'
def message(key):return source('poland_stk.text_'+hashlib.sha256(('poland_stk.'+key).encode()).hexdigest()[:12])
@lru_cache(maxsize=1)
def reference():
    raw=(REF/'graph.json.gz').read_bytes();manifest=json.loads((REF/'manifest.json').read_text());assert hashlib.sha256(raw).hexdigest()==manifest['graph_sha256'];graph=json.loads(gzip.decompress(raw));graph['revision']=manifest['graph_sha256'];graph['by_id']={p['id']:p for p in graph['points']};return graph
class RouteInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    network_revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    waypoints:list[str]=Field(min_length=2,max_length=1001)
    legs:list[list[list[StrictInt]]]=Field(min_length=1,max_length=1000)
    valid_until:date
class RouteEdit(RouteInput):
    expected_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
def geometry(graph,path,start):
    coords=[];node=start;visited={start}
    for index in path:
        if type(index) is not int or not 0<=index<len(graph['edges']):raise HTTPException(422,message('invalid'))
        a,b,length,points,*_=graph['edges'][index]
        if a==node:next_node=b;line=[points[i:i+2] for i in range(0,len(points),2)]
        elif b==node:next_node=a;line=[points[i:i+2] for i in range(len(points)-2,-1,-2)]
        else:raise HTTPException(422,message('not_connected'))
        if next_node in visited:raise HTTPException(422,message('invalid'))
        visited.add(next_node);coords.extend(line if not coords else line[1:]);node=next_node
    return node,coords

def parallel(paths,scale):
    from .manual_route_parallel import project,nearby
    projected=[[[project(lon/scale,lat/scale) for lon,lat in line]] for line in paths];south=min(lat/scale for line in paths for lon,lat in line);factor=40075016.686*math.cos(math.radians(south))*200/190
    return all(nearby(a,b,factor) and nearby(b,a,factor) for i,a in enumerate(projected) for b in projected[i+1:])

def validate(data,previous=None):
    day=today()
    if not day<=data.valid_until<=maximum(day):raise HTTPException(422,message('dates'))
    if len(data.legs)!=len(data.waypoints)-1 or any(len(p)>40 for p in data.waypoints):raise HTTPException(422,message('invalid'))
    graph=reference()
    if data.network_revision!=graph['revision']:
        if previous and data.network_revision==previous['network_revision'] and data.waypoints==previous['waypoints'] and data.legs==previous['legs']:
            return {**previous,'valid_until':data.valid_until.isoformat()}
        raise HTTPException(409,message('reference_changed'))
    points=[]
    for ident in data.waypoints:
        point=graph['by_id'].get(ident)
        if not point:raise HTTPException(422,message('invalid'))
        if point['node'] is None:raise HTTPException(422,message('unlinked'))
        points.append(point)
    used=set();total=0;all_count=0
    for a,b,choices in zip(points,points[1:],data.legs):
        if a['node']==b['node']:raise HTTPException(422,message('same_position'))
        if not 1<=len(choices)<=3:raise HTTPException(422,message('invalid'))
        lines=[];lengths=[];seen_choices=set()
        for path in choices:
            if not 1<=len(path)<=5000 or len(set(path))!=len(path) or tuple(path) in seen_choices:raise HTTPException(422,message('invalid'))
            seen_choices.add(tuple(path));all_count+=len(path)
            if all_count>20000:raise HTTPException(422,message('limit'))
            end,line=geometry(graph,path,a['node'])
            if end!=b['node']:raise HTTPException(422,message('not_connected'))
            lines.append(line);lengths.append(sum(graph['edges'][e][2] for e in path));used.update(path)
        if len(lines)>1 and not parallel(lines,graph['scale']):raise HTTPException(422,message('not_parallel'))
        total+=min(lengths)
    value=dict(network_revision=data.network_revision,waypoints=data.waypoints,legs=data.legs,valid_until=data.valid_until.isoformat(),points=points,scale=graph['scale'],geometry=[[i,graph['edges'][i][3]] for i in sorted(used)],length_m=round(total,2))
    if len(packed(value))>8000000:raise HTTPException(422,message('limit'))
    return value

def row_value(row):return dict(id=row.id,revision=digest(row.payload_json),**json.loads(row.payload_json))
def listing(db,user):return dict(owner_id=user.id,items=[row_value(r) for r in db.scalars(select(PolandRouteKnowledge).where(PolandRouteKnowledge.owner_id==user.id).order_by(PolandRouteKnowledge.id.desc()))])
def own(db,user,route_id,revision):
    row=db.scalar(select(PolandRouteKnowledge).where(PolandRouteKnowledge.owner_id==user.id,PolandRouteKnowledge.id==route_id).with_for_update())
    if not row:raise HTTPException(404,message('missing'))
    if digest(row.payload_json)!=revision:raise HTTPException(409,message('changed'))
    return row

def create_router(require_account,require_admin):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/tf/poland-stk-data/{name}.json')
    def public(name:str):
        if not re.fullmatch(r'(topology|manifest|geometry-\d{1,3})',name):raise HTTPException(404)
        path=STATIC/'poland-stk-data'/(name+'.json')
        if not path.is_file():raise HTTPException(404)
        return FileResponse(path,media_type='application/json',headers={'Cache-Control':'public, max-age=86400'})
    @router.get('/tf/poland-stk-worker.js')
    def worker_script():return FileResponse(STATIC/'poland-stk-worker.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/tf/poland-stk.js')
    def controller():return FileResponse(STATIC/'poland-stk.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/poland-route-knowledge/manual')
    def get(user=Depends(driver),db=Depends(database_session)):return listing(db,user)
    @router.post('/api/v1/tf/poland-route-knowledge/manual',status_code=201)
    def save(data:RouteInput,user=Depends(driver),db=Depends(database_session)):
        identity(db,user,lock=True);value=validate(data);key=digest(packed([value['network_revision'],value['waypoints'],value['legs']]))
        if db.scalar(select(PolandRouteKnowledge.id).where(PolandRouteKnowledge.owner_id==user.id,PolandRouteKnowledge.path_key==key)):raise HTTPException(409,message('duplicate'))
        row=PolandRouteKnowledge(owner_id=user.id,path_key=key,payload_json=packed(value));db.add(row)
        try:db.commit()
        except IntegrityError:db.rollback();raise HTTPException(409,message('duplicate')) from None
        return listing(db,user)
    @router.put('/api/v1/tf/poland-route-knowledge/manual/{route_id}')
    def update(route_id:int,data:RouteEdit,user=Depends(driver),db=Depends(database_session)):
        identity(db,user,lock=True);row=own(db,user,route_id,data.expected_sha256);value=validate(data,json.loads(row.payload_json));key=digest(packed([value['network_revision'],value['waypoints'],value['legs']]))
        if db.scalar(select(PolandRouteKnowledge.id).where(PolandRouteKnowledge.owner_id==user.id,PolandRouteKnowledge.path_key==key,PolandRouteKnowledge.id!=row.id)):raise HTTPException(409,message('duplicate'))
        row.path_key=key;row.payload_json=packed(value)
        try:db.commit()
        except IntegrityError:db.rollback();raise HTTPException(409,message('duplicate')) from None
        return listing(db,user)
    @router.delete('/api/v1/tf/poland-route-knowledge/manual/{route_id}')
    def remove(route_id:int,expected_sha256:str=Query(pattern=r'^[0-9a-f]{64}$'),user=Depends(driver),db=Depends(database_session)):
        identity(db,user,lock=True);row=own(db,user,route_id,expected_sha256);db.delete(row);db.commit();return listing(db,user)
    @router.get('/api/v1/admin/knowledge/{tf_id}/poland-route-knowledge/manual')
    def administrative(tf_id:int,actor=Depends(require_admin),db=Depends(database_session)):
        from .accounts.access import permissions
        if permissions(db,actor).get('knowledge',0)<1:raise HTTPException(403)
        user=db.get(User,tf_id);category=db.get(EmployeeCategory,tf_id)
        if not user or user.role!='tf' or category and category.category!='tf' or not db.get(TfProfile,tf_id):raise HTTPException(404)
        return listing(db,user)
    return router
