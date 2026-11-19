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

    def test_long_point_sequence_is_preserved_without_gps(self):
        codes=['AFW' if i%2==0 else 'AFR' for i in range(1001)]
        result=self.save(waypoints=codes,routes=['1000']*1000)
        self.assertEqual(result.status_code,201,result.text)
        with Session(self.engine) as db:
            row=db.scalar(select(ManualRouteKnowledge).where(ManualRouteKnowledge.owner_id==self.uid))
            self.assertEqual(json.loads(row.payload_json)['waypoints'],codes)
            self.assertEqual(len(json.loads(row.payload_json)['legs']),1000)
            self.assertGreater(len(row.payload_json.encode()),65535)
            self.assertEqual(db.scalar(select(func.count()).select_from(TrainGpsRecording)),0)
        self.assertEqual(self.save(waypoints=['AFW']*1002,routes=['1000']*1001).status_code,422)

    def test_mysql_storage_supports_long_routes_and_widens_old_text_once(self):
        from sqlalchemy.dialects import mysql
        from sqlalchemy import Text
        from unittest.mock import Mock,patch
        from lokzeitleiste.manual_route_knowledge import ensure_storage
        self.assertEqual(ManualRouteKnowledge.__table__.c.payload_json.type.compile(dialect=mysql.dialect()),'MEDIUMTEXT')
        connection=Mock();connection.dialect.name='mysql'
        with patch('lokzeitleiste.manual_route_knowledge.inspect') as schema:
            schema.return_value.get_columns.return_value=[dict(name='payload_json',type=mysql.TEXT(collation='utf8mb4_unicode_ci'))]
            ensure_storage(connection)
            self.assertIn('MEDIUMTEXT NOT NULL',str(connection.execute.call_args.args[0]))
            connection.execute.reset_mock()
            schema.return_value.get_columns.return_value=[dict(name='payload_json',type=mysql.MEDIUMTEXT())]
            ensure_storage(connection);connection.execute.assert_not_called()
        connection.dialect.name='sqlite';ensure_storage(connection);connection.execute.assert_not_called()

    def test_saved_route_listing_and_owned_edit_with_stale_revision(self):
        response=self.save();self.assertEqual(response.status_code,201,response.text)
        rows=self.client.get('/api/v1/tf/route-knowledge/manual',headers=self.headers).json()['items']
        self.assertEqual(len(rows),1);record=rows[0]
        self.assertEqual(record['waypoints'],['AFW','AFR']);self.assertEqual(record['from_code'],'AFW');self.assertEqual(record['to_code'],'AFR')
        path='/api/v1/tf/route-knowledge/manual/'+str(record['id'])
        updated={**self.payload,'waypoints':['AFW','AFR','AFW'],'routes':['1000','1000'],'expected_sha256':record['revision']}
        result=self.client.put(path,json=updated,headers=self.headers);self.assertEqual(result.status_code,200,result.text)
        saved=result.json()['saved_routes'];self.assertEqual(len(saved),1);self.assertEqual(saved[0]['id'],record['id']);self.assertEqual(saved[0]['waypoints'],updated['waypoints']);self.assertNotEqual(saved[0]['revision'],record['revision'])
        self.assertEqual(self.client.put(path,json=updated,headers=self.headers).status_code,409)
        self.assertEqual(self.client.put(path,json={**updated,'expected_sha256':saved[0]['revision'],'valid_until':(maximum(today())+timedelta(days=1)).isoformat()},headers=self.headers).status_code,422)
        self.assertEqual(self.client.get('/api/v1/tf/route-knowledge/manual',headers=self.headers).json()['items'][0]['waypoints'],updated['waypoints'])
        other=test_api.ApiFlowTest.create_tf(self,'787120','EDIT-OTHER').json()['id']
        token=self.client.post('/api/v1/account/login',json={'username':'787120','password':'tf-secret-12345'}).json()['access_token']
        outsider={'Authorization':'Bearer '+token}
        self.assertEqual(self.client.get('/api/v1/tf/route-knowledge/manual',headers=outsider).json()['items'],[])
        self.assertEqual(self.client.put(path,json={**updated,'expected_sha256':saved[0]['revision']},headers=outsider).status_code,404)
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(func.count()).select_from(ManualRouteKnowledge)),1)

    def test_edit_cannot_overwrite_a_different_saved_route(self):
        self.assertEqual(self.save().status_code,201)
        self.assertEqual(self.save(waypoints=['AFR','AFW']).status_code,201)
        rows=self.client.get('/api/v1/tf/route-knowledge/manual',headers=self.headers).json()['items']
        original=next(row for row in rows if row['from_code']=='AFW')
        changed={**self.payload,'waypoints':['AFR','AFW'],'expected_sha256':original['revision']}
        result=self.client.put('/api/v1/tf/route-knowledge/manual/'+str(original['id']),json=changed,headers=self.headers)
        self.assertEqual(result.status_code,409,result.text)
        after=self.client.get('/api/v1/tf/route-knowledge/manual',headers=self.headers).json()['items']
        self.assertEqual(after,rows)
