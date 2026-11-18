import json,unittest
from uuid import uuid4
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from lokzeitleiste.models import DutyReportCorrection,DutyReportDraft,DutyReport,WorkEntry,WorkEntryLock,ReportDispatch
from lokzeitleiste.work_reports.schemas import ReportIn,DraftReportIn
import test_work_reports,test_accounts
class CorrectionTest(unittest.TestCase):
    setUp=test_work_reports.WorkReportsTest.setUp
    tearDown=test_work_reports.WorkReportsTest.tearDown
    payload=test_work_reports.WorkReportsTest.payload
    create=test_work_reports.WorkReportsTest.create
    def create_staff(self,grants=None,username='office-one'):
        response=self.client.post('/api/v1/admin/staff',json=test_accounts.AccountsTest.payload(self,username,grants))
        self.assertEqual(response.status_code,201,response.text);return response.json()['id']
    staff_login=test_accounts.AccountsTest.staff_login
    change=test_accounts.AccountsTest.change
    active_staff=test_accounts.AccountsTest.active_staff
    def test_return_edit_resubmit_one_entry_retained_pdf_and_retry(self):
        original=self.payload();original['train_journeys']=[dict(id=str(uuid4()),train_number='123',start_station='BHF',end_station='LL',start_at='2026-10-12T10:00',end_at='2026-10-12T16:00',events=[])];report=self.create(original);rid=report['id'];base=f'/api/v1/admin/work-reports/{rid}'
        r=self.client.post(base+'/return',json={'reason':'Bitte Dienstende prüfen','expected_version':report['version']});self.assertEqual(r.status_code,200,r.text);returned=r.json()
        self.assertEqual(self.client.post(base+'/return',json={'reason':'Bitte Dienstende prüfen','expected_version':report['version']}).json()['client_id'],returned['client_id'])
        listed=self.driver.get('/api/v1/tf/work-report-drafts').json()['drafts'];self.assertEqual(len(listed),1);draft=listed[0];self.assertEqual(draft['returned']['report_id'],rid)
        self.assertEqual(self.driver.delete('/api/v1/tf/work-report-drafts/'+draft['client_id']).status_code,409)
        self.assertEqual(self.driver.get('/api/v1/tf/work-reports/month/2026/10').json()['reports'][0]['returned']['client_id'],draft['client_id'])
        snapshot=self.client.get(base+'/versions/1/pdf').content;self.assertTrue(snapshot.startswith(b'%PDF'))
        with Session(self.engine) as db:self.assertEqual(snapshot,db.scalar(select(ReportDispatch.pdf_data).where(ReportDispatch.tf_user_id==self.tf).order_by(ReportDispatch.id)).__bytes__())
        corrected={**draft['report'],'end_at':'2026-10-12T18:00:00','overrun_reason':'Korrigiert'}
        save=self.driver.put('/api/v1/tf/work-report-drafts/'+draft['client_id'],json={'expected_revision':draft['revision'],'report':corrected,'receipt_keys':[]});self.assertEqual(save.status_code,200,save.text)
        submit=self.driver.post('/api/v1/tf/work-reports',headers={'X-CTL-Draft-Revision':str(save.json()['revision'])},json=corrected);self.assertEqual(submit.status_code,201,submit.text)
        new=submit.json();followup=self.driver.put(f'/api/v1/tf/work-reports/{rid}/train-journeys',json={'expected_revision':new['train_revision'],'train_journeys':corrected['train_journeys']});self.assertEqual(followup.status_code,200,followup.text);self.assertEqual(followup.json()['version'],new['version']);self.assertEqual(new['id'],rid);self.assertEqual(new['version'],report['version']+1);self.assertIsNone(new['returned']);self.assertEqual(new['end_at'],'2026-10-12T18:00:00')
        again=self.driver.post('/api/v1/tf/work-reports',json=corrected);self.assertEqual(again.status_code,201,again.text);self.assertEqual(again.json()['version'],new['version'])
        self.assertEqual(self.client.get(base+'/versions/1/pdf').content,snapshot)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(WorkEntry)),1);self.assertEqual(db.scalar(select(func.count()).select_from(DutyReport)),1)
            history=db.scalar(select(DutyReportCorrection));self.assertEqual(json.loads(history.payload_json)['end_at'],original['end_at']+':00');self.assertIsNotNone(history.completed_at)
        second=self.client.post(base+'/return',json={'reason':'Weitere Prüfung','expected_version':new['version']});self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(self.driver.post('/api/v1/tf/work-reports',json=corrected).status_code,409,'Old correction cannot overwrite a later return')
    def test_permissions_locks_and_stale_version(self):
        report=self.create();base=f"/api/v1/admin/work-reports/{report['id']}";data={'reason':'Prüfung','expected_version':report['version']}
        _,reader=self.active_staff({'work_reports':1},'report-reader');_,writer=self.active_staff({'work_reports':2},'report-writer')
        self.assertEqual(reader.post(base+'/return',json=data).status_code,403)
        self.assertEqual(writer.post(base+'/return',json={**data,'expected_version':99}).status_code,409)
        with Session(self.engine) as db:db.add(WorkEntryLock(entry_id=report['entry_id'],locked=True,actor_id=1,reason='Prüfung'));db.commit()
        self.assertEqual(writer.post(base+'/return',json=data).status_code,409)
        with Session(self.engine) as db:db.get(WorkEntryLock,report['entry_id']).locked=False;db.commit()
        self.assertEqual(writer.post(base+'/return',json=data).status_code,200)
        self.assertEqual(self.driver.put(f"/api/v1/tf/work-reports/{report['id']}/train-journeys",json={'expected_revision':0,'train_journeys':[]}).status_code,409)
    def test_draft_times_outside_duty_allowed_but_final_report_rejects(self):
        data=self.payload();data['train_journeys']=[dict(id=str(uuid4()),train_number='123',start_station='BHF',end_station='LL',start_at='2026-10-12T08:00',end_at='2026-10-12T16:00',events=[])]
        self.assertTrue(DraftReportIn.model_validate(data))
        with self.assertRaises(ValueError):ReportIn.model_validate({**data,'check_duty_bounds':False})
        r=self.driver.put('/api/v1/tf/work-report-drafts/'+data['client_id'],json={'expected_revision':0,'report':data,'receipt_keys':[]});self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.driver.post('/api/v1/tf/work-reports',json=data).status_code,422)
