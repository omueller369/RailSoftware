# Regressionstests für GPS-Erfassung und Kartendarstellung.
import json,unittest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from lokzeitleiste.main import app
from lokzeitleiste.models import TrainGpsRecording,User,AccountPolicy,RailwayStationCoordinates
import test_stations
from test_gps import points

class DemoSharingTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown
    def recording(self,ended=True):
        journey=str(uuid4());response=self.driver.put('/api/v1/tf/gps/'+journey,json=dict(train_number='DEMO',points=points(),ended=ended,expected_revision=0));self.assertEqual(response.status_code,200,response.text)
        with Session(self.engine) as db:row=db.scalar(select(TrainGpsRecording).where(TrainGpsRecording.journey_id==journey));return journey,row.id,row.payload_json
    def test_confirmed_batch_is_atomic_and_owned(self):
        first,first_id,_=self.recording();second,second_id,_=self.recording()
        def change(journey,shared=True,revision=1):return dict(journey_id=journey,shared=shared,expected_revision=revision)
        endpoint='/api/v1/tf/gps-demo/shares'
        # Bei einem Konflikt in einer gewählten Aufnahme darf die gesamte Auswahl nicht veröffentlicht werden.
        failed=self.driver.post(endpoint,json={'changes':[change(first),change(second,revision=2)]})
        self.assertEqual(failed.status_code,409,failed.text)
        self.assertEqual(self.driver.get('/api/v1/tf/gps-demo/shared').json()['items'],[])
        response=self.driver.post(endpoint,json={'changes':[change(first),change(second)]})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(self.client.get('/api/v1/admin/gps-demo/shared').json()['items']),2)
        self.assertEqual(self.driver.post(endpoint,json={'changes':[change(first,False),change(second,False)]}).status_code,200)
        self.assertEqual(self.driver.get('/api/v1/tf/gps-demo/shared').json()['items'],[])
        self.assertEqual(self.driver.post(endpoint,json={'changes':[change(first),change(first)]}).status_code,422)
        self.assertEqual(self.driver.post(endpoint,json={'changes':[change(first),change(str(uuid4()))]}).status_code,404)
        self.assertEqual(self.driver.get('/api/v1/tf/gps-demo/shared').json()['items'],[])
        self.assertEqual(self.client.post(endpoint,json={'changes':[change(first)]}).status_code,403)
    def test_anonymous_and_original_preservation(self):
        anonymous=TestClient(app,base_url='https://testserver');self.staff_clients.append(anonymous)
        for prefix in ['tf','admin']:
            self.assertEqual(anonymous.get('/api/v1/'+prefix+'/gps-demo/shared').status_code,401)
        journey,entry,original=self.recording()
        self.driver.put('/api/v1/tf/gps-demo/recordings/'+journey+'/share',json=dict(shared=True,expected_revision=1))
        response=self.client.get('/api/v1/admin/gps-demo/shared/'+str(entry))
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response.headers['cache-control'])
        self.assertNotIn('journey_id',self.client.get('/api/v1/admin/gps-demo/shared').json()['items'][0])
        with Session(self.engine) as db:self.assertEqual(db.get(TrainGpsRecording,entry).payload_json,original)
    def test_explicit_snapshot_owner_only_and_revocation(self):
        journey,entry,original=self.recording();url='/api/v1/tf/gps-demo/recordings/'+journey+'/share'
        self.assertEqual(self.driver.get('/api/v1/tf/gps-demo/shared').json()['items'],[])
        self.assertEqual(self.client.get('/api/v1/admin/gps-demo/shared/'+str(entry)).status_code,404)
        self.assertEqual(self.driver.put(url,json=dict(shared=True,expected_revision=2)).status_code,409)
        self.assertEqual(self.driver.put(url,json=dict(shared=True,expected_revision=1)).status_code,200)
        self.assertEqual(len(self.client.get('/api/v1/admin/gps-demo/shared').json()['items']),1)
        # Later original edits cannot silently publish different location data.
        with Session(self.engine) as db:
            row=db.get(TrainGpsRecording,entry);payload=json.loads(row.payload_json);payload['train_number']='PRIVATE';row.payload_json=json.dumps(payload);row.revision=2;db.commit()
        self.assertEqual(self.driver.get('/api/v1/tf/gps-demo/shared/'+str(entry)).json()['train_number'],'DEMO')
        other=self.create_tf('787101','P-DEMO').json()['id'];peer=TestClient(app,base_url='https://testserver');self.staff_clients.append(peer);peer.post('/api/v1/account/login',json=dict(username='787101',password='tf-secret-12345'))
        self.assertEqual(peer.get('/api/v1/tf/gps-demo/shared/'+str(entry)).status_code,200)
        self.assertEqual(peer.put(url,json=dict(shared=False,expected_revision=2)).status_code,404)
        self.assertEqual(peer.get('/api/v1/tf/gps/'+journey).status_code,404)
        self.assertEqual(self.driver.put(url,json=dict(shared=False,expected_revision=2)).status_code,200)
        for client,prefix in [(peer,'tf'),(self.client,'admin')]:
            self.assertEqual(client.get(f'/api/v1/{prefix}/gps-demo/shared/{entry}').status_code,404)
            self.assertEqual(client.get(f'/api/v1/{prefix}/gps-demo/shared/{entry}/access').status_code,404)
        with Session(self.engine) as db:self.assertEqual(json.loads(db.get(TrainGpsRecording,entry).payload_json)['train_number'],'PRIVATE')
    def test_active_owner_finished_only_and_visibility(self):
        journey,entry,_=self.recording(False);url='/api/v1/tf/gps-demo/recordings/'+journey+'/share'
        self.assertEqual(self.driver.put(url,json=dict(shared=True,expected_revision=1)).status_code,422)
        journey,entry,_=self.recording();url='/api/v1/tf/gps-demo/recordings/'+journey+'/share';self.driver.put(url,json=dict(shared=True,expected_revision=1))
        with Session(self.engine) as db:db.get(User,self.tf).active=False;db.commit()
        self.assertEqual(self.client.get('/api/v1/admin/gps-demo/shared').json()['items'],[])
        self.assertEqual(self.client.get('/api/v1/admin/gps-demo/shared/'+str(entry)).status_code,404)
        with Session(self.engine) as db:db.get(User,self.tf).active=True;db.commit()
        url='/api/v1/tf/gps-demo/preferences';self.assertFalse(self.driver.get(url).json()['hidden']);self.assertTrue(self.driver.put(url,json={'hidden':True}).json()['hidden']);self.assertTrue(self.driver.get(url).json()['hidden'])
        self.assertEqual(self.driver.put(url,json={'hidden':'false'}).status_code,422)
    def test_current_ds100_read_only_batch_and_permissions(self):
        from test_accounts import AccountsTest
        self.change=AccountsTest.change.__get__(self);self.payload=AccountsTest.payload.__get__(self);self.create_staff=AccountsTest.create_staff.__get__(self);self.staff_login=AccountsTest.staff_login.__get__(self);self.active_staff=AccountsTest.active_staff.__get__(self)
        _,staff=self.active_staff({'gps_demo':1});_,denied=self.active_staff({'knowledge':1},username='other-office')
        for prefix,client in [('tf',self.driver),('admin',staff)]:
            url=f'/api/v1/{prefix}/gps-demo/stations'
            self.assertIsNone(client.post(url,json={'points':[{'lat':52,'lon':13}]}).json()['items'][0]['station'])
        with Session(self.engine) as db:db.add(RailwayStationCoordinates(code='BBB',catalog_name='Berlin Beispiel',latitude=52,longitude=13,source_name='Test',source_url='https://example.test',source_date='2026-11',max_spread_m=0));db.commit()
        self.assertEqual(staff.post('/api/v1/admin/gps-demo/stations',json={'points':[{'lat':52,'lon':13}]}).json()['items'][0]['station']['code'],'BBB')
        self.assertEqual(denied.get('/api/v1/admin/gps-demo/shared').status_code,403)
        self.assertEqual(denied.post('/api/v1/admin/gps-demo/stations',json={'points':[]}).status_code,403)
        self.assertEqual(staff.put('/api/v1/tf/gps-demo/preferences',json={'hidden':True}).status_code,403)
        self.assertEqual(self.driver.post('/api/v1/tf/gps-demo/stations',json={'points':[{'lat':91,'lon':13}]}).status_code,422)
        self.assertIn('gps_demo',[m['id'] for m in staff.get('/api/v1/admin/start').json()['modules']])
