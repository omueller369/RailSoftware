# Regressionstests für Streckenkenntnisse und Referenzgeometrie.
import json
import unittest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_gps
from lokzeitleiste.models import TrainGpsRecording, User
from lokzeitleiste.route_knowledge import route_segments
from lokzeitleiste.gps_analysis import analyse, confirmed_departures

class RouteKnowledgeTest(unittest.TestCase):
    setUp=test_gps.RecordingTest.setUp
    tearDown=test_gps.RecordingTest.tearDown
    path=test_gps.RecordingTest.path
    save=test_gps.RecordingTest.save

    def test_timestamps_are_preserved_without_changing_geometry_or_originals(self):
        points=[dict(p,lon=13+i*.001) for i,p in enumerate(test_gps.points(40))]
        points[4]['break_before']=True;points[6]['accuracy']=100
        original=json.loads(json.dumps(points))
        timed=route_segments(points,timed=True)
        self.assertEqual([[p[:2] for p in line] for line in timed],route_segments(points))
        dates={p['t'] for p in points}
        self.assertTrue(all(p[2] in dates for line in timed for p in line))
        self.assertEqual(points,original)
        path,saved=self.save(points=points)
        self.assertEqual(saved.status_code,200)
        item=self.driver.get('/api/v1/tf/route-knowledge?dates=1').json()['items'][0]
        self.assertEqual(item['timed_segments'],timed)
        self.assertNotIn('segments',item,'Timed requests avoid downloading duplicate coordinate arrays')
        self.assertEqual(route_segments(test_gps.points(15),timed=True),[],'Stationary points do not invent a travelled line')

    def test_poland_reference_assets_and_invalid_paths(self):
        for path in ['/tf/poland-rail.js','/tf/poland-rail-data/overview.js']:
            response=self.driver.get(path)
            self.assertEqual(response.status_code,200,path)
            self.assertIn('javascript',response.headers['content-type'])
        self.assertEqual(self.driver.get('/tf/poland-rail-data/tile-999-999.js').status_code,404)
        self.assertEqual(self.driver.get('/tf/poland-rail-data/not-a-tile.js').status_code,404)

    def test_public_network_assets_and_gzip(self):
        plain=self.driver.get('/tf/rail-network-data.js?v=0.26.61',headers={'Accept-Encoding':'identity'})
        compressed=self.driver.get('/tf/rail-network-data.js?v=0.26.61',headers={'Accept-Encoding':'gzip'})
        disabled=self.driver.get('/tf/rail-network-data.js',headers={'Accept-Encoding':'gzip;q=0'})
        self.assertEqual(plain.status_code,200)
        self.assertEqual(compressed.headers.get('content-encoding'),'gzip')
        self.assertEqual(compressed.content,plain.content)
        self.assertNotIn('content-encoding',disabled.headers)
        self.assertIn('Accept-Encoding',compressed.headers['vary'])
        self.assertEqual(self.driver.get('/tf/rail-network.js').status_code,200)
        self.assertEqual(self.driver.get('/tf/route-coverage.js').status_code,200)

    def test_own_tracks_pagination_and_access(self):
        path,saved=self.save(points=[dict(p,lon=13+i*.001) for i,p in enumerate(test_gps.points(15))])
        self.assertEqual(saved.status_code,200)
        payload=json.dumps(dict(points=[dict(p,lon=13+i*.001) for i,p in enumerate(test_gps.points(15))]))
        with Session(self.engine) as db:
            owner=db.scalar(select(TrainGpsRecording.owner_id).where(TrainGpsRecording.journey_id==path.rsplit('/',1)[1]))
            foreign=User(username='route-other',role='tf',password_hash='unused');db.add(foreign);db.flush()
            db.add(TrainGpsRecording(owner_id=foreign.id,journey_id=str(uuid4()),payload_json=payload,revision=1))
            db.add_all([TrainGpsRecording(owner_id=owner,journey_id=str(uuid4()),payload_json=payload,revision=1) for _ in range(20)]);db.commit()
        first=self.driver.get('/api/v1/tf/route-knowledge').json()
        second=self.driver.get('/api/v1/tf/route-knowledge?offset='+str(first['next_offset'])).json()
        self.assertEqual(first['owner_id'],owner);self.assertEqual(len(first['items']),20);self.assertEqual(len(second['items']),1)
        self.assertEqual(len({r['journey_id'] for r in first['items']+second['items']}),21)
        self.assertIsNone(second['next_offset']);self.assertTrue(first['items'][0]['segments'])
        self.assertEqual(self.client.get('/api/v1/tf/route-knowledge').status_code,403)
        self.assertEqual(self.driver.get('/api/v1/tf/route-knowledge?offset=-1').status_code,422)
        self.assertEqual(self.driver.get('/tf/streckenkenntnisse').status_code,200)

    def test_gaps_pause_bad_fixes_and_foreign_positions_not_travelled(self):
        points=[dict(p,lon=13+i*.001) for i,p in enumerate(test_gps.points(40))]
        points[2]['break_before']=True;points[4]['accuracy']=100;points[6]['lat']=60
        lines=route_segments(points)
        self.assertEqual(len(lines),3)
        self.assertEqual(lines[0],[[52,13],[52,13.001]])
        self.assertEqual(lines[1],[[52,13.002],[52,13.003]])
        points=[dict(p,lon=13+i*.001) for i,p in enumerate(test_gps.points(15))]
        points[2]['t']+=60000;points[3]['t']+=60000
        self.assertEqual(len(route_segments(points)),2)

    def test_short_pause_survives_sync_and_cannot_create_stop_or_departure(self):
        points=test_gps.points(125)
        points[13]['break_before']=True
        self.assertEqual([r['kind'] for r in analyse(points)['rows']],['Start','Ende'])
        path,saved=self.save(points=points)
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertTrue(self.driver.get(path).json()['points'][13]['break_before'])
        motion=[dict(p,lon=13+i*.001,speed=10) for i,p in enumerate(test_gps.points(15))]
        motion[2]['break_before']=True
        self.assertEqual(list(confirmed_departures(motion)),[])
