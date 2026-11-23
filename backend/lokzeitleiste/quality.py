# Prüfentscheidungen sind an den angezeigten Änderungsstand gebunden, damit parallele Bearbeitungen sichtbar bleiben.
# Prüfentscheidungen bleiben versioniert; die Fachbestände werden nicht durch Anzeige- oder Diagnosefunktionen verändert.
import hashlib,json
from datetime import date
from pathlib import Path
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Query,Response
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,func
from .db import database_session
from .models import (User,TfProfile,EmployeeCategory,DutyReport,DutyReportCorrection,ReportReviewEvent,
 RailwayStation,RailwayStationCoordinates,StationCoordinateContribution,CoordinateReviewEvent,
 RouteKnowledgeEntry,ManualRouteKnowledge,PolandRouteKnowledge,TfLocationKnowledge,TfRollingStockKnowledge,
 BackupSettings,BackupRun,now_utc)
from .accounts.access import demand,permissions
from .localization import source
from .location_knowledge import validity,today
from .tf_portal import driver_dependency
STATIC=Path(__file__).parent/'static'
def text(key):return source('quality.text_'+hashlib.sha256(('quality.'+key).encode()).hexdigest()[:12])
def payload_hash(report):return hashlib.sha256(report.payload_json.encode()).hexdigest()
def review_view(db,report):
    from .documents.archive import report_version
    version=report_version(json.loads(report.payload_json));sha=payload_hash(report)
    events=list(db.scalars(select(ReportReviewEvent).where(ReportReviewEvent.report_id==report.id).order_by(ReportReviewEvent.id)))
    latest=next((e for e in reversed(events) if e.version==version and e.payload_sha256==sha),None)
    corrections=list(db.scalars(select(DutyReportCorrection).where(DutyReportCorrection.report_id==report.id)))
    returned=any(e.completed_at is None for e in corrections)
    history=[dict(id=e.id,state=e.state,version=e.version,comment=e.comment,actor_id=e.actor_id,at=e.created_at.isoformat()) for e in events]
    for e in corrections:
        history.append(dict(state='returned',version=e.version,comment=e.reason,actor_id=e.returned_by,at=e.returned_at.isoformat()))
        if e.completed_at:history.append(dict(state='received',version=e.version+1,comment='',actor_id=e.owner_id,at=e.completed_at.isoformat()))
    return dict(state='returned' if returned else latest.state if latest else 'received',revision=events[-1].id if events else 0,payload_sha256=sha,version=version,history=sorted(history,key=lambda e:e['at']))
class ReviewInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    state:Literal['received','in_review','approved']
    comment:str=Field(default='',max_length=2000)
    expected_revision:int=Field(ge=0)
    expected_version:int=Field(ge=1)
    expected_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
class CoordinateDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:Literal['confirm','reject']
    expected_token:str=Field(pattern=r'^[a-f0-9]{64}$')
    comment:str=Field(min_length=1,max_length=2000)
class BackupInput(BaseModel):
    enabled:bool

def expiry_rows(db,owner):
    items=[]
    def add(kind,ident,name,until,origin):items.append(dict(kind=kind,id=ident,name=name,valid_until=until or '',state={'unknown':'missing'}.get(validity(until),validity(until)),origin=origin))
    protected=set()
    for row in db.scalars(select(RouteKnowledgeEntry).where(RouteKnowledgeEntry.owner_id==owner)):
        p=json.loads(row.source_json);key=(str(p.get('route_number','')),tuple(sorted([p.get('from_code',''),p.get('to_code','')])) )
        if p.get('status')=='streckenkundig':protected.add(key)
        add('routes',row.id,' · '.join(str(p.get(k,'')) for k in ['route_number','from_code','to_code']),p.get('valid_until'),'import')
    for row in db.scalars(select(ManualRouteKnowledge).where(ManualRouteKnowledge.owner_id==owner)):
        p=json.loads(row.payload_json);way=p.get('waypoints',[]);routes=p.get('routes',[])
        key=(str(routes[0]) if len(routes)==1 else '',tuple(sorted([way[0],way[-1]])) if way else ())
        if key not in protected:add('routes',row.id,' → '.join(way),p.get('valid_until'),'manual')
    for row in db.scalars(select(PolandRouteKnowledge).where(PolandRouteKnowledge.owner_id==owner)):
        p=json.loads(row.payload_json);points=p.get('points',[]);add('routes',row.id,' → '.join((e.get('name') or e['id']) for e in [points[0],points[-1]]) if points else '',p.get('valid_until'),'poland')
    for row in db.scalars(select(TfLocationKnowledge).where(TfLocationKnowledge.owner_id==owner)):add('places',row.id,row.ds100+' · '+row.station_name,row.known_until,'inventory')
    for row in db.scalars(select(TfRollingStockKnowledge).where(TfRollingStockKnowledge.owner_id==owner)):add('classes',row.id,row.series,row.valid_until,'inventory')
    return items

