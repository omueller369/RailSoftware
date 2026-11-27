# Dienstpläne werden nur nach Bestätigung und ausschließlich dem zugeordneten TF gezeigt.
import io,unittest
from datetime import datetime
import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_work_reports,test_accounts
from lokzeitleiste.models import User,DutyRosterEntry,DutyReport

BASE='/api/v1/admin/duty-rosters'
class DutyRostersTest(unittest.TestCase):
    setUp=test_work_reports.WorkReportsTest.setUp
    tearDown=test_work_reports.WorkReportsTest.tearDown
    payload=test_work_reports.WorkReportsTest.payload
    def excel(self):
        if hasattr(self,'_excel_content'):return self._excel_content
        book=openpyxl.Workbook();sheet=book.active;sheet.append(['TF','Start','Ende','Hinweis']);sheet.append(['Testperson 186,187 Vorname',datetime(2026,11,24,23,0),datetime(2026,11,25,8,0),'Übergabe an Kollege']);sheet.append(['TF','Start','Ende','Hinweis']);out=io.BytesIO();book.save(out);self._excel_content=out.getvalue();return self._excel_content
    def preview(self):
        result=self.client.post(BASE+'/preview',files={'file':('plan.xlsx',self.excel())},data={'header':'1','sheet':'0'});self.assertEqual(result.status_code,200,result.text);return result.json()
    def confirm(self,preview,**changes):
        with Session(self.engine) as db:owner=db.scalar(select(User.id).where(User.username=='787100'))
        body=dict(columns={'duty_start':1,'duty_end':2,'comment':3},assignments=[{'row':2,'tf_user_id':owner}]);body.update(changes)
        return self.client.post(BASE+'/'+str(preview['id'])+'/confirm',json=body)
    def test_preview_confirmation_isolation_and_idempotence(self):
        choices=self.client.get(BASE+'/recipients');self.assertEqual(choices.status_code,200,choices.text);self.assertTrue(any(r['number']=='787100' for r in choices.json()))
        preview=self.preview();self.assertEqual(len(preview['rows']),1);self.assertEqual(preview['rows'][0]['values'][1],'2026-11-24T23:00:00')
        self.assertEqual(self.driver.get('/api/v1/tf/duty-rosters').json(),[])
        invalid=self.confirm(preview,columns={'duty_start':99});self.assertEqual(invalid.status_code,422)
        invalid=self.confirm(preview,assignments=[{'row':2,'tf_user_id':999999}]);self.assertEqual(invalid.status_code,422)
        result=self.confirm(preview);self.assertEqual(result.status_code,200,result.text)
        own=self.driver.get('/api/v1/tf/duty-rosters');self.assertEqual(own.status_code,200,own.text);self.assertEqual(len(own.json()),1);self.assertEqual(own.json()[0]['values']['comment'],'Übergabe an Kollege');self.assertNotIn('Testperson',own.text)
        self.assertTrue(self.confirm(preview).json()['already_imported'])
        repeated=self.preview();self.assertTrue(self.confirm(repeated).json()['already_imported'])
        with Session(self.engine) as db:self.assertEqual(len(list(db.scalars(select(DutyRosterEntry)))),1);self.assertEqual(len(list(db.scalars(select(DutyReport)))),0)
        with Session(self.engine) as db:
            row=db.scalar(select(DutyRosterEntry));other=User(username='787555',password_hash='unused',role='tf',active=True);db.add(other);db.flush();row.tf_user_id=other.id;db.commit()
        self.assertEqual(self.driver.get('/api/v1/tf/duty-rosters').json(),[])
    def test_access_and_format_limits(self):
        self.assertEqual(self.driver.post(BASE+'/preview',files={'file':('plan.xlsx',self.excel())}).status_code,401)
        result=self.client.post(BASE+'/preview',files={'file':('plan.exe',b'unsafe')});self.assertEqual(result.status_code,422)
        self.assertEqual(self.client.get('/tf/dienstplan').status_code,200)
        self.assertEqual(self.driver.get('/api/v1/tf/duty-rosters',params={'start':'wrong'}).status_code,422)

    def test_pause_rows_skipped_in_preview_and_mapping_confirmation(self):
        book=openpyxl.Workbook();sheet=book.active;sheet.append(['Z-Art/P','Dienstbeginn','Dienstende']);sheet.append([' Pause ','ohne Datum','ohne Datum']);sheet.append(['Leerzug',datetime(2026,11,25,8),datetime(2026,11,25,12)])
        out=io.BytesIO();book.save(out)
        result=self.client.post(BASE+'/preview',files={'file':('plan.xlsx',out.getvalue())});self.assertEqual(result.status_code,200,result.text);preview=result.json();self.assertEqual(preview['skipped_pauses'],1);self.assertEqual([r['row'] for r in preview['rows']],[3])
        result=self.confirm(preview,columns={'activity':0,'duty_start':1,'duty_end':2},assignments=[{'row':3,'tf_user_id':self.tf}]);self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['count'],1)
        # Auch eine abweichend benannte Spalte wird nach ausdrücklicher Zuordnung geprüft.
        sheet.cell(1,1,'Tätigkeit');out=io.BytesIO();book.save(out)
        result=self.client.post(BASE+'/preview',files={'file':('custom.xlsx',out.getvalue())});preview=result.json();self.assertEqual(len(preview['rows']),2)
        result=self.confirm(preview,columns={'activity':0,'duty_start':1,'duty_end':2},assignments=[{'row':2,'tf_user_id':self.tf},{'row':3,'tf_user_id':self.tf}]);self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['count'],1);self.assertEqual(result.json()['skipped_pauses'],1)
        self.assertTrue(all(r['values']['activity']=='Leerzug' for r in self.driver.get('/api/v1/tf/duty-rosters').json()))

    def test_update_removes_only_published_roster_pauses_and_repeat_does_not_duplicate(self):
        import json,hashlib
        from lokzeitleiste.models import DutyRosterImport
        from lokzeitleiste.duty_rosters import remove_pause_entries
        book=openpyxl.Workbook();sheet=book.active;sheet.append(['Z-Art/P','Dienstbeginn','Dienstende']);sheet.append(['Pause',datetime(2026,11,25,8),datetime(2026,11,25,9)]);sheet.append(['Vollzug',datetime(2026,11,25,9),datetime(2026,11,25,12)])
        out=io.BytesIO();book.save(out);content=out.getvalue();mapping={'activity':0,'duty_start':1,'duty_end':2};assignments={2:self.tf,3:self.tf}
        # Bestand vor der Bereinigung: Pause und Leistung wurden zusammen bestätigt.
        preview=dict(sheet=0,header=1,columns=['Z-Art/P','Dienstbeginn','Dienstende'],rows=[dict(row=2,values=['Pause','2026-11-25T08:00:00','2026-11-25T09:00:00']),dict(row=3,values=['Vollzug','2026-11-25T09:00:00','2026-11-25T12:00:00'])])
        checksum=hashlib.sha256(content).hexdigest();fingerprint=hashlib.sha256(json.dumps([checksum,0,1,sorted(mapping.items()),sorted(assignments.items())],sort_keys=True).encode()).hexdigest()
        report=self.driver.post('/api/v1/tf/work-reports',json=self.payload());self.assertEqual(report.status_code,201,report.text)
        with Session(self.engine) as db:
            from lokzeitleiste.models import User
            uploader=db.scalar(select(User.id).where(User.role=='admin'))
            batch=DutyRosterImport(uploader_id=uploader,filename='old.xlsx',source_sha256=checksum,confirmation_sha256=fingerprint,preview_json=json.dumps(preview));db.add(batch);db.flush()
            for row in preview['rows']:db.add(DutyRosterEntry(import_id=batch.id,source_row=row['row'],tf_user_id=self.tf,date='2026-11-25',payload_json=json.dumps({k:row['values'][i] for k,i in mapping.items()})))
            db.add(DutyRosterEntry(import_id=batch.id,source_row=4,tf_user_id=self.tf,date='2026-11-25',payload_json=json.dumps({'activity':' PAUSE\n'})))
            db.add(DutyRosterEntry(import_id=batch.id,source_row=5,tf_user_id=self.tf,date='2026-11-25',payload_json=json.dumps({'activity':'Pausenbereitschaft'})));db.commit()
            original=db.get(DutyReport,report.json()['id']).payload_json
            self.assertEqual(remove_pause_entries(db),2);db.commit();self.assertEqual(remove_pause_entries(db),0);self.assertEqual(db.get(DutyReport,report.json()['id']).payload_json,original)
            self.assertEqual({json.loads(r.payload_json)['activity'] for r in db.scalars(select(DutyRosterEntry))},{'Vollzug','Pausenbereitschaft'})
        result=self.client.post(BASE+'/preview',files={'file':('same.xlsx',content)});new=result.json();self.assertEqual(new['skipped_pauses'],1)
        result=self.confirm(new,columns=mapping,assignments=[{'row':3,'tf_user_id':self.tf}]);self.assertEqual(result.status_code,200,result.text);self.assertFalse(result.json()['already_imported'])
        with Session(self.engine) as db:self.assertEqual(len(list(db.scalars(select(DutyRosterEntry)))),1)

    def version_file(self,comment,day=24,rows=1):
        book=openpyxl.Workbook();sheet=book.active;sheet.append(['TF','Start','Ende','Hinweis'])
        for i in range(rows):sheet.append(['Fiktiver Tf',datetime(2026,11,day,8+i),datetime(2026,11,day,9+i),comment])
        out=io.BytesIO();book.save(out);return out.getvalue()
    def upload_version(self,content):
        result=self.client.post(BASE+'/preview',files={'file':('version.xlsx',content)});self.assertEqual(result.status_code,200,result.text);return result.json()
    def current(self):return self.driver.get('/api/v1/tf/duty-rosters').json()
    def test_last_file_replaces_every_tf_and_period_only_after_confirmation(self):
        from fastapi.testclient import TestClient
        from lokzeitleiste.main import app
        other=self.create_tf('787666','ROSTER-OTHER').json()['id'];client=TestClient(app,base_url='https://testserver');self.staff_clients.append(client);client.post('/api/v1/account/login',json={'username':'787666','password':'tf-secret-12345'})
        first=self.upload_version(self.version_file('Alt',24,2));self.assertEqual(self.confirm(first,assignments=[{'row':2,'tf_user_id':self.tf},{'row':3,'tf_user_id':other}]).status_code,200)
        report=self.driver.post('/api/v1/tf/work-reports',json=self.payload());self.assertEqual(report.status_code,201,report.text)
        new=self.upload_version(self.version_file('Neu',28));self.assertEqual(self.current()[0]['values']['comment'],'Alt')
        bad=self.confirm(new,columns={'duty_start':99});self.assertEqual(bad.status_code,422);self.assertEqual(self.current()[0]['values']['comment'],'Alt')
        result=self.confirm(new);self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['replaced'],2)
        self.assertEqual(self.current()[0]['values']['comment'],'Neu');self.assertEqual(client.get('/api/v1/tf/duty-rosters').json(),[])
        with Session(self.engine) as db:
            self.assertEqual(len(list(db.scalars(select(DutyRosterEntry)))),1);self.assertIsNotNone(db.get(DutyReport,report.json()['id']))
    def test_old_retry_never_reactivates_but_fresh_import_of_same_file_can(self):
        first_content=self.version_file('Version A');a=self.upload_version(first_content);self.confirm(a)
        b=self.upload_version(self.version_file('Version B'));self.confirm(b)
        retry=self.confirm(a);self.assertEqual(retry.status_code,200,retry.text);self.assertTrue(retry.json()['superseded']);self.assertEqual(self.current()[0]['values']['comment'],'Version B')
        again=self.upload_version(first_content);result=self.confirm(again);self.assertEqual(result.status_code,200,result.text);self.assertFalse(result.json()['superseded']);self.assertEqual(self.current()[0]['import_id'],again['id'])
        self.assertEqual(self.current()[0]['values']['comment'],'Version A');self.assertFalse(self.confirm(again).json()['superseded'])
        repeat=self.upload_version(first_content);self.assertTrue(self.confirm(repeat).json()['already_imported']);self.assertEqual(len(self.current()),1)
    def test_confirmation_order_is_authoritative_and_migration_does_not_reset_it(self):
        from lokzeitleiste.duty_rosters import migrate_publication
        first=self.upload_version(self.version_file('Früher hochgeladen'));second=self.upload_version(self.version_file('Später hochgeladen'))
        self.confirm(second);self.confirm(first)
        self.assertEqual(self.current()[0]['import_id'],first['id'])
        with Session(self.engine) as db:migrate_publication(db);db.commit()
        self.assertEqual(self.current()[0]['import_id'],first['id']);self.assertTrue(self.confirm(second).json()['superseded'])
    def test_legacy_update_keeps_only_newest_confirmed_upload(self):
        import json
        from lokzeitleiste.models import DutyRosterImport
        from lokzeitleiste.duty_rosters import migrate_publication
        with Session(self.engine) as db:
            uploader=db.scalar(select(User.id).where(User.role=='admin'))
            for i in range(2):
                batch=DutyRosterImport(uploader_id=uploader,filename='legacy.xlsx',source_sha256=str(i)*64,confirmation_sha256=str(i)*64,preview_json='{}');db.add(batch);db.flush();db.add(DutyRosterEntry(import_id=batch.id,source_row=2,tf_user_id=self.tf,date='2026-11-24',payload_json=json.dumps({'comment':str(i)})))
            db.commit();migrate_publication(db);db.commit();migrate_publication(db);db.commit()
            self.assertEqual(len(list(db.scalars(select(DutyRosterEntry)))),1);self.assertEqual(len(list(db.scalars(select(DutyRosterImport)))),2)
        self.assertEqual(self.current()[0]['values']['comment'],'1')

    def test_database_failure_during_replacement_rolls_back_old_roster(self):
        from sqlalchemy.exc import IntegrityError
        from lokzeitleiste.models import DutyRosterImport,DutyRosterPublication
        first=self.upload_version(self.version_file('Gültig'));self.confirm(first)
        newer=self.upload_version(self.version_file('FAIL_ROSTER'))
        with self.engine.begin() as connection:connection.exec_driver_sql("CREATE TRIGGER reject_roster BEFORE INSERT ON duty_roster_entries WHEN NEW.payload_json LIKE '%FAIL_ROSTER%' BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        with self.assertRaises(IntegrityError):self.confirm(newer)
        self.assertEqual(self.current()[0]['values']['comment'],'Gültig')
        with Session(self.engine) as db:
            self.assertEqual(db.get(DutyRosterPublication,1).import_id,first['id']);self.assertIsNone(db.get(DutyRosterImport,newer['id']).confirmation_sha256)
