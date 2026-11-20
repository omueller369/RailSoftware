"""Deletion/compaction never bypass ownership, coverage, revisions or explicit consent."""
import json,math,unittest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_manual_route_knowledge as manual
import test_api
from lokzeitleiste.models import TrainGpsRecording,ManualRouteKnowledge,GpsDemoShare,RouteKnowledgeEntry
from lokzeitleiste.route_knowledge_import import digest,packed
from lokzeitleiste.route_knowledge_mapping import match
from lokzeitleiste.manual_route_parallel import trace

class ManualCompactionTest(unittest.TestCase):
    setUp=manual.ManualRouteTest.setUp
    tearDown=manual.ManualRouteTest.tearDown
    save=manual.ManualRouteTest.save
    listing=manual.ManualRouteTest.listing
    def recording(self,*,ended=True,off_route=False):
        mapped=match(dict(route_number='1000',from_code='AFW',to_code='AFR'))
        positions=[p for path in trace('1000',mapped['from_m'],mapped['to_m']) for p in path]
        points=[dict(t=1795165200000+i*5000,lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*y)))),lon=x*360-180,accuracy=5,speed=10) for i,(x,y) in enumerate(positions)]
        if off_route:
            for p in points:p.update(lat=52,lon=13)
        self.journey=str(uuid4());self.raw=dict(train_number='TEST',points=points,ended=ended,manual_stops=[],stop_edits={},stations={},reasons={},start_station='AFW',end_station='AFR',selection=[])
        with Session(self.engine) as db:
            row=TrainGpsRecording(owner_id=self.uid,journey_id=self.journey,payload_json=packed(self.raw),revision=3);db.add(row);db.commit();self.record_id=row.id
        self.link=dict(journey_id=self.journey,expected_revision=3,expected_sha256=digest(packed(self.raw)))
        return self.link
    def linked(self,**options):
        self.recording(**options);result=self.save(source_gps=self.link);self.assertEqual(result.status_code,201,result.text);return result.json()['saved_routes'][0]
    def path(self,row):return '/api/v1/tf/route-knowledge/manual/'+str(row['id'])
    def gps(self):
        with Session(self.engine) as db:
            row=db.get(TrainGpsRecording,self.record_id);return row.revision,json.loads(row.payload_json)
    def test_manual_delete_preserves_csv_and_raw_gps_and_needs_current_revision(self):
        row=self.linked();before=self.gps()
        original=packed(dict(section='Protected CSV',route_number='1000',from_code='AFW',to_code='AFR',status='streckenkundig',valid_until='2030-01-01',acquired_since='',acquisition_trips=''))
        with Session(self.engine) as db:db.add(RouteKnowledgeEntry(owner_id=self.uid,section_key=digest('protected'),content_sha256=digest(original),source_json=original,source_sha256='a'*64));db.commit()
        self.assertEqual(self.client.delete(self.path(row)+'?expected_sha256='+'0'*64,headers=self.headers).status_code,409)
        r=self.client.delete(self.path(row)+'?expected_sha256='+row['revision'],headers=self.headers)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['saved_routes'],[]);self.assertEqual(self.gps(),before)
        self.assertEqual(self.listing()[0]['section'],'Protected CSV')
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(RouteKnowledgeEntry)).source_json,original)
    def test_verified_separate_confirmation_removes_only_raw_points_and_shared_snapshot(self):
        row=self.linked();before=self.gps();path=self.path(row)+'/gps-compaction'
        with Session(self.engine) as db:db.add(GpsDemoShare(recording_id=self.record_id,owner_id=self.uid,payload_json=packed(self.raw),source_revision=3));db.commit()
        check=self.client.get(path+'?expected_sha256='+row['revision'],headers=self.headers);self.assertEqual(check.status_code,200,check.text);self.assertTrue(check.json()['eligible']);self.assertEqual(self.gps(),before)
        no=self.client.post(path,json=dict(expected_sha256=row['revision'],confirmed=False),headers=self.headers);self.assertEqual(no.status_code,422);self.assertEqual(self.gps(),before)
        yes=self.client.post(path,json=dict(expected_sha256=row['revision'],confirmed=True),headers=self.headers);self.assertEqual(yes.status_code,200,yes.text)
        stored=yes.json()['saved_routes'][0];self.assertEqual(stored['waypoints'],['AFW','AFR']);self.assertTrue(stored['source_gps']['points_removed']);self.assertNotEqual(stored['revision'],row['revision']);revision,payload=self.gps();self.assertEqual(revision,4);self.assertEqual(payload['points'],[]);self.assertEqual(payload['stations'],self.raw['stations']);self.assertTrue(payload['ended'])
        with Session(self.engine) as db:self.assertIsNone(db.get(GpsDemoShare,self.record_id));self.assertIsNotNone(db.get(ManualRouteKnowledge,row['id']))
        stale=self.client.put('/api/v1/tf/gps/'+self.journey,json={**self.raw,'expected_revision':3},headers=self.headers);self.assertEqual(stale.status_code,409,stale.text)
        self.assertEqual(self.client.get('/api/v1/tf/gps/'+self.journey,headers=self.headers).json()['points'],[])
    def test_incomplete_route_does_not_remove_gps(self):
        row=self.linked(off_route=True);before=self.gps();r=self.client.post(self.path(row)+'/gps-compaction',json=dict(expected_sha256=row['revision'],confirmed=True),headers=self.headers);self.assertEqual(r.status_code,409,r.text);self.assertEqual(self.gps(),before)
    def test_source_change_and_path_change_block_compaction(self):
        row=self.linked();path=self.path(row)+'/gps-compaction'
        with Session(self.engine) as db:record=db.get(TrainGpsRecording,self.record_id);record.revision+=1;db.commit()
        self.assertEqual(self.client.post(path,json=dict(expected_sha256=row['revision'],confirmed=True),headers=self.headers).status_code,409)
        with Session(self.engine) as db:record=db.get(TrainGpsRecording,self.record_id);record.revision=3;db.commit()
        update=self.client.put(self.path(row),json={**self.payload,'waypoints':['AFR','AFW'],'expected_sha256':row['revision']},headers=self.headers);self.assertEqual(update.status_code,200,update.text)
        changed=update.json()['saved_routes'][0];self.assertEqual(self.client.get(path+'?expected_sha256='+changed['revision'],headers=self.headers).status_code,409);self.assertGreater(len(self.gps()[1]['points']),0)
    def test_owned_routes_and_gps_link_cannot_cross_tf(self):
        row=self.linked();own=self.client.get('/api/v1/tf/route-knowledge/manual/gps-source/'+self.journey,headers=self.headers);self.assertEqual(own.status_code,200);self.assertEqual(own.json()['item']['sha256'],self.link['expected_sha256']);other=test_api.ApiFlowTest.create_tf(self,'787120','COMPACT-OTHER').json()['id'];token=self.client.post('/api/v1/account/login',json={'username':'787120','password':'tf-secret-12345'}).json()['access_token'];headers={'Authorization':'Bearer '+token}
        self.assertEqual(self.client.get('/api/v1/tf/route-knowledge/manual/gps-source/'+self.journey,headers=headers).status_code,404)
        self.assertEqual(self.client.delete(self.path(row)+'?expected_sha256='+row['revision'],headers=headers).status_code,404)
        self.assertEqual(self.client.post(self.path(row)+'/gps-compaction',json=dict(expected_sha256=row['revision'],confirmed=True),headers=headers).status_code,404)
        self.assertEqual(self.client.post('/api/v1/tf/route-knowledge/manual',json={**self.payload,'source_gps':self.link},headers=headers).status_code,404)
    def test_running_or_stale_source_cannot_be_linked(self):
        self.recording(ended=False);self.assertEqual(self.save(source_gps=self.link).status_code,409)
        self.assertEqual(self.save(source_gps={**self.link,'expected_sha256':'0'*64}).status_code,409)

if __name__=='__main__':unittest.main()
