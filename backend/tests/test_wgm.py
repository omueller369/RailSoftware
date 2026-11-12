import unittest
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select
import test_accounts
from lokzeitleiste.models import User,TfProfile,TfEmployment,EmployeeCategory,WgmProfile,WgmAddress,AccountPolicy,ProfilePhoto
from lokzeitleiste.wgm import migrate_existing_wgm
from lokzeitleiste.user_directories import user_path


class WgmTest(unittest.TestCase):
    setUp=test_accounts.AccountsTest.setUp
    tearDown=test_accounts.AccountsTest.tearDown
    active_staff=test_accounts.AccountsTest.active_staff
    create_staff=test_accounts.AccountsTest.create_staff
    staff_login=test_accounts.AccountsTest.staff_login
    change=test_accounts.AccountsTest.change

    def payload(self,username='office-one',grants=None):
        return test_accounts.AccountsTest.payload(self,username,grants)

    def wgm(self,**changes):
        data=dict(username='wgm.mueller',password='wgm-secret-12345',first_name='Anna',last_name='Wagen',personnel_number='W-001',birth_date='1990-05-12',vacation_days=30,email='anna.wagen@example.com',gender='female',nationality='DE',weekly_minutes=2400,entry_date='2020-01-01',exit_date=None,immediate_block=False,addresses=[dict(street='Hauptstraße',house_number='1a',postal_code='01234',city='Berlin',federal_state='BE',is_postal=True)])
        data.update(changes);return data

    def create(self,client=None,**changes):
        response=(client or self.client).post('/api/v1/admin/wgm',json=self.wgm(**changes));self.assertEqual(response.status_code,201,response.text);return response.json()

    def test_independent_profile_and_fields_and_permissions(self):
        person=self.create();uid=person['id']
        self.assertTrue(user_path('wgm.mueller','wgm').is_dir())
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,uid).role,'wgm');self.assertIsNone(db.get(TfProfile,uid));self.assertIsNone(db.get(TfEmployment,uid));self.assertEqual(db.get(WgmProfile,uid).personnel_number,'W-001')
            self.assertEqual(db.scalar(select(WgmAddress).where(WgmAddress.user_id==uid)).postal_code,'01234')
        self.assertNotIn(uid,{p['id'] for p in self.client.get('/api/v1/admin/tf').json()})
        self.assertEqual(self.client.post('/api/v1/account/login',json={'username':'wgm.mueller','password':'wgm-secret-12345'}).status_code,401)
        _,blocked=self.active_staff({'employees':3},username='only-tf')
        self.assertEqual(blocked.get('/api/v1/admin/wgm').status_code,403)
        _,reader=self.active_staff({'wgm':1},username='wgm-reader')
        self.assertEqual(reader.get('/api/v1/admin/wgm').status_code,200)
        self.assertEqual(reader.get('/api/v1/admin/tf').status_code,403)
        edit=self.wgm();edit.pop('password');self.assertEqual(reader.put('/api/v1/admin/wgm/'+str(uid),json=edit).status_code,403)
        self.assertEqual(reader.post('/api/v1/admin/wgm',json=self.wgm(username='second')).status_code,403)
        modules=reader.get('/api/v1/admin/start').json()['modules'];self.assertIn('wgm',{m['id'] for m in modules})
        for forbidden in ['tf_number','bahncard','driver_type','home_station']:
            self.assertEqual(self.client.post('/api/v1/admin/wgm',json=self.wgm(**{forbidden:'x'})).status_code,422)

    def test_update_common_data_rename_files_and_unique_values(self):
        person=self.create();path=user_path('wgm.mueller','wgm');(path/'test.txt').write_text('retained')
        data=self.wgm(username='wgm.neu',last_name='Neu',weekly_minutes=1800);data.pop('password')
        result=self.client.put('/api/v1/admin/wgm/'+str(person['id']),json=data);self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['weekly_minutes'],1800);self.assertEqual((user_path('wgm.neu','wgm')/'test.txt').read_text(),'retained');self.assertFalse(path.exists())
        self.assertEqual(self.client.post('/api/v1/admin/wgm',json=self.wgm(username='other')).status_code,409)
        invalid=dict(data,exit_date='2019-01-01');self.assertEqual(self.client.put('/api/v1/admin/wgm/'+str(person['id']),json=invalid).status_code,422)
        self.assertEqual(self.client.get('/api/v1/admin/wgm/'+str(self.tf)).status_code,404)

    def test_legacy_migration_retains_id_credentials_photo_and_files_once(self):
        from fastapi.testclient import TestClient
        from lokzeitleiste.main import app
        from uuid import uuid4
        driver=TestClient(app,base_url='https://testserver');self.staff_clients.append(driver)
        driver.post('/api/v1/account/login',json={'username':'787100','password':'tf-secret-12345'})
        report=driver.post('/api/v1/tf/work-reports',json=dict(client_id=str(uuid4()),start_at='2026-11-12T08:00',end_at='2026-11-12T16:00',actual_pause=30,overrun_reason='',trips=[]))
        self.assertEqual(report.status_code,201,report.text)
        report_id=report.json()['id']
        with Session(self.engine) as db:
            row=db.get(EmployeeCategory,self.tf);row.category='wgm';old_hash=db.get(User,self.tf).password_hash;old_name=db.get(User,self.tf).username
            db.add(ProfilePhoto(user_id=self.tf,image_data=b'retained-photo'));db.commit()
            old=user_path(old_name,'tf');old.mkdir(parents=True,exist_ok=True);(old/'history.txt').write_text('original')
            migrate_existing_wgm(db);migrate_existing_wgm(db)
            self.assertEqual(db.get(User,self.tf).role,'wgm');self.assertEqual(db.get(User,self.tf).password_hash,old_hash)
            self.assertEqual(db.get(User,self.tf).username,old_name);self.assertEqual(db.get(WgmProfile,self.tf).personnel_number,'P-ACCOUNT')
            self.assertIsNotNone(db.get(TfProfile,self.tf),'Historical reports retain their original companion records')
            self.assertEqual(db.get(ProfilePhoto,self.tf).image_data,b'retained-photo')
            self.assertEqual((user_path(old_name,'wgm')/'history.txt').read_text(),'original');self.assertFalse(old.exists())
        self.assertNotIn(self.tf,{p['id'] for p in self.client.get('/api/v1/admin/tf').json()})
        self.assertEqual(self.client.get('/api/v1/admin/wgm').json()[0]['id'],self.tf)
        detail=self.client.get('/api/v1/admin/work-reports/'+str(report_id))
        self.assertEqual(detail.status_code,200,detail.text)
        self.assertEqual(detail.json()['employee']['employee_category'],'wgm')
        self.assertEqual(self.client.get('/api/v1/admin/work-reports/'+str(report_id)+'/pdf').status_code,200)
        self.assertEqual(driver.get('/api/v1/tf/me').status_code,401)


    def test_migration_collision_stops_without_losing_original(self):
        with Session(self.engine) as db:
            db.get(EmployeeCategory,self.tf).category='wgm';db.commit();name=db.get(User,self.tf).username
            old=user_path(name,'tf');old.mkdir(parents=True,exist_ok=True);(old/'keep.txt').write_text('keep')
            target=user_path(name,'wgm');target.mkdir(parents=True,exist_ok=True);(target/'other.txt').write_text('other')
            with self.assertRaises(Exception):migrate_existing_wgm(db)
            self.assertEqual(db.get(User,self.tf).role,'tf');self.assertIsNone(db.get(WgmProfile,self.tf))
            self.assertEqual((old/'keep.txt').read_text(),'keep');self.assertEqual((target/'other.txt').read_text(),'other')
