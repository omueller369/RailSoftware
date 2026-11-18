"""Explicit owner-bound corrections; one accounting entry and immutable prior PDFs."""
import json,hashlib
from datetime import datetime,timedelta,time
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select,delete
from sqlalchemy.orm import defer
from ..localization import source
from ..models import DutyReportCorrection as Correction,DutyReportDraft,User,DutyReport,WorkEntry,WorkMonth,WorkEntryAudit,DutyGuestTrip,now_utc
from ..records.service import assert_unlocked
from ..reports.intervals import interval,set_end_date,period_entries,touched_months
from .schemas import DraftReportIn,minutes,train_pause_minutes

def text(key):return source('report_rework.text_'+hashlib.sha256(key.encode()).hexdigest()[:12])
def active(db,report_id):return db.scalar(select(Correction).options(defer(Correction.pdf_content),defer(Correction.payload_json),defer(Correction.submitted_json)).where(Correction.report_id==report_id,Correction.completed_at.is_(None)))
def info(row):return dict(report_id=row.report_id,client_id=row.client_id,version=row.version,reason=row.reason)
def for_draft(db,owner_id,client_id):return db.scalar(select(Correction).options(defer(Correction.pdf_content),defer(Correction.payload_json),defer(Correction.submitted_json)).where(Correction.owner_id==owner_id,Correction.client_id==str(client_id)))
def aligned(db,report,payload):
    entry=db.scalar(select(WorkEntry).where(WorkEntry.id==report.entry_id).with_for_update().execution_options(populate_existing=True))
    start,end=datetime.fromisoformat(payload['start_at']),datetime.fromisoformat(payload['end_at'])
    guest=sum(max(0,minutes(max(start,datetime.fromisoformat(trip['start_at'])),min(end,datetime.fromisoformat(trip['end_at'])))) for trip in payload.get('trips',[]))
    if entry.guest_minutes!=guest or interval(entry)!=(start,end) or entry.kind!=payload.get('kind','Dienstschicht') or entry.pause_minutes!=payload['actual_pause']+train_pause_minutes(payload.get('train_journeys',[])) or entry.note!=payload.get('overrun_reason',''):
        raise HTTPException(409,text('conflict'))
    return entry

def snapshot_pdf(db,user,report):
    from ..documents.archive import report_filename,work_report_pdf
    from ..models import ReportDispatch,DocumentFile
    from ..documents.storage import safe_path
    filename=report_filename(report)
    original=db.scalar(select(ReportDispatch.pdf_data).where(ReportDispatch.tf_user_id==user.id,ReportDispatch.filename==filename,ReportDispatch.pdf_data.is_not(None)).order_by(ReportDispatch.id.desc()).limit(1))
    if original:return original
    document=db.scalar(select(DocumentFile).where(DocumentFile.owner_id==user.id,DocumentFile.source_key==f'work-report:{report.id}'))
    if document and document.display_name==filename:
        try:return safe_path(user,document.relative_path).read_bytes()
        except HTTPException as exc:
            if exc.status_code!=404:raise
    return work_report_pdf(db,user,report)


def return_report(db,report_id,actor,reason,expected_version):
    from ..accounts.employee_categories import category
    from ..documents.archive import report_version,work_report_pdf
    original=db.get(DutyReport,report_id)
    if not original:raise HTTPException(404)
    user=db.scalar(select(User).where(User.id==original.tf_user_id).with_for_update())
    report=db.scalar(select(DutyReport).where(DutyReport.id==report_id).with_for_update().execution_options(populate_existing=True))
    assert_unlocked(db,report.entry_id);payload=json.loads(report.payload_json)
    if user.role!='tf' or category(db,user.id)!='tf' or report_version(payload)!=expected_version:raise HTTPException(409,text('conflict'))
    previous=active(db,report.id)
    if previous:
        if previous.reason!=reason:raise HTTPException(409,text('conflict'))
        return previous
    aligned(db,report,payload)
    client_id=str(uuid4());draft_payload=DraftReportIn.model_validate(dict(payload,client_id=client_id)).model_dump_json()
    row=Correction(report_id=report.id,owner_id=user.id,client_id=client_id,version=report_version(payload),reason=reason,returned_by=actor.id,payload_json=report.payload_json,pdf_content=snapshot_pdf(db,user,report))
    db.add(row);db.add(DutyReportDraft(owner_id=user.id,client_id=client_id,payload_json=draft_payload,receipt_keys_json='[]',revision=1))
    db.add(WorkEntryAudit(entry_id=report.entry_id,actor_id=actor.id,action='work_report_returned'))
    db.commit();return row

