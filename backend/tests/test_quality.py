# Regressionstests für Prüfabläufe, Ablaufübersicht und Betriebsstatus.
# Die Prüfmodule dürfen weder fremde TF-Bestände lesen noch Entscheidungen auf veraltete Daten anwenden.
import hashlib,json,unittest,zipfile,tempfile
from datetime import date,timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_api
from lokzeitleiste.models import (User,DutyReport,WorkEntry,WorkMonth,ReportReviewEvent,StationCoordinateContribution,
 RailwayStation,RailwayStationCoordinates,TfLocationKnowledge,BackupRun)
from lokzeitleiste.quality import review_view
from lokzeitleiste.backups import build,verify,execute
from lokzeitleiste.location_knowledge import today
class QualityTest(unittest.TestCase):
    def setUp(self):
        test_api.ApiFlowTest.setUp(self)
        self.client.post('/api/v1/admin/login',json={'username':'admin','password':'admin-secret-12345'})
        self.uid=test_api.ApiFlowTest.create_tf(self,'787119','QUALITY').json()['id']
        token=self.client.post('/api/v1/account/login',json={'username':'787119','password':'tf-secret-12345'}).json()['access_token'];self.headers={'Authorization':'Bearer '+token}
    def tearDown(self):test_api.ApiFlowTest.tearDown(self)
    def test_expiry_is_owned_and_never_changes_original_records(self):
        with Session(self.engine) as db:
            for i,(days,expected) in enumerate([(-1,'expired'),(5,'expiring'),(150,'valid')]):db.add(TfLocationKnowledge(owner_id=self.uid,identity_key=str(i)*64,station_name='Ort '+str(i),ds100='Q'+str(i),known_until=(today()+timedelta(days=days)).isoformat(),content_sha256='a'*64))
            db.add(TfLocationKnowledge(owner_id=self.uid,identity_key='f'*64,station_name='Unklar',ds100='Q9',known_until='',content_sha256='b'*64));db.commit()
        r=self.client.get('/api/v1/tf/quality/knowledge',headers=self.headers);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['counts'],dict(valid=1,expiring=1,expired=1,missing=1));self.assertEqual(r.json()['owner_id'],self.uid)
        own=self.client.get('/api/v1/admin/quality/knowledge/'+str(self.uid));self.assertEqual(own.status_code,200,own.text);self.assertEqual(own.json()['counts'],r.json()['counts'])
        token=self.client.post('/api/v1/account/login',json={'username':'787119','password':'tf-secret-12345'}).json()['access_token'];self.assertEqual(self.client.get('/api/v1/admin/quality/knowledge/'+str(self.uid),headers={'Authorization':'Bearer '+token}).status_code,401)
    def report(self):
        # Für den Prüfablauf genügt ein unveränderter Bericht; die bestehenden Erfassungstests prüfen dessen Fachvalidierung.
        with Session(self.engine) as db:
            month=WorkMonth(tf_user_id=self.uid,year=2026,month=11);db.add(month);db.flush()
            entry=WorkEntry(work_month_id=month.id,client_id='c'*36,entry_date=date(2026,11,23),start_time='08:00',end_time='16:00',kind='Dienstschicht',pause_minutes=0,guest_minutes=0,note='');db.add(entry);db.flush()
            r=DutyReport(tf_user_id=self.uid,entry_id=entry.id,client_id='a'*36,payload_json=json.dumps(dict(start_at='2026-11-23T08:00',end_at='2026-11-23T16:00',_train_revision=0)));db.add(r);db.commit();return r.id,review_view(db,r)
    def test_review_requires_review_before_approval_and_checks_payload(self):
        rid,state=self.report();url='/api/v1/admin/work-reports/'+str(rid)+'/review';body=dict(state='approved',expected_version=state['version'],expected_revision=state['revision'],expected_sha256=state['payload_sha256'],comment='Geprüft')
        self.assertEqual(self.client.post(url,json=body).status_code,409)
        body['state']='in_review';r=self.client.post(url,json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['state'],'in_review');self.assertEqual(self.client.post(url,json=body).status_code,409)
        body.update(state='approved',expected_revision=r.json()['revision']);r=self.client.post(url,json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(len(r.json()['history']),2)
        with Session(self.engine) as db:
            report=db.get(DutyReport,rid);p=json.loads(report.payload_json);p['_train_revision']=1;report.payload_json=json.dumps(p);db.commit();self.assertEqual(review_view(db,report)['state'],'received')
    def test_coordinate_revert_preserves_audit_and_rejects_stale_tokens(self):
        with Session(self.engine) as db:
            db.add(RailwayStation(code='QXX',name='Prüfort'));db.flush();point=RailwayStationCoordinates(code='QXX',catalog_name='Prüfort',latitude=51,longitude=13,source_name='TF-GPS',source_url='/tf/arbeitsbericht',source_date='2026-11',max_spread_m=0);db.add(point);db.flush()
            from lokzeitleiste.station_coordinate_contributions import current
            after=current(db.get(RailwayStation,'QXX'),point)['coordinate'];row=StationCoordinateContribution(request_id='b'*36,owner_id=self.uid,code='QXX',proposal_json=json.dumps(dict(latitude=51,longitude=13)),before_json=None,after_json=json.dumps(after));db.add(row);db.commit();rid=row.id
        r=self.client.get('/api/v1/admin/quality/coordinates');self.assertEqual(r.status_code,200,r.text);item=next(x for x in r.json()['items'] if x['id']==rid);url='/api/v1/admin/quality/coordinates/'+str(rid)
        body=dict(decision='reject',comment='Falscher Ort',expected_token='0'*64);self.assertEqual(self.client.post(url,json=body).status_code,409);body['expected_token']=item['current']['token'];r=self.client.post(url,json=body);self.assertEqual(r.status_code,200,r.text)
        with Session(self.engine) as db:self.assertIsNone(db.get(RailwayStationCoordinates,'QXX'));self.assertEqual(len(list(db.scalars(select(StationCoordinateContribution)))),2)
        self.assertEqual(self.client.get('/api/v1/admin/quality/coordinates').json()['total'],0)
    def test_backup_restores_isolated_database_and_detects_corruption(self):
        root=Path(self.documents.name);(root/'TF').mkdir(exist_ok=True);(root/'TF'/'probe.txt').write_text('Sicherung: äöü')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'backup.zip';build(path,self.engine,root);result=verify(path);self.assertGreater(result['tables'],20);self.assertEqual(result['files'],1)
            bad=Path(tmp)/'bad.zip'
            with zipfile.ZipFile(path) as source,zipfile.ZipFile(bad,'w') as target:
                for name in source.namelist():target.writestr(name,'Beschädigt'.encode() if name=='files/TF/probe.txt' else source.read(name))
            with self.assertRaises(ValueError):verify(bad)
        with Session(self.engine) as db:db.add(BackupRun(id='a'*32,state='running'));db.commit()
        execute('a'*32,self.engine,root)
        with Session(self.engine) as db:self.assertEqual(db.get(BackupRun,'a'*32).state,'verified')
if __name__=='__main__':unittest.main()
