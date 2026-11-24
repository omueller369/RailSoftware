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
    def excel(self):
        book=openpyxl.Workbook();sheet=book.active;sheet.append(['TF','Start','Ende','Hinweis']);sheet.append(['Testperson 186,187 Vorname',datetime(2026,11,24,23,0),datetime(2026,11,25,8,0),'Übergabe an Kollege']);sheet.append(['TF','Start','Ende','Hinweis']);out=io.BytesIO();book.save(out);return out.getvalue()
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
