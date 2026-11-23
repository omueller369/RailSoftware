# Regressionstests für Betriebsstellen und Ortszuordnungen.
import json,math,unittest
from datetime import datetime,timezone
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import test_stations
from lokzeitleiste.main import app
from lokzeitleiste.models import RailwayStationCoordinates,StationCoordinateContribution


class StationContributionTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown
    def point(self,lat=52,lon=13,code='BBB'):
        with Session(self.engine) as db:
            point=db.get(RailwayStationCoordinates,code)
            if not point:point=RailwayStationCoordinates(code=code);db.add(point)
            point.catalog_name='Berlin Beispiel';point.latitude=lat;point.longitude=lon;point.source_name='Original';point.source_url='https://example.test/source';point.source_date='2026-05';point.max_spread_m=0;db.commit()
    def check(self,lat=52,lon=13,code='BBB',**params):
        return self.driver.get('/api/v1/tf/stations/'+code+'/coordinates',params={'owner_id':self.tf,'latitude':lat,'longitude':lon,**params})
    def data(self,lat=52,lon=13,**changes):
        plan=self.check(lat,lon).json()
        return dict(request_id=str(uuid4()),owner_id=self.tf,latitude=lat,longitude=lon,accuracy_m=5,observed_at=1794744000000,expected_token=plan['token'],confirmed=True,confirm_overwrite=False,**changes)
    def write(self,data,code='BBB'):
        return self.driver.put('/api/v1/tf/stations/'+code+'/coordinates',json=data)
    def test_create_audited_shared_coordinate_and_idempotent_retry(self):
        self.assertIsNone(self.check().json()['coordinate'])
        data=self.data();result=self.write(data);self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['coordinate']['latitude'],52)
        self.assertEqual(self.driver.get('/api/v1/tf/stations/coordinate-revision').json()['revision'],1)
        again=self.write(data);self.assertEqual(again.status_code,200);self.assertTrue(again.json()['already_applied'])
        self.assertTrue(self.check(request_id=data['request_id']).json()['already_applied'])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(StationCoordinateContribution)),1)
            audit=db.scalar(select(StationCoordinateContribution));self.assertEqual(audit.owner_id,self.tf);self.assertIsNone(audit.before_json);self.assertEqual(json.loads(audit.proposal_json)['accuracy_m'],5)
        self.create_tf('787200','COORD-OTHER')
        other=TestClient(app,base_url='https://testserver');self.staff_clients.append(other);other.post('/api/v1/account/login',json={'username':'787200','password':'tf-secret-12345'})
        row=other.get('/api/v1/tf/stations/catalog?q=BBB').json()[0];self.assertEqual(row['coordinates']['latitude'],52)
        snapshot=other.get('/api/v1/tf/stations/offline-catalog').json();self.assertEqual(snapshot['coordinate_revision'],1);self.assertIn(['BBB','Berlin Beispiel',52,13],snapshot['stations'])
        self.assertEqual(self.write({**data,'latitude':51}).status_code,409)
        self.assertEqual(self.write(data,code='AAA').status_code,409)
    def test_nearby_and_exactly_1000m_need_only_initial_confirmation(self):
        self.point(0,1)
        latitude=math.degrees(1000/6371000)
        check=self.check(latitude,1).json();self.assertAlmostEqual(check['distance_m'],1000,places=6);self.assertFalse(check['confirmation_required'])
        data=self.data(latitude,1);self.assertEqual(self.write({**data,'confirmed':False}).status_code,422)
        self.assertEqual(self.write(data).status_code,200)
        with Session(self.engine) as db:self.assertAlmostEqual(db.get(RailwayStationCoordinates,'BBB').latitude,latitude)
    def test_far_replacement_requires_second_confirmation_and_records_previous_point(self):
        self.point(51,12);check=self.check().json();self.assertTrue(check['confirmation_required']);self.assertGreater(check['distance_m'],1000)
        data=self.data();response=self.write(data);self.assertEqual(response.status_code,409);self.assertEqual(response.json()['detail']['code'],'confirmation_required')
        with Session(self.engine) as db:self.assertEqual(db.get(RailwayStationCoordinates,'BBB').latitude,51)
        response=self.write({**data,'confirm_overwrite':True});self.assertEqual(response.status_code,200,response.text)
        with Session(self.engine) as db:
            row=db.scalar(select(StationCoordinateContribution));self.assertEqual(json.loads(row.before_json)['latitude'],51);self.assertEqual(db.get(RailwayStationCoordinates,'BBB').latitude,52)
    def test_concurrent_change_cannot_be_overwritten_using_an_old_confirmation(self):
        data=self.data();self.point(50,10)
        result=self.write({**data,'confirm_overwrite':True});self.assertEqual(result.status_code,409);self.assertEqual(result.json()['detail']['code'],'coordinate_changed')
        with Session(self.engine) as db:self.assertEqual(db.get(RailwayStationCoordinates,'BBB').latitude,50);self.assertEqual(db.scalar(select(func.count()).select_from(StationCoordinateContribution)),0)
        data['expected_token']=self.check().json()['token'];self.assertEqual(self.write(data).status_code,409);self.assertEqual(self.write({**data,'confirm_overwrite':True}).status_code,200)
        # Geht eine Bestätigung verloren, darf dieselbe angenommene Anfrage keine zweite Anwendung verlangen.
        self.point(49,9)
        repeat=self.check(request_id=data['request_id']).json();self.assertTrue(repeat['already_applied']);self.assertEqual(repeat['coordinate']['latitude'],49)
    def test_authentication_owner_binding_and_invalid_proposals(self):
        data=self.data();path='/api/v1/tf/stations/BBB/coordinates'
        self.assertEqual(self.client.put(path,json=data).status_code,403)
        self.assertEqual(self.write({**data,'owner_id':self.tf+999}).status_code,403)
        for changes in [dict(latitude=91),dict(longitude=181),dict(latitude='NaN'),dict(accuracy_m=51),dict(accuracy_m=-1),dict(latitude=0,longitude=0),dict(expected_token='bad')]:
            self.assertEqual(self.write({**data,**changes}).status_code,422,changes)
        self.assertEqual(self.check(code='UNKNOWN').status_code,404)
        self.assertEqual(self.check(owner_id=self.tf+1).status_code,403)
        self.driver.cookies.clear();self.assertEqual(self.write(data).status_code,401)
