import json
import unittest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_gps
from lokzeitleiste.models import TrainGpsRecording, User

class GpsDemoTest(unittest.TestCase):
    setUp=test_gps.RecordingTest.setUp
    tearDown=test_gps.RecordingTest.tearDown
    path=test_gps.RecordingTest.path
    save=test_gps.RecordingTest.save

    def test_own_completed_recordings_only_and_read_only(self):
        path,saved=self.save()
        self.assertEqual(saved.status_code,200,saved.text)
        self.save(ended=False)
        self.save(points=[],manual_stops=[dict(key='manual-'+str(test_gps.BASE),start=test_gps.BASE,end=test_gps.BASE+1000)])
        with Session(self.engine) as db:
            admin=db.scalar(select(User).where(User.username=='admin'))
            foreign=TrainGpsRecording(owner_id=admin.id,journey_id=str(uuid4()),payload_json=json.dumps(dict(train_number='PRIVATE',points=test_gps.points(),ended=True)),revision=1)
            db.add(foreign);db.commit();foreign_id=foreign.journey_id
        listing=self.driver.get('/api/v1/tf/gps-recordings')
        self.assertEqual(listing.status_code,200,listing.text)
        data=listing.json();self.assertEqual(len(data['items']),1)
        self.assertEqual(data['items'][0]['journey_id'],path.rsplit('/',1)[1])
        self.assertNotIn('points',data['items'][0]);self.assertIsNone(data['next_offset'])
        self.assertEqual(self.driver.get(path).json(),saved.json())
        self.assertEqual(self.driver.get('/api/v1/tf/gps/'+foreign_id).status_code,404)
        self.assertEqual(self.client.get('/api/v1/tf/gps-recordings').status_code,403)
        self.assertEqual(self.driver.get('/api/v1/tf/gps-recordings?offset=-1').status_code,422)
        self.assertEqual(self.driver.get('/tf/gps-demo').status_code,200)

    def test_bounded_pages_without_duplicates(self):
        path,saved=self.save()
        payload=json.dumps(dict(train_number='123',points=test_gps.points(seconds=5),ended=True))
        with Session(self.engine) as db:
            owner=db.scalar(select(TrainGpsRecording.owner_id).where(TrainGpsRecording.journey_id==path.rsplit('/',1)[1]))
            db.add_all([TrainGpsRecording(owner_id=owner,journey_id=str(uuid4()),payload_json=payload,revision=1) for _ in range(100)]);db.commit()
        first=self.driver.get('/api/v1/tf/gps-recordings').json()
        second=self.driver.get('/api/v1/tf/gps-recordings?offset='+str(first['next_offset'])).json()
        self.assertEqual(len(first['items']),100);self.assertEqual(len(second['items']),1)
        self.assertEqual(len({row['journey_id'] for row in first['items']+second['items']}),101)
        self.assertIsNone(second['next_offset'])
