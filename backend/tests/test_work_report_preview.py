# Gemeinsamer PDF-Satz für Entwurf und Endfassung, ohne Berichtsspeicherung.
import unittest,json,base64,io
from uuid import uuid4
from types import SimpleNamespace
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from pypdf import PdfReader
import test_work_reports,test_accounts
from lokzeitleiste.models import DutyReport,DutyReportDraft,DocumentFile,User,WorkEntry
from lokzeitleiste.documents.archive import work_report_layout,work_report_pdf
from lokzeitleiste.work_reports.preview import normalize

class WorkReportPreviewTest(unittest.TestCase):
    setUp=test_work_reports.WorkReportsTest.setUp;tearDown=test_work_reports.WorkReportsTest.tearDown;payload=test_work_reports.WorkReportsTest.payload;create=test_work_reports.WorkReportsTest.create
    create_staff=test_accounts.AccountsTest.create_staff;staff_login=test_accounts.AccountsTest.staff_login;change=test_accounts.AccountsTest.change;active_staff=test_accounts.AccountsTest.active_staff
    def preview(self,data,**extra):return self.driver.post('/api/v1/tf/work-reports/preview',json={'report':data,**extra})
    def test_same_tables_and_a4_pages_as_final(self):
        data=self.payload();data['train_journeys']=[dict(id=str(uuid4()),train_number='12345',rotation_name='Umlauf A',start_station='BHF',end_station='LL',start_at=data['start_at'],end_at=data['end_at'],events=[])]
        saved=self.create(data)
        with Session(self.engine) as db:
            user=db.get(User,self.tf);report=db.get(DutyReport,saved['id']);raw=json.loads(report.payload_json)
            final=work_report_layout(db,user,report);pdf=work_report_pdf(db,user,report)
        response=self.preview(raw,owner={'first_name':'Fremder Name'});self.assertEqual(response.status_code,200,response.text)
        result=response.json();preview=result['layout']
        self.assertEqual(preview['sections'],json.loads(json.dumps(final['sections'])))
        self.assertEqual(preview['train_pages'],json.loads(json.dumps(final['train_pages'])))
        for i,(label,value) in enumerate(final['lines']):
            if i!=1:self.assertEqual(preview['lines'][i],[label,value])
        reader=PdfReader(io.BytesIO(base64.b64decode(result['pdf'])));official=PdfReader(io.BytesIO(pdf))
        self.assertEqual(len(reader.pages),len(official.pages));self.assertEqual(len(reader.pages),2)
        for page in reader.pages:self.assertAlmostEqual(float(page.mediabox.width),595.2756,places=2);self.assertAlmostEqual(float(page.mediabox.height),841.8898,places=2)
        text='\n'.join(p.extract_text() for p in reader.pages);self.assertIn('ENTWURF',text);self.assertNotIn('Fremder Name',text);self.assertIn('Umlauf A',text)
        self.assertIn('no-store',response.headers['cache-control'])
    def test_incomplete_conflicting_and_pending_values_are_not_saved(self):
        data=self.payload();data['start_at']='';data['end_at']='2026-10-12T08:00';data['trips'][0]['start_at']='';data['trips'][0]['transport']='Unbekannt';data['train_journeys']=[{'id':'x','train_number':'','start_at':'2026-10-12T10:00','end_at':'2026-10-12T09:00','events':[{'cause':'Altwert','reason':'Freitext','start_at':'','end_at':''}]}]
        response=self.preview(data,guest={'start_station':'Unfertige Gastfahrt'},editors=[{'id':'x','pending':True,'eventFields':{'reason':'Unfertiger Halt'}}])
        self.assertEqual(response.status_code,200,response.text);result=response.json();text='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(base64.b64decode(result['pdf']))).pages)
        for value in ['ENTWURF','Altwert','Freitext','Unfertige Gastfahrt','Unfertiger Halt']:self.assertIn(value,text)
        with Session(self.engine) as db:
            for cls in [DutyReport,DutyReportDraft,WorkEntry,DocumentFile]:self.assertEqual(db.scalar(select(func.count()).select_from(cls)),0)
        self.assertEqual(self.driver.post('/api/v1/tf/work-reports',json=data).status_code,422,'Final validation is unchanged')
    def test_bounds_and_invalid_shape(self):
        self.assertEqual(self.preview({'train_journeys':[{}]*51}).status_code,413)
        self.assertEqual(self.driver.post('/api/v1/tf/work-reports/preview',content=b'X'*180001).status_code,413)
        self.assertEqual(self.driver.post('/api/v1/tf/work-reports/preview',json={'report':None}).status_code,422)
