import json
import unittest
from uuid import uuid4
from sqlalchemy.orm import Session
from lokzeitleiste.models import EmployeeCategory, DutyReportDraft
from lokzeitleiste.accounts.employee_categories import category
import test_accounts
import test_work_reports


class AdminWorkReportsTest(unittest.TestCase):
    setUp=test_work_reports.WorkReportsTest.setUp
    tearDown=test_accounts.AccountsTest.tearDown
    payload=test_work_reports.WorkReportsTest.payload
    create=test_work_reports.WorkReportsTest.create
    def create_staff(self,grants=None,username='office-one'):
        response=self.client.post('/api/v1/admin/staff',json=test_accounts.AccountsTest.payload(self,username,grants))
        self.assertEqual(response.status_code,201,response.text)
        return response.json()['id']
    staff_login=test_accounts.AccountsTest.staff_login
    change=test_accounts.AccountsTest.change
    active_staff=test_accounts.AccountsTest.active_staff

    def test_inbox_receives_only_finalized_reports_filter_and_pagination(self):
        with Session(self.engine) as db:
            db.add(DutyReportDraft(owner_id=self.tf,client_id=str(uuid4()),payload_json=json.dumps(self.payload())))
            db.commit()
        path='/api/v1/admin/work-reports?year=2026&month=10'
        self.assertEqual(self.client.get(path).json()['total'],0)
        report=self.create()
        self.create(self.payload('2026-10-13T09:00','2026-10-13T17:00'))
        data=self.client.get(path+'&limit=1').json()
        self.assertEqual(data['total'],2)
        self.assertEqual(len(data['items']),1)
        self.assertEqual(self.client.get(path+'&limit=1&offset=1').json()['items'][0]['id'],report['id'])
        self.assertEqual(self.client.get(path+'&employee_id=999999').json()['total'],0)
        self.assertEqual(self.client.get(path+'&employee_category=wgm').json()['total'],0)
        self.assertEqual(self.client.get('/api/v1/admin/work-reports?year=2026&month=11').json()['total'],0)
        self.assertEqual(self.client.get('/api/v1/admin/work-reports?year=2026&month=13').status_code,422)
        self.assertEqual(self.client.get(path+'&employee_category=admin').status_code,422)

    def test_category_persists_and_legacy_updates_do_not_reset_it(self):
        people=self.client.get('/api/v1/admin/tf').json();profile=next(p for p in people if p['id']==self.tf)
        self.assertEqual(profile['employee_category'],'tf')
        data={key:profile[key] for key in ['first_name','last_name','personnel_number','vacation_days','birth_date','bahncard','email','federal_state']}
        self.assertEqual(self.client.put(f'/api/v1/admin/tf/{self.tf}',json=dict(data,employee_category='wgm')).status_code,200)
        self.assertEqual(self.client.put(f'/api/v1/admin/tf/{self.tf}',json=data).status_code,200)
        with Session(self.engine) as db:self.assertEqual(category(db,self.tf),'wgm')
        self.assertEqual(self.client.put(f'/api/v1/admin/tf/{self.tf}',json=dict(data,employee_category='admin')).status_code,422)
        report=self.create()
        row=self.client.get('/api/v1/admin/work-reports?year=2026&month=10&employee_category=wgm').json()['items'][0]
        self.assertEqual(row['employee']['employee_category'],'wgm')
        self.assertEqual(row['id'],report['id'])
        self.assertEqual(self.client.get('/api/v1/admin/work-reports/employees').json()[0]['employee_category'],'wgm')

    def test_create_wgm_uses_shared_staff_foundation_without_admin_rights(self):
        profile=self.client.get('/api/v1/admin/tf').json()[0]
        data=dict(profile,username='787101',personnel_number='P-WGM',email='wgm@example.com',password='wagon-secret-12345',employee_category='wgm')
        response=self.client.post('/api/v1/admin/tf',json=data)
        self.assertEqual(response.status_code,201,response.text)
        with Session(self.engine) as db:
            from lokzeitleiste.models import User
            user_id=response.json()['id']
            self.assertEqual(category(db,user_id),'wgm')
            self.assertEqual(db.get(User,user_id).role,'tf')
        people=self.client.get('/api/v1/admin/tf').json()
        self.assertEqual(next(p for p in people if p['id']==user_id)['employee_category'],'wgm')

    def test_independent_permissions_protect_list_details_pdf_and_picker(self):
        report=self.create();base='/api/v1/admin/work-reports'
        _,denied=self.active_staff({'employees':1,'reports':3},username='no-inbox')
        for path in [base+'?year=2026&month=10',base+'/employees',base+'/'+str(report['id']),base+'/'+str(report['id'])+'/pdf']:
            self.assertEqual(denied.get(path).status_code,403,path)
            self.assertEqual(self.driver.get(path).status_code,401,path)
        self.assertNotIn('work_reports',{m['id'] for m in denied.get('/api/v1/admin/start').json()['modules']})
        _,reader=self.active_staff({'work_reports':1},username='inbox-reader')
        modules=reader.get('/api/v1/admin/start').json()['modules']
        self.assertIn('work_reports',{m['id'] for m in modules})
        people=reader.get(base+'/employees').json();self.assertNotIn('email',people[0]);self.assertNotIn('birth_date',people[0])
        response=reader.get(base+'/'+str(report['id']));self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertEqual(response.json()['report']['start_at'],report['start_at'])
        pdf=reader.get(base+'/'+str(report['id'])+'/pdf');self.assertEqual(pdf.status_code,200);self.assertEqual(pdf.headers['content-type'],'application/pdf');self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(reader.get(base+'/999999').status_code,404)
        self.assertEqual(reader.put(base+'/'+str(report['id']),json={}).status_code,405)


if __name__=='__main__':unittest.main()
