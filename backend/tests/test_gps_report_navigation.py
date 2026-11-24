# Ein GPS-Link darf nur zum eigenen Bericht führen.
import json,unittest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_train_journeys
from lokzeitleiste.models import TrainGpsRecording,User,DutyReport

class GpsReportNavigationTest(unittest.TestCase):
    setUp=test_train_journeys.TrainJourneysTest.setUp
    tearDown=test_train_journeys.TrainJourneysTest.tearDown
    payload=test_train_journeys.TrainJourneysTest.payload
    create=test_train_journeys.TrainJourneysTest.create
    train=test_train_journeys.TrainJourneysTest.train
    event=test_train_journeys.TrainJourneysTest.event
    data=test_train_journeys.TrainJourneysTest.data
    def test_link_resolves_own_report_without_points_and_rejects_foreign(self):
        report=self.create(self.data());jid=report['train_journeys'][0]['id']
        with Session(self.engine) as db:
            owner=db.scalar(select(User.id).where(User.username=='787100'));db.add(TrainGpsRecording(owner_id=owner,journey_id=jid,payload_json=json.dumps({'points':[]}),revision=1));db.commit()
        url='/api/v1/tf/gps/'+jid+'/work-report';r=self.driver.get(url);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json(),{'report_id':report['id'],'client_id':report['client_id']});self.assertNotIn('points',r.text)
        self.assertEqual(self.driver.get('/api/v1/tf/gps/'+str(uuid4())+'/work-report').status_code,404)
        with Session(self.engine) as db:
            other=User(username='787555',role='tf',active=True,password_hash='unused');db.add(other);db.flush();db.scalar(select(TrainGpsRecording)).owner_id=other.id;db.commit()
        self.assertEqual(self.driver.get(url).status_code,404)