def resubmit(db,user,data,row):
    from .service import resolve_train_stations
    from ..app_defaults import use_journeys
    from ..worktime.service import validate_no_overlap
    from ..documents.archive import archive_report,archive_month
    from ..models import RailwayStation
    report=db.scalar(select(DutyReport).where(DutyReport.id==row.report_id,DutyReport.tf_user_id==user.id).with_for_update())
    incoming=data.model_dump_json()
    if len(incoming.encode('utf-8'))>60000:raise HTTPException(422,source('server_work_reports_service.text_a14edc14d076'))
    if row.completed_at:
        if row.submitted_json!=incoming or active(db,report.id) or json.loads(report.payload_json)['client_id']!=str(data.client_id):raise HTTPException(409,text('conflict'))
        return report
    assert_unlocked(db,report.entry_id)
    if report.payload_json!=row.payload_json:raise HTTPException(409,text('conflict'))
    previous=json.loads(row.payload_json);entry=aligned(db,report,previous);old_periods=touched_months(entry.entry_date,interval(entry)[1].date())
    for trip in data.trips:
        for code,field in [(trip.start_station,'start_station_name'),(trip.end_station,'end_station_name')]:
            station=db.get(RailwayStation,code)
            if not station:raise HTTPException(422,source('server_work_reports_service.text_b2e103a3cabe')+code)
            setattr(trip,field,station.name)
    use_journeys(db,data.train_journeys,previous.get('train_journeys',[]));resolve_train_stations(db,data.train_journeys)
    payload=json.loads(data.model_dump_json());payload['_train_revision']=previous.get('_train_revision',0)+1;payload['_pdf_version_offset']=previous.get('_pdf_version_offset',0)
    encoded=json.dumps(payload,ensure_ascii=False)
    if len(encoded.encode('utf-8'))>60000:raise HTTPException(422,text('conflict'))
    # Absence entries occupy the entire day, just as on first submission.
    first=data.start_at.date();last=(data.end_at-timedelta(minutes=1)).date()
    from ..reports.daily import WORK_KINDS
    absences={source('server_work_reports_service.text_35d3a889824d'),source('server_work_reports_service.text_be1600b499c6')}
    for other in period_entries(db,user.id,first,last,lock=True):
        if other.id==entry.id:continue
        a,b=interval(other)
        if (other.kind in absences or data.kind in absences) and other.kind in WORK_KINDS|absences:
            if a<datetime.combine(last+timedelta(days=1),time.min) and b>datetime.combine(first,time.min):raise HTTPException(409,text('conflict'))
    period=db.scalar(select(WorkMonth).where(WorkMonth.tf_user_id==user.id,WorkMonth.year==data.start_at.year,WorkMonth.month==data.start_at.month))
    if not period:period=WorkMonth(tf_user_id=user.id,year=data.start_at.year,month=data.start_at.month);db.add(period);db.flush()
    entry.work_month_id=period.id;entry.kind=data.kind;entry.entry_date=data.start_at.date();entry.start_time=data.start_at.strftime('%H:%M');entry.end_time=data.end_at.strftime('%H:%M');set_end_date(entry,data.end_at.date());entry.pause_minutes=data.actual_pause+train_pause_minutes(payload['train_journeys']);entry.guest_minutes=sum(max(0,minutes(max(t.start_at,data.start_at),min(t.end_at,data.end_at))) for t in data.trips);entry.note=data.overrun_reason;entry.updated_at=now_utc()
    try:validate_no_overlap(db,user.id,entry)
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
    report.payload_json=encoded
    db.execute(delete(DutyGuestTrip).where(DutyGuestTrip.report_id==report.id))
    for trip in data.trips:db.add(DutyGuestTrip(report_id=report.id,**trip.model_dump(exclude={'start_station_name','end_station_name','self_payer'})))
    row.completed_at=now_utc();row.submitted_json=incoming
    db.add(WorkEntryAudit(entry_id=entry.id,actor_id=user.id,action='work_report_corrected'))
    archive_report(db,user,report,queue_email=True)
    for year,month in set(old_periods)-set(touched_months(entry.entry_date,interval(entry)[1].date())):archive_month(db,user,year,month)
    db.flush();return report
