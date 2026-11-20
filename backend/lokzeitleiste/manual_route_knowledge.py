"""Explicitly confirmed route knowledge, with no fabricated GPS rides or trip counts."""
import json
from datetime import datetime,date
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select,inspect,text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import database_session
from .models import ManualRouteKnowledge,User
from .tf_portal import driver_dependency
from .operating_points import load_points
from .route_knowledge_mapping import match
from .route_knowledge_import import digest,packed,identity
from .localization import source
KEYS={'view': 'text_b7f9ac3a3f45', 'create': 'text_2e35159db647', 'start': 'text_c9fa26ef1765', 'until': 'text_47e8bd8d5b40', 'save': 'text_c6647df04fbb', 'undo': 'text_3727c732d5d8', 'reset': 'text_e87fcb0a884a', 'help': 'text_60ee27e69534', 'choose': 'text_6882a967cd71', 'invalid': 'text_3152f57cf1a9', 'date_error': 'text_f8bd4777a8f6', 'saved': 'text_a5638474e6bc', 'error': 'text_2754b9f01859', 'duplicate': 'text_d39b25fbacf6', 'layer': 'text_43066bcd226f', 'loading': 'text_0569e84397dc', 'failed': 'text_698b8320d21b', 'map_help': 'text_7ba4e05ed470'}

KEYS.update({'selected_title': 'text_62d2e5e29f03', 'saved_title': 'text_804e444f8e53', 'ds100': 'text_76905d6d3c00', 'station': 'text_0b3d3c256426', 'route': 'text_0e142f788945', 'km': 'text_c814ffa5778c', 'from': 'text_1f8316cccfdd', 'to': 'text_a8e1eb64181d', 'valid_date': 'text_c3e6edf505b9', 'reload_saved': 'text_9223bb62836b', 'saved_hint': 'text_c45f07603ede', 'save_changes': 'text_1c7e29dae522', 'continue_here': 'text_d180bb4df449', 'empty_saved': 'text_b48030b6ff54', 'list_error': 'text_307f554ef539', 'conflict': 'text_37b4d7cab3e1', 'not_found': 'text_0336e2a4df6f', 'editing': 'text_4b6c686e1fb1', 'discard': 'text_99d0336a2152'})

def message(key):return source('manual_route.'+KEYS[key])
def today():return datetime.now(ZoneInfo('Europe/Berlin')).date()
def maximum(day):
    try:return day.replace(year=day.year+1)
    except ValueError:return day.replace(year=day.year+1,day=28)

class RouteInput(BaseModel):
    waypoints:list[str]=Field(min_length=2,max_length=1001)
    routes:list[str|list[str]]=Field(min_length=1,max_length=1000)
    valid_until:date


class RouteEdit(RouteInput):
    expected_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')


def saved_route(item):
    payload=json.loads(item.payload_json)
    return dict(id=item.id,from_code=payload['waypoints'][0],to_code=payload['waypoints'][-1],valid_until=payload['valid_until'],waypoints=payload['waypoints'],routes=payload['routes'],revision=digest(item.payload_json))


def saved_routes(db,owner_id):
    return [saved_route(row) for row in db.scalars(select(ManualRouteKnowledge).where(ManualRouteKnowledge.owner_id==owner_id).order_by(ManualRouteKnowledge.id.desc()))]


