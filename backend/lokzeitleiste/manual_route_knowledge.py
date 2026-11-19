"""Explicitly confirmed route knowledge, with no fabricated GPS rides or trip counts."""
import json
from datetime import datetime,date
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
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

def message(key):return source('manual_route.'+KEYS[key])
def today():return datetime.now(ZoneInfo('Europe/Berlin')).date()
def maximum(day):
    try:return day.replace(year=day.year+1)
    except ValueError:return day.replace(year=day.year+1,day=28)

class RouteInput(BaseModel):
    waypoints:list[str]=Field(min_length=2,max_length=101)
    routes:list[str]=Field(min_length=1,max_length=100)
    valid_until:date


def validate(data):
    day=today()
    if not day<=data.valid_until<=maximum(day):raise HTTPException(422,message('date_error'))
    codes=[' '.join(code.upper().split()) for code in data.waypoints]
    if any(not code or len(code)>10 for code in codes) or len(data.routes)!=len(codes)-1:raise HTTPException(422,message('invalid'))
    refs={}
    for point in load_points()['points']:refs.setdefault(point['code'],point)
    legs=[]
    for start,end,route in zip(codes,codes[1:],data.routes):
        if start==end or start not in refs or end not in refs or not route.isascii() or not route.isdigit() or len(route)>6:raise HTTPException(422,message('invalid'))
        row=dict(section=refs[start]['name']+' – '+refs[end]['name'],route_number=str(int(route)),status='streckenkundig',valid_until=data.valid_until.isoformat(),acquired_since='',acquisition_trips='',from_code=start,to_code=end)
        if match(row)['status']!='mapped':raise HTTPException(422,message('invalid'))
        legs.append(row)
    return dict(waypoints=codes,routes=[r['route_number'] for r in legs],valid_until=data.valid_until.isoformat(),legs=legs)


def entries(db,owner_id):
    result=[]
    for item in db.scalars(select(ManualRouteKnowledge).where(ManualRouteKnowledge.owner_id==owner_id).order_by(ManualRouteKnowledge.id)):
        for i,row in enumerate(json.loads(item.payload_json)['legs']):result.append(dict(id='manual-'+str(item.id)+'-'+str(i),**row,map_match=match(row),manual=True))
    return result


def create_router(require_account):
    router=APIRouter();driver=driver_dependency(require_account)
    @router.post('/api/v1/tf/route-knowledge/manual',status_code=201)
    def save(data:RouteInput,user:User=Depends(driver),db:Session=Depends(database_session)):
        identity(db,user,lock=True)
        payload=validate(data);key=digest(packed([payload['waypoints'],payload['routes']]))
        if db.scalar(select(ManualRouteKnowledge.id).where(ManualRouteKnowledge.owner_id==user.id,ManualRouteKnowledge.path_key==key)):raise HTTPException(409,message('duplicate'))
        item=ManualRouteKnowledge(owner_id=user.id,path_key=key,payload_json=packed(payload));db.add(item)
        try:db.commit()
        except IntegrityError:db.rollback();raise HTTPException(409,message('duplicate')) from None
        return dict(id=item.id,owner_id=user.id,items=entries(db,user.id))
    return router
