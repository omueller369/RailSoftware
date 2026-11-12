"""Administration inbox for finalized reports. Editing rules are deliberately deferred."""
import calendar
import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import database_session
from ..models import DutyReport, TfProfile, User, WorkEntry, EmployeeCategory
from ..localization import source
from ..accounts.employee_categories import category
from .service import report_view

STATIC = Path(__file__).parent.parent / 'static'


def create_router(require_admin):
    def no_store(response:Response):
        response.headers['Cache-Control']='private, no-store'

    router = APIRouter(dependencies=[Depends(no_store)])

    @router.get('/admin/work-reports')
    def page():
        return FileResponse(STATIC / 'admin-work-reports.html')

    @router.get('/admin/work-reports.js')
    def script():
        return FileResponse(STATIC / 'admin-work-reports.js', media_type='text/javascript', headers={'Cache-Control':'no-cache'})

    def employee(profile, kind):
        return dict(id=profile.user_id, name=profile.first_name+' '+profile.last_name,
                    personnel_number=profile.personnel_number, employee_category=kind)

    def owned_report(db, report_id):
        report=db.get(DutyReport, report_id)
        if not report:
            raise HTTPException(404, source('admin_work_reports.text_a48ddd455f9b'))
        return report

    @router.get('/api/v1/admin/work-reports/employees')
    def employees(user=Depends(require_admin), db:Session=Depends(database_session)):
        rows=db.execute(select(TfProfile, EmployeeCategory.category).join(User, User.id==TfProfile.user_id)
                        .outerjoin(EmployeeCategory,EmployeeCategory.user_id==TfProfile.user_id)
                        .where(User.role=='tf').order_by(TfProfile.last_name,TfProfile.first_name,TfProfile.user_id))
        return [employee(profile,kind or 'tf') for profile,kind in rows]

    @router.get('/api/v1/admin/work-reports')
    def listing(year:int=Query(ge=2000,le=2100),month:int=Query(ge=1,le=12),
                employee_id:int|None=Query(default=None,ge=1),employee_category:Literal['tf','wgm']|None=None,
                offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),
                user=Depends(require_admin),db:Session=Depends(database_session)):
        query=select(DutyReport,TfProfile,EmployeeCategory.category).join(TfProfile,TfProfile.user_id==DutyReport.tf_user_id).join(WorkEntry,WorkEntry.id==DutyReport.entry_id).outerjoin(EmployeeCategory,EmployeeCategory.user_id==TfProfile.user_id)
        query=query.where(WorkEntry.entry_date>=date(year,month,1),WorkEntry.entry_date<=date(year,month,calendar.monthrange(year,month)[1]))
        if employee_id is not None:query=query.where(DutyReport.tf_user_id==employee_id)
        if employee_category:query=query.where(func.coalesce(EmployeeCategory.category,'tf')==employee_category)
        total=db.scalar(select(func.count()).select_from(query.subquery()))
        rows=db.execute(query.order_by(WorkEntry.entry_date.desc(),DutyReport.id.desc()).offset(offset).limit(limit))
        items=[]
        for report,profile,kind in rows:
            payload=json.loads(report.payload_json)
            start=datetime.fromisoformat(payload['start_at']);end=datetime.fromisoformat(payload['end_at'])
            items.append(dict(id=report.id,employee=employee(profile,kind or 'tf'),start_at=payload['start_at'],end_at=payload['end_at'],
                              kind=payload.get('kind','Dienstschicht'),duration_minutes=int((end-start).total_seconds()//60),created_at=report.created_at.isoformat()))
        return dict(items=items,total=total,offset=offset,limit=limit)

    @router.get('/api/v1/admin/work-reports/{report_id}')
    def details(report_id:int,user=Depends(require_admin),db:Session=Depends(database_session)):
        report=owned_report(db,report_id)
        return dict(report=report_view(db,report),employee=employee(db.get(TfProfile,report.tf_user_id),category(db,report.tf_user_id)))

    @router.get('/api/v1/admin/work-reports/{report_id}/pdf')
    def pdf(report_id:int,user=Depends(require_admin),db:Session=Depends(database_session)):
        from ..documents.archive import work_report_pdf,report_filename
        report=owned_report(db,report_id)
        content=work_report_pdf(db,db.get(User,report.tf_user_id),report)
        return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{report_filename(report)}"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

    return router
