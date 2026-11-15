import json,unittest
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import test_accounts
from lokzeitleiste.main import app
from lokzeitleiste.models import GpsLivePosition,TrainGpsRecording
from lokzeitleiste.gps_preferences import Preferences
from lokzeitleiste.gps_analysis import analyse


class GpsPreferencesTest(unittest.TestCase):
    tearDown=test_accounts.AccountsTest.tearDown
    def setUp(self):
        test_accounts.AccountsTest.setUp(self)
        self.now=datetime(2026,11,15,12,0)
        mock=patch('lokzeitleiste.gps_preferences.now_utc',side_effect=lambda:self.now);mock.start();self.addCleanup(mock.stop)
        self.driver=TestClient(app,base_url='https://testserver');self.staff_clients.append(self.driver)
        self.driver.post('/api/v1/account/login',json={'username':'787100','password':'tf-secret-12345'})
        self.second=self.create_tf('787101','P-GPS-SECOND').json()['id']
        self.viewer=TestClient(app,base_url='https://testserver');self.staff_clients.append(self.viewer)
        self.viewer.post('/api/v1/account/login',json={'username':'787101','password':'tf-secret-12345'})
    def test_original_marker_png_assets_have_correct_type_and_safe_paths(self):
        from pathlib import Path
        from PIL import Image
        import io
        for kind in ['electric','steam','diesel','tank']:
            response=self.client.get('/tf/gps-marker-'+kind+'.png')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['content-type'],'image/png')
            self.assertEqual(response.content,(Path(__file__).parents[1]/'lokzeitleiste/static'/('gps-marker-'+kind+'.png')).read_bytes())
            image=Image.open(io.BytesIO(response.content));self.assertEqual(image.size,(128,128));self.assertEqual(image.mode,'RGBA')
            self.assertEqual(image.getextrema()[-1],(0,255))
        self.assertEqual(self.client.get('/tf/gps-marker-unknown.png').status_code,422)

    def prefs(self,client=None,**values):
        client=client or self.driver;old=client.get('/api/v1/tf/gps-settings').json();data={key:old[key] for key in Preferences.model_fields};data.update(values,expected_revision=old['revision'])
        reply=client.put('/api/v1/tf/gps-settings',json=data);self.assertEqual(reply.status_code,200,reply.text);return reply.json()
    def start(self):
        reply=self.driver.post('/api/v1/tf/gps-sharing/start',json={'journey_id':str(uuid4())});self.assertEqual(reply.status_code,200,reply.text);return reply.json()['session_id']
    def point(self,**values):
        point=dict(t=int(self.now.replace(tzinfo=timezone.utc).timestamp()*1000),lat=52.1,lon=13.1,accuracy=5,speed=12,elapsed_ms=600000,stopped_ms=60000,train_number='12345');point.update(values);return point
    def send(self,session,**values):return self.driver.put('/api/v1/tf/gps-sharing/'+session,json=self.point(**values))
    def feed(self):return self.viewer.get('/api/v1/tf/gps-shared-positions').json()['positions']

    def test_defaults_and_consent_do_not_start_sharing(self):
        data=self.driver.get('/api/v1/tf/gps-settings').json();self.assertFalse(data['share_enabled']);self.assertEqual(data['stop_minutes'],2)
        self.assertEqual(self.driver.post('/api/v1/tf/gps-sharing/start',json={'journey_id':str(uuid4())}).status_code,403)
        self.prefs(share_enabled=True,stop_minutes=15,marker='steam')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(GpsLivePosition)),0)
            self.assertEqual(db.scalar(select(func.count()).select_from(TrainGpsRecording)),0)
        self.assertEqual(self.feed(),[])
        session=self.start();self.assertEqual(self.feed(),[])
        self.assertTrue(self.send(session).json()['accepted']);self.assertEqual(len(self.feed()),1)
        self.assertEqual(self.feed()[0]['marker'],'steam')
        self.assertEqual(self.driver.get('/api/v1/tf/gps-shared-positions').json()['positions'],[])

    def test_five_minute_limit_expiry_no_backfill_and_freshness(self):
        self.prefs(share_enabled=True);session=self.start();self.assertTrue(self.send(session).json()['accepted'])
        self.assertFalse(self.send(session,lat=53).json()['accepted']);self.assertEqual(self.feed()[0]['lat'],52.1)
        self.now+=timedelta(seconds=300);self.assertTrue(self.send(session,lat=53).json()['accepted']);self.assertEqual(self.feed()[0]['lat'],53)
        self.now+=timedelta(seconds=601);self.assertEqual(self.feed(),[])
        self.assertEqual(self.send(session,t=self.point()['t']-121000).status_code,422)
        self.assertEqual(self.send(session,accuracy=51).status_code,422)
        self.assertTrue(self.send(session).json()['accepted'])
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(func.count()).select_from(GpsLivePosition)),1)

    def test_both_sides_control_fields_and_first_name_is_server_owned(self):
        self.prefs(share_enabled=True,show_first_name=True,show_speed=False)
        self.prefs(self.viewer,show_first_name=True,show_train=False)
        session=self.start();self.assertEqual(self.send(session).status_code,200)
        row=self.feed()[0];self.assertEqual(row['first_name'],'Mira');self.assertNotIn('speed',row);self.assertNotIn('train_number',row)
        self.assertIn('elapsed_ms',row);self.assertNotIn('session_id',row)
        self.assertEqual(self.send(session,first_name='Spoof').status_code,422)
        self.prefs(show_first_name=False);self.assertNotIn('first_name',self.feed()[0])

    def test_revoke_stop_ownership_and_revision(self):
        self.prefs(share_enabled=True);session=self.start();self.send(session)
        self.assertEqual(self.viewer.put('/api/v1/tf/gps-sharing/'+session,json=self.point()).status_code,403)
        self.viewer.delete('/api/v1/tf/gps-sharing/'+session);self.assertEqual(len(self.feed()),1)
        self.prefs(share_enabled=False);self.assertEqual(self.feed(),[])
        self.assertEqual(self.send(session).status_code,403)
        self.prefs(share_enabled=True);self.assertEqual(self.send(session).status_code,409)
        replacement=self.start();self.send(replacement);self.driver.delete('/api/v1/tf/gps-sharing/'+replacement);self.assertEqual(self.feed(),[])
        old=self.driver.get('/api/v1/tf/gps-settings').json();body={key:old[key] for key in Preferences.model_fields};body['expected_revision']=0
        self.assertEqual(self.driver.put('/api/v1/tf/gps-settings',json=body).status_code,409)
        body.update(expected_revision=old['revision'],stop_minutes=3);self.assertEqual(self.driver.put('/api/v1/tf/gps-settings',json=body).status_code,422)
        for path in ['/api/v1/tf/gps-settings','/api/v1/tf/gps-shared-positions']:
            self.assertEqual(self.client.get(path,headers={'X-CTL-Area':'backend'}).status_code,403)

    def test_recording_preserves_threshold_and_only_new_recordings_change_it(self):
        start=self.point()['t'];journey=str(uuid4());path='/api/v1/tf/gps/'+journey
        points=[dict(t=start+i*5000,lat=52,lon=13,accuracy=5,speed=0) for i in range(13)]
        data=dict(train_number='123',points=points,ended=False,stop_minutes=1,expected_revision=0)
        reply=self.driver.put(path,json=data);self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual(reply.json()['stop_minutes'],1)
        self.prefs(stop_minutes=15)
        self.assertEqual(self.driver.get(path).json()['stop_minutes'],1)
        data.update(stop_minutes=None,expected_revision=1)
        reply=self.driver.put(path,json=data);self.assertEqual(reply.status_code,200,reply.text);self.assertEqual(reply.json()['stop_minutes'],1)
        data.update(stop_minutes=4,expected_revision=2)
        self.assertEqual(self.driver.put(path,json=data).status_code,409)

    def test_stop_thresholds_are_inclusive_and_gaps_never_imply_a_stop(self):
        start=self.point()['t']
        for minutes in [1,2,4,5,10,15]:
            points=[dict(t=start+i*5000,lat=52,lon=13,accuracy=5,speed=0) for i in range(minutes*12+1)]
            self.assertEqual(len([r for r in analyse(points[:-1],stop_minutes=minutes)['rows'] if r['kind']=='Halt']),0)
            self.assertEqual(len([r for r in analyse(points,stop_minutes=minutes)['rows'] if r['kind']=='Halt']),1)
        points=[dict(t=start,lat=52,lon=13,accuracy=5,speed=0),dict(t=start+120000,lat=52,lon=13,accuracy=5,speed=0)]
        self.assertFalse([r for r in analyse(points,stop_minutes=1)['rows'] if r['kind']=='Halt'])
