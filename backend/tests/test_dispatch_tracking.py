"""Dispatcher classification, delegation and consent/TTL-gated live tracking."""
import json,unittest
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.orm import Session
from sqlalchemy import select
import test_accounts
from lokzeitleiste.models import EmployeeCategory,GpsPreference,GpsLivePosition,ModulePermission,User
from lokzeitleiste.gps_preferences import Preferences

class DispatchTrackingTest(unittest.TestCase):
    setUp=test_accounts.AccountsTest.setUp
    tearDown=test_accounts.AccountsTest.tearDown
    payload=test_accounts.AccountsTest.payload
    create_staff=test_accounts.AccountsTest.create_staff
    staff_login=test_accounts.AccountsTest.staff_login
    active_staff=test_accounts.AccountsTest.active_staff
    change=test_accounts.AccountsTest.change
    def dispatcher(self,name='dispatch-one',permissions=None):
        response=self.client.post('/api/v1/admin/dispatchers',json=self.payload(name,permissions))
        self.assertEqual(response.status_code,201,response.text);return response.json()['id']
    def test_separate_stocks_default_access_login_and_explicit_opt_out(self):
        self.assertEqual(self.client.post('/api/v1/admin/dispatchers',json={**self.payload('invalid-dispatch'),'permissions':None}).status_code,422)
        dispatcher=self.dispatcher();office=self.create_staff({},'normal-office')
        self.assertEqual([r['id'] for r in self.client.get('/api/v1/admin/dispatchers').json()],[dispatcher])
        self.assertEqual([r['id'] for r in self.client.get('/api/v1/admin/staff').json()],[office])
        data=self.client.get('/api/v1/admin/dispatchers').json()[0];self.assertEqual(data['permissions']['tracking'],1)
        self.assertEqual(data['addresses'][0]['postal_code'],'01234');self.assertNotIn('password_hash',data)
        self.assertEqual(self.client.put('/api/v1/admin/staff/'+str(dispatcher),json=self.payload('unused',data['permissions'])).status_code,404)
        updated={**self.payload('unused',data['permissions']),'last_name':'Disposition'}
        r=self.client.put('/api/v1/admin/dispatchers/'+str(dispatcher),json=updated);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.put('/api/v1/admin/dispatchers/'+str(office),json=updated).status_code,404)
        client,_=self.staff_login('dispatch-one');self.assertEqual(client.get('/api/v1/admin/tracking/positions').status_code,403)
        self.assertEqual(self.change(client).status_code,200);client.post('/api/v1/admin/login',json={'username':'dispatch-one','password':'personal-secret-67890'})
        self.assertEqual(client.get('/api/v1/admin/tracking/positions').status_code,200)
        self.assertIn('tracking',{r['id'] for r in client.get('/api/v1/admin/start').json()['modules']})
        self.assertEqual(client.get('/api/v1/admin/dispatchers').status_code,403)
        self.dispatcher('dispatch-disabled',{'tracking':0})
        self.assertEqual(next(r for r in self.client.get('/api/v1/admin/dispatchers').json() if r['username']=='dispatch-disabled')['permissions']['tracking'],0)
        self.assertIn('Disponenten',self.client.get('/admin/dispatchers').text)
    def test_delegation_and_other_permissions_cannot_bypass_classification(self):
        target=self.dispatcher();_,office=self.active_staff({'staff':3},'staff-manager')
        self.assertEqual(office.get('/api/v1/admin/dispatchers').status_code,403)
        self.assertEqual(office.get('/api/v1/admin/tracking/positions').status_code,403)
        self.assertEqual(office.get('/api/v1/admin/staff/'+str(target)+'/photo').status_code,403)
        self.assertEqual(office.post('/api/v1/admin/accounts/'+str(target)+'/reset-password',json={'initial_password':'reset-secret-12345'}).status_code,403)
        _,manager=self.active_staff({'dispatchers':3,'tracking':1},'dispatch-manager')
        self.assertEqual(manager.get('/api/v1/admin/dispatchers').status_code,200)
        payload=self.payload('cannot-escalate',{'tracking':3})
        self.assertEqual(manager.post('/api/v1/admin/dispatchers',json=payload).status_code,403)
        self.assertEqual(manager.get('/api/v1/admin/staff').status_code,403)
    def test_feed_consent_active_session_field_disclosure_and_expiry(self):
        now=datetime(2026,11,18,12);stamp=int(now.replace(tzinfo=timezone.utc).timestamp()*1000)
        pref=Preferences(share_enabled=True,show_train=True,show_first_name=True)
        point={'t':stamp,'lat':51.15,'lon':10.4,'train_number':'12345','elapsed_ms':1000,'stopped_ms':0,'speed':2}
        with Session(self.engine) as db:
            db.add(GpsPreference(user_id=self.tf,payload_json=pref.model_dump_json(),revision=1));db.add(GpsLivePosition(user_id=self.tf,session_id=str(uuid4()),journey_id=str(uuid4()),point_json=json.dumps(point),updated_at=now));db.commit()
        with patch('lokzeitleiste.gps_preferences.now_utc',return_value=now):
            r=self.client.get('/api/v1/admin/tracking/positions');self.assertEqual(r.status_code,200,r.text);self.assertIn('no-store',r.headers['cache-control'])
            item=r.json()['positions'][0];self.assertEqual(item['train_number'],'12345');self.assertIn('first_name',item);self.assertNotIn('last_name',item)
            with Session(self.engine) as db:
                pref.show_train=pref.show_first_name=False;db.get(GpsPreference,self.tf).payload_json=pref.model_dump_json();db.commit()
            item=self.client.get('/api/v1/admin/tracking/positions').json()['positions'][0];self.assertNotIn('train_number',item);self.assertNotIn('first_name',item)
            with Session(self.engine) as db:db.get(User,self.tf).active=False;db.commit()
            self.assertEqual(self.client.get('/api/v1/admin/tracking/positions').json()['positions'],[])
            with Session(self.engine) as db:
                db.get(User,self.tf).active=True;pref.share_enabled=False;db.get(GpsPreference,self.tf).payload_json=pref.model_dump_json();db.commit()
            self.assertEqual(self.client.get('/api/v1/admin/tracking/positions').json()['positions'],[])
            with Session(self.engine) as db:
                pref.share_enabled=True;db.get(GpsPreference,self.tf).payload_json=pref.model_dump_json();db.commit()
        with patch('lokzeitleiste.gps_preferences.now_utc',return_value=now+timedelta(seconds=601)):
            self.assertEqual(self.client.get('/api/v1/admin/tracking/positions').json()['positions'],[])
        with Session(self.engine) as db:db.delete(db.get(GpsLivePosition,self.tf));db.commit()
        self.assertEqual(self.client.get('/api/v1/admin/tracking/positions').json()['positions'],[])