def validate(data):
    day=today()
    if not day<=data.valid_until<=maximum(day):raise HTTPException(422,message('date_error'))
    codes=[' '.join(code.upper().split()) for code in data.waypoints]
    if any(not code or len(code)>10 for code in codes) or len(data.routes)!=len(codes)-1:raise HTTPException(422,message('invalid'))
    refs={}
    for point in load_points()['points']:refs.setdefault(point['code'],point)
    legs=[]
    routes=[]
    for start,end,selection in zip(codes,codes[1:],data.routes):
        selected=selection if isinstance(selection,list) else [selection]
        if not 1<=len(selected)<=16 or start==end or start not in refs or end not in refs:raise HTTPException(422,message('invalid'))
        group=[];matches=[]
        for route in selected:
            if not route.isascii() or not route.isdigit() or len(route)>6:raise HTTPException(422,message('invalid'))
            code=str(int(route))
            if code in group:raise HTTPException(422,message('invalid'))
            group.append(code)
            row=dict(section=refs[start]['name']+' – '+refs[end]['name'],route_number=code,status='streckenkundig',valid_until=data.valid_until.isoformat(),acquired_since='',acquisition_trips='',from_code=start,to_code=end)
            mapped=match(row)
            if mapped['status']!='mapped':raise HTTPException(422,message('invalid'))
            matches.append(mapped);legs.append(row)
        if len(group)>1:
            from .manual_route_parallel import parallel
            if not parallel(matches):raise HTTPException(422,message('invalid'))
        routes.append(sorted(group,key=int) if len(group)>1 else group[0])
    return dict(waypoints=codes,routes=routes,valid_until=data.valid_until.isoformat(),legs=legs)



def entries(db,owner_id):
    result=[]
    for item in db.scalars(select(ManualRouteKnowledge).where(ManualRouteKnowledge.owner_id==owner_id).order_by(ManualRouteKnowledge.id)):
        for i,row in enumerate(json.loads(item.payload_json)['legs']):result.append(dict(id='manual-'+str(item.id)+'-'+str(i),**row,map_match=match(row),manual=True))
    return result


def create_router(require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.get('/api/v1/tf/route-knowledge/manual')
    def listing(user:User=Depends(driver),db:Session=Depends(database_session)):
        return dict(owner_id=user.id,items=saved_routes(db,user.id))
    @router.post('/api/v1/tf/route-knowledge/manual',status_code=201)
    def save(data:RouteInput,user:User=Depends(driver),db:Session=Depends(database_session)):
        identity(db,user,lock=True)
        payload=validate(data);key=digest(packed([payload['waypoints'],payload['routes']]))
        if db.scalar(select(ManualRouteKnowledge.id).where(ManualRouteKnowledge.owner_id==user.id,ManualRouteKnowledge.path_key==key)):raise HTTPException(409,message('duplicate'))
        item=ManualRouteKnowledge(owner_id=user.id,path_key=key,payload_json=packed(payload));db.add(item)
        try:db.commit()
        except IntegrityError:db.rollback();raise HTTPException(409,message('duplicate')) from None
        return dict(id=item.id,owner_id=user.id,items=entries(db,user.id),saved_routes=saved_routes(db,user.id))
    @router.put('/api/v1/tf/route-knowledge/manual/{route_id}')
    def update(route_id:int,data:RouteEdit,user:User=Depends(driver),db:Session=Depends(database_session)):
        identity(db,user,lock=True)
        item=db.scalar(select(ManualRouteKnowledge).where(ManualRouteKnowledge.id==route_id,ManualRouteKnowledge.owner_id==user.id).with_for_update())
        if item is None:raise HTTPException(404,message('not_found'))
        if digest(item.payload_json)!=data.expected_sha256:raise HTTPException(409,message('conflict'))
        payload=validate(data);key=digest(packed([payload['waypoints'],payload['routes']]))
        if db.scalar(select(ManualRouteKnowledge.id).where(ManualRouteKnowledge.owner_id==user.id,ManualRouteKnowledge.path_key==key,ManualRouteKnowledge.id!=item.id)):raise HTTPException(409,message('duplicate'))
        item.path_key=key;item.payload_json=packed(payload)
        try:db.commit()
        except IntegrityError:db.rollback();raise HTTPException(409,message('duplicate')) from None
        return dict(id=item.id,owner_id=user.id,items=entries(db,user.id),saved_routes=saved_routes(db,user.id))
    return router


def ensure_storage(connection):
    """Widen the existing MySQL column without rewriting or deleting route records."""
    if connection.dialect.name not in ('mysql','mariadb'):return
    column=next(c for c in inspect(connection).get_columns('manual_route_knowledge') if c['name']=='payload_json')
    if type(column['type']).__name__.upper()=='TEXT':
        connection.execute(text('ALTER TABLE manual_route_knowledge MODIFY COLUMN payload_json MEDIUMTEXT NOT NULL'))
