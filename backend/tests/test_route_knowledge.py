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
