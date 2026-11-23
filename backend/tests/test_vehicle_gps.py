# Fahrzeugfahrten prüfen wir über die echten Anmelde-, GPS- und Verwaltungsrouten.
import unittest
from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from test_stations import StationDirectoryTest
from test_accounts import AccountsTest
from lokzeitleiste.models import VehicleGpsJourney

class VehicleGpsTest(unittest.TestCase):
    setUp=StationDirectoryTest.setUp
    tearDown=StationDirectoryTest.tearDown
    active_staff=AccountsTest.active_staff
    create_staff=AccountsTest.create_staff
    staff_login=AccountsTest.staff_login
    change=AccountsTest.change
    payload=AccountsTest.payload

    def create(self,number='91 80 6185 001-2'):
        r=self.client.post('/api/v1/admin/vehicles',json={'vehicle_number':number});self.assertEqual(r.status_code,201,r.text);return r.json()['id']
    def body(self,**values):
        at=int(datetime(2026,11,10,23,30,tzinfo=timezone.utc).timestamp()*1000)
        return dict(dict(train_number='123',expected_revision=0,start_station='AAA',end_station='BBB',ended=True,points=[dict(t=at,lat=52,lon=13,accuracy=5),dict(t=at+60000,lat=52.009,lon=13,accuracy=5)]),**values)
    def count(self):
        with Session(self.engine) as db:return db.scalar(select(func.count()).select_from(VehicleGpsJourney))
    def test_optional_live_completed_replay_and_cleanup(self):
        vehicle=self.create();path='/api/v1/tf/gps/'+str(uuid4());body=self.body(vehicle_id=vehicle,ended=False)
        r=self.driver.put(path,json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.count(),0)
        self.assertFalse(self.client.get('/api/v1/admin/vehicles').json()[0]['has_gps_journeys'])
        body.update(expected_revision=1,ended=True)
        r=self.driver.put(path,json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.count(),1)
        body['expected_revision']=2;r=self.driver.put(path,json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.count(),1)
        result=self.client.get(f'/api/v1/admin/vehicles/{vehicle}/gps-journeys').json();row=result['items'][0]
        self.assertEqual((row['date'],row['time'],row['tf_number'],row['from_code'],row['to_code']),('11.11.2026','00.30','787100','AAA','BBB'));self.assertAlmostEqual(row['total_km'],1.001,places=3)
        self.assertTrue(self.client.get('/api/v1/admin/vehicles').json()[0]['has_gps_journeys'])
        self.assertEqual(self.driver.delete(path).status_code,200);self.assertEqual(self.count(),1,'Compacting raw points retains the separate completed journey')
        r=self.driver.put('/api/v1/tf/gps/'+str(uuid4()),json=self.body());self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.count(),1,'No vehicle selection creates no fleet entry')
    def test_locked_assignment_unknown_vehicle_and_permissions(self):
        vehicle=self.create();other=self.create('91 80 6185 002-0');path='/api/v1/tf/gps/'+str(uuid4());body=self.body(vehicle_id=vehicle,ended=False)
        r=self.driver.put(path,json=body);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.driver.put(path,json={**body,'vehicle_id':other,'expected_revision':1}).status_code,409)
        self.assertEqual(self.driver.put('/api/v1/tf/gps/'+str(uuid4()),json=self.body(vehicle_id=999999)).status_code,422)
        # Eine alte App ohne das neue Feld darf die bestehende Zuordnung nicht löschen.
        old={k:v for k,v in body.items() if k!='vehicle_id'};old['expected_revision']=1;r=self.driver.put(path,json=old);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['vehicle_id'],vehicle)
        url=f'/api/v1/admin/vehicles/{vehicle}/gps-journeys'
        self.assertIn(self.driver.get(url).status_code,[401,403])
        _,denied=self.active_staff({},'gps-denied');self.assertEqual(denied.get(url).status_code,403)
        _,reader=self.active_staff({'vehicles':1},'gps-reader');self.assertEqual(reader.get(url).status_code,200)
    def test_gap_estimation_and_explicit_pause_not_bridged(self):
        vehicle=self.create();body=self.body(vehicle_id=vehicle);a,b=body['points'];body['points']=[a,{**b,'break_before':True,'accuracy':80},{**b,'t':b['t']+60000,'lat':52.018},{**b,'t':b['t']+120000,'lat':52.027}]
        r=self.driver.put('/api/v1/tf/gps/'+str(uuid4()),json=body);self.assertEqual(r.status_code,200,r.text)
        row=self.client.get(f'/api/v1/admin/vehicles/{vehicle}/gps-journeys').json()['items'][0];self.assertAlmostEqual(row['total_km'],1.001,places=3)
