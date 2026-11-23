# Regressionstests für Ortskenntnisse und ihre Gültigkeit.
import unittest,json
from datetime import date,datetime,timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select
import test_stations
from lokzeitleiste.main import app
from lokzeitleiste.models import TfLocationKnowledge
from lokzeitleiste.location_knowledge import add_months,validity,renew_from_gps,refresh_hash

class LocationKnowledgeTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown
    def add(self,**changes):
        data=dict(ds100='AAA',known_until='2027-11-17');data.update(changes);return self.driver.post('/api/v1/tf/location-knowledge',json=data)
    def items(self):return self.driver.get('/api/v1/tf/knowledge/places').json()['items']
    @patch('lokzeitleiste.location_knowledge.today',return_value=date(2026,11,17))
    def test_add_boundaries_calendar_and_no_other_owner_access(self,_):
        self.assertEqual(self.add(known_until='2027-11-18').status_code,422)
        self.assertEqual(self.add(known_until='2026-11-16').status_code,422)
        self.assertEqual(self.add(ds100='UNKNOWN').status_code,422)
        response=self.add(known_until='2027-01-01');self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.add().status_code,409)
        item=self.items()[0];self.assertEqual(item['validity'],'expiring')
        self.create_tf('787101','P-LOC-OTHER');other=TestClient(app,base_url='https://testserver');self.staff_clients.append(other);other.post('/api/v1/account/login',json={'username':'787101','password':'tf-secret-12345'})
        path='/api/v1/tf/location-knowledge/'+str(item['id']);payload=dict(known_until='2027-11-17',expected_revision=item['revision'])
        self.assertEqual(other.patch(path,json=payload).status_code,404)
        self.assertEqual(self.client.patch(path,json=payload).status_code,403)
        self.assertEqual(self.driver.patch(path,json={**payload,'known_until':'2026-12-31'}).status_code,422)
        self.assertEqual(self.driver.patch(path,json=payload).status_code,200)
        self.assertEqual(self.driver.patch(path,json=payload).status_code,409,'Stale editor cannot overwrite GPS or another update')
        self.assertEqual(self.items()[0]['known_until'],'2027-11-17')
    def test_leap_year_and_three_calendar_months(self):
        self.assertEqual(add_months(date(2024,2,29),12),date(2025,2,28))
        self.assertEqual(add_months(date(2026,8,31),3),date(2026,11,30))
        self.assertEqual(validity('2027-02-17',date(2026,11,17)),'expiring')
        self.assertEqual(validity('2027-02-18',date(2026,11,17)),'valid')
        self.assertEqual(validity('2026-11-17',date(2026,11,17)),'expiring')
        self.assertEqual(validity('2026-11-16',date(2026,11,17)),'expired')
        self.assertEqual(validity('0000-00-00'),'unknown')
    @patch('lokzeitleiste.location_knowledge.today',return_value=date(2026,11,17))
    def test_gps_capture_day_not_upload_date_no_downgrade_no_early_end_and_replay(self,_):
        first=int(datetime(2026,11,10,22,45,tzinfo=timezone.utc).timestamp()*1000)
        later=int(datetime(2026,11,11,1,0,tzinfo=timezone.utc).timestamp()*1000)
        payload=dict(start_station='AAA',end_station='BBB',ended=False,points=[dict(t=first,lat=52,lon=13,accuracy=5),dict(t=later,lat=52.001,lon=13.001,accuracy=5)])
        with Session(self.engine) as db:
            self.assertEqual(renew_from_gps(db,self.tf,payload),1);db.commit()
            rows=list(db.scalars(select(TfLocationKnowledge).where(TfLocationKnowledge.owner_id==self.tf)));self.assertEqual(len(rows),1);self.assertEqual(rows[0].known_until,'2027-11-10')
            payload['ended']=True;payload['renew_end_location']=True;payload['renew_end_station']='BBB';self.assertEqual(renew_from_gps(db,self.tf,payload),1);db.commit()
            rows={r.ds100:r for r in db.scalars(select(TfLocationKnowledge).where(TfLocationKnowledge.owner_id==self.tf))};self.assertEqual(rows['BBB'].known_until,'2027-11-11')
            rows['AAA'].known_until='2030-01-01';refresh_hash(rows['AAA']);db.commit()
            self.assertEqual(renew_from_gps(db,self.tf,payload),0);self.assertEqual(rows['AAA'].known_until,'2030-01-01')
            self.assertEqual(renew_from_gps(db,self.tf,{**payload,'points':[]}),0)
            self.assertEqual(renew_from_gps(db,self.tf,{**payload,'points':[dict(t=first,accuracy=150),dict(t=later,accuracy=150)]}),0)
            self.assertEqual(renew_from_gps(db,self.tf,{**payload,'start_station':None,'end_station':None}),0)
    @patch('lokzeitleiste.location_knowledge.today',return_value=date(2026,11,17))
    def test_real_gps_save_updates_inventory_atomically(self,_):
        from uuid import uuid4
        t=int(datetime(2026,11,10,23,30,tzinfo=timezone.utc).timestamp()*1000)
        body=dict(train_number='123',expected_revision=0,start_station='AAA',end_station='BBB',renew_end_location=True,renew_end_station='BBB',ended=True,points=[dict(t=t,lat=52,lon=13,accuracy=5),dict(t=t+60000,lat=52.001,lon=13.001,accuracy=5)])
        response=self.driver.put('/api/v1/tf/gps/'+str(uuid4()),json=body);self.assertEqual(response.status_code,200,response.text)
        items=self.items();self.assertEqual(len(items),2);self.assertTrue(all(row['known_until']=='2027-11-11' for row in items),'Berlin capture date used after midnight')

    @patch('lokzeitleiste.location_knowledge.today',return_value=date(2026,11,17))
    def test_destination_requires_station_bound_yes_and_keeps_no_on_replay(self,_):
        from uuid import uuid4
        t=int(datetime(2026,11,10,12,tzinfo=timezone.utc).timestamp()*1000)
        path='/api/v1/tf/gps/'+str(uuid4())
        body=dict(train_number='123',expected_revision=0,start_station='AAA',end_station='BBB',ended=True,points=[dict(t=t,lat=52,lon=13,accuracy=5),dict(t=t+60000,lat=52.001,lon=13.001,accuracy=5)])
        for decision,station in [(None,None),(False,'BBB'),(True,'AAA')]:
            if decision is not None:body.update(renew_end_location=decision,renew_end_station=station)
            response=self.driver.put(path,json=body);self.assertEqual(response.status_code,200,response.text)
            body['expected_revision']=response.json()['revision']
            self.assertEqual([r['ds100'] for r in self.items()],['AAA'],'Missing, No, or another destination never grants renewal')
        body.update(renew_end_location=True,renew_end_station='BBB')
        response=self.driver.put(path,json=body);self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.json()['renew_end_location']);body['expected_revision']=response.json()['revision']
        places={r['ds100']:r for r in self.items()};self.assertEqual(places['BBB']['known_until'],'2027-11-10')
        before=places['BBB'].copy()
        body.update(renew_end_location=False)
        response=self.driver.put(path,json=body);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(next(r for r in self.items() if r['ds100']=='BBB'),before,'No never shortens or deletes previous knowledge')

    @patch('lokzeitleiste.location_knowledge.today',return_value=date(2026,11,17))
    def test_legacy_spacing_does_not_allow_a_duplicate_new_station(self,_):
        from lokzeitleiste.models import RailwayStation
        from lokzeitleiste.location_knowledge import identity_key
        with Session(self.engine) as db:
            db.add(RailwayStation(code='AA G',name='Güterbahnhof'))
            row=TfLocationKnowledge(owner_id=self.tf,identity_key=identity_key('AA  G'),station_name='Alter Name',ds100='AA  G',known_until='2027-01-01');refresh_hash(row);db.add(row);db.commit()
        self.assertEqual(self.add(ds100=' aa g ').status_code,409)
        self.assertEqual(len(self.items()),1)
