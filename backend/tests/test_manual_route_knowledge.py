"""Manual M1 routes are owned, bounded, validated and never manufactured GPS rides."""
import json,unittest
from datetime import timedelta
from sqlalchemy import select,func
from sqlalchemy.orm import Session
import test_api
from lokzeitleiste.models import ManualRouteKnowledge,TrainGpsRecording,RouteKnowledgeEntry
from lokzeitleiste.manual_route_knowledge import today,maximum
from lokzeitleiste.route_knowledge_import import digest,packed

class ManualRouteTest(unittest.TestCase):
    def setUp(self):
        test_api.ApiFlowTest.setUp(self)
        self.client.post('/api/v1/admin/login',json={'username':'admin','password':'admin-secret-12345'})
        self.uid=test_api.ApiFlowTest.create_tf(self,'787119','MANUAL').json()['id']
        login=self.client.post('/api/v1/account/login',json={'username':'787119','password':'tf-secret-12345'})
        self.headers={'Authorization':'Bearer '+login.json()['access_token']}
        self.payload=dict(waypoints=['AFW','AFR'],routes=['1000'],valid_until=maximum(today()).isoformat())
    def tearDown(self):test_api.ApiFlowTest.tearDown(self)
    def save(self,**changes):return self.client.post('/api/v1/tf/route-knowledge/manual',json={**self.payload,**changes},headers=self.headers)
    def listing(self):return self.client.get('/api/v1/tf/route-knowledge/imports',headers=self.headers).json()['items']
    def test_save_qualified_m1_route_without_gps_and_duplicate(self):
        result=self.save();self.assertEqual(result.status_code,201,result.text)
        row=self.listing()[0];self.assertEqual(row['status'],'streckenkundig');self.assertEqual(row['acquisition_trips'],'');self.assertEqual(row['map_match']['status'],'mapped');self.assertEqual(row['valid_until'],self.payload['valid_until'])
        self.assertEqual(self.save().status_code,409)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(ManualRouteKnowledge)),1)
            self.assertEqual(db.scalar(select(func.count()).select_from(TrainGpsRecording)),0)
    def test_bad_dates_routes_and_unknown_or_disconnected_points_rejected(self):
        for data in [dict(valid_until=(today()-timedelta(days=1)).isoformat()),dict(valid_until=(maximum(today())+timedelta(days=1)).isoformat()),dict(routes=['999999']),dict(waypoints=['AFW','AFW']),dict(waypoints=['AFW','MISSING']),dict(routes=['1000','1001']),dict(waypoints=['AFW','BLS'])]:
            result=self.save(**data);self.assertEqual(result.status_code,422,(data,result.text))
        self.assertEqual(self.listing(),[])
    def test_confirmed_csv_priority_and_ownership(self):
        row=dict(section='Original CSV',route_number='1000',status='streckenkundig',valid_until='2030-01-01',acquired_since='2020-01-01',acquisition_trips='7',from_code='AFW',to_code='AFR')
        with Session(self.engine) as db:
            original=packed(row);db.add(RouteKnowledgeEntry(owner_id=self.uid,section_key=digest('original'),content_sha256=digest(original),source_json=original,source_sha256='a'*64));db.commit()
        self.assertEqual(self.save().status_code,201)
        self.assertEqual(self.save(waypoints=['AFR','AFW']).status_code,201)
        rows=self.listing();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['section'],'Original CSV');self.assertEqual(rows[0]['valid_until'],'2030-01-01')
        other=test_api.ApiFlowTest.create_tf(self,'787120','MANUAL-OTHER').json()['id']
        token=self.client.post('/api/v1/account/login',json={'username':'787120','password':'tf-secret-12345'}).json()['access_token']
        items=self.client.get('/api/v1/tf/route-knowledge/imports',headers={'Authorization':'Bearer '+token}).json()['items'];self.assertEqual(items,[])
        self.assertEqual(self.client.post('/api/v1/tf/route-knowledge/manual',json=self.payload,headers={'X-CTL-Area':'backend'}).status_code,403)
    def test_calendar_year_leap_date(self):
        from datetime import date
        self.assertEqual(maximum(date(2028,2,29)),date(2029,2,28))