def create_router(require_account,require_admin):
    def private(response:Response):response.headers['Cache-Control']='private, no-store'
    router=APIRouter(dependencies=[Depends(private)]);driver=driver_dependency(require_account)
    @router.get('/tf/quality-ui.js')
    def script():return FileResponse(STATIC/'quality-ui.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/admin/quality')
    def page():return FileResponse(STATIC/'admin-quality.html')
    @router.get('/admin/quality.js')
    def admin_script():return FileResponse(STATIC/'admin-quality.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    def expiry_result(db,user,state,q,offset,limit):
        rows=expiry_rows(db,user.id);counts={s:sum(r['state']==s for r in rows) for s in ['valid','expiring','expired','missing']}
        rows=[r for r in rows if (not state or r['state']==state) and (not q or q.casefold() in r['name'].casefold())];rows.sort(key=lambda r:({'expired':0,'expiring':1,'missing':2,'valid':3}[r['state']],r['valid_until'],r['name']))
        return dict(owner_id=user.id,counts=counts,items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit)
    @router.get('/api/v1/tf/quality/knowledge')
    def own_expiry(state:Literal['valid','expiring','expired','missing']|None=None,q:str=Query(default='',max_length=255),offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),user=Depends(driver),db=Depends(database_session)):
        return expiry_result(db,user,state,q,offset,limit)
    @router.get('/api/v1/admin/quality/knowledge/{tf_id}')
    def staff_expiry(tf_id:int,state:Literal['valid','expiring','expired','missing']|None=None,q:str=Query(default='',max_length=255),offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),actor=Depends(require_admin),db=Depends(database_session)):
        demand(db,actor,'knowledge',1);user=db.get(User,tf_id);category=db.get(EmployeeCategory,tf_id)
        if not user or user.role!='tf' or category and category.category!='tf' or not db.get(TfProfile,tf_id):raise HTTPException(404)
        return expiry_result(db,user,state,q,offset,limit)
    @router.post('/api/v1/admin/work-reports/{report_id}/review')
    def report_review(report_id:int,data:ReviewInput,actor=Depends(require_admin),db=Depends(database_session)):
        demand(db,actor,'work_reports',2)
        report=db.scalar(select(DutyReport).where(DutyReport.id==report_id).with_for_update())
        if not report:raise HTTPException(404)
        current=review_view(db,report)
        if current['state']=='returned' or (current['version'],current['revision'],current['payload_sha256'])!=(data.expected_version,data.expected_revision,data.expected_sha256):raise HTTPException(409,text('changed'))
        if data.state=='approved' and current['state']!='in_review':raise HTTPException(409,text('changed'))
        row=ReportReviewEvent(report_id=report.id,actor_id=actor.id,version=current['version'],payload_sha256=current['payload_sha256'],state=data.state,comment=data.comment.strip());db.add(row);db.commit();return review_view(db,report)
    @router.get('/api/v1/admin/quality/coordinates')
    def coordinate_list(offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),pending:bool=True,actor=Depends(require_admin),db=Depends(database_session)):
        demand(db,actor,'employees',1)
        query=select(StationCoordinateContribution).where(StationCoordinateContribution.owner_id.is_not(None))
        if pending:query=query.where(~select(CoordinateReviewEvent.id).where(CoordinateReviewEvent.contribution_id==StationCoordinateContribution.id).exists())
        total=db.scalar(select(func.count()).select_from(query.subquery()));rows=db.scalars(query.order_by(StationCoordinateContribution.id.desc()).offset(offset).limit(limit));items=[]
        from .station_coordinate_contributions import current
        for r in rows:
            station=db.get(RailwayStation,r.code)
            if not station:continue
            point=db.get(RailwayStationCoordinates,r.code);events=db.scalars(select(CoordinateReviewEvent).where(CoordinateReviewEvent.contribution_id==r.id).order_by(CoordinateReviewEvent.id))
            items.append(dict(id=r.id,code=r.code,name=station.name,owner_id=r.owner_id,at=r.created_at.isoformat(),before=json.loads(r.before_json) if r.before_json else None,after=json.loads(r.after_json),current=current(station,point),proposal=json.loads(r.proposal_json),history=[dict(id=e.id,decision=e.decision,comment=e.comment,actor_id=e.actor_id,at=e.created_at.isoformat()) for e in events]))
        return dict(items=items,total=total,offset=offset,limit=limit,can_write=permissions(db,actor)['employees']>=2)
    @router.post('/api/v1/admin/quality/coordinates/{entry_id}')
    def coordinate_decision(entry_id:int,data:CoordinateDecision,actor=Depends(require_admin),db=Depends(database_session)):
        demand(db,actor,'employees',2)
        proposal=db.get(StationCoordinateContribution,entry_id)
        if not proposal or proposal.owner_id is None:raise HTTPException(404)
        station=db.scalar(select(RailwayStation).where(RailwayStation.code==proposal.code).with_for_update());point=db.get(RailwayStationCoordinates,proposal.code)
        from .station_coordinate_contributions import current
        live=current(station,point)
        if live['token']!=data.expected_token or db.scalar(select(CoordinateReviewEvent.id).where(CoordinateReviewEvent.contribution_id==entry_id)):raise HTTPException(409,text('changed'))
        if not data.comment.strip():raise HTTPException(422,text('comment'))
        if data.decision=='reject':
            if live['coordinate']!=json.loads(proposal.after_json):raise HTTPException(409,text('changed'))
            before=json.loads(proposal.before_json) if proposal.before_json else None
            if before:
                if point is None:point=RailwayStationCoordinates(code=station.code);db.add(point)
                for k in ['latitude','longitude','catalog_name','source_name','source_url','source_date']:setattr(point,k,before[k])
                point.max_spread_m=0
            elif point is not None:db.delete(point);point=None
            # Eine neue Revision sorgt dafür, dass auch andere Geräte die Rücknahme laden.
            db.add(StationCoordinateContribution(request_id=str(uuid4()),owner_id=None,code=station.code,proposal_json=json.dumps(dict(review_of=entry_id)),before_json=json.dumps(live['coordinate']),after_json=json.dumps(current(station,point)['coordinate'])))
        db.add(CoordinateReviewEvent(contribution_id=entry_id,actor_id=actor.id,decision=data.decision,comment=data.comment.strip()));db.commit();return dict(state='verified')
    @router.get('/api/v1/admin/quality/backups')
    def backup_status(actor=Depends(require_admin),db=Depends(database_session)):
        if actor.role!='admin':raise HTTPException(403,text('forbidden'))
        settings=db.get(BackupSettings,1)
        return dict(enabled=settings.enabled if settings else True,requested=settings.requested if settings else False,items=[dict(id=r.id,state=r.state,created_at=r.created_at.isoformat(),completed_at=r.completed_at.isoformat() if r.completed_at else None,summary=json.loads(r.summary_json)) for r in db.scalars(select(BackupRun).order_by(BackupRun.created_at.desc()).limit(20))])
    @router.put('/api/v1/admin/quality/backups')
    def backup_settings(data:BackupInput,actor=Depends(require_admin),db=Depends(database_session)):
        if actor.role!='admin':raise HTTPException(403,text('forbidden'))
        settings=db.get(BackupSettings,1)
        if not settings:settings=BackupSettings(id=1);db.add(settings)
        settings.enabled=data.enabled;db.commit();return dict(enabled=settings.enabled)
    @router.post('/api/v1/admin/quality/backups/request')
    def request_backup(actor=Depends(require_admin),db=Depends(database_session)):
        if actor.role!='admin':raise HTTPException(403,text('forbidden'))
        settings=db.get(BackupSettings,1)
        if not settings:settings=BackupSettings(id=1);db.add(settings)
        settings.requested=True;db.commit();return dict(state='queued')
    return router
