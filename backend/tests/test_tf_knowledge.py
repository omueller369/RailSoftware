import csv,io,unittest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.orm import Session
import test_stations
from lokzeitleiste.main import app
from lokzeitleiste.models import TfLocationKnowledge,TfRollingStockKnowledge
from lokzeitleiste.tf_knowledge import parse

def raw(kind='places',rows=None,trailing=True):
    headers=['Bahnhof','DS100','Kundig bis'] if kind=='places' else ['Baureihe','Gültig bis']
    rows=rows if rows is not None else ([['Test Bahnhof','AA G','2025-01-01'],['Test Zwei','AAG','0000-00-00']] if kind=='places' else [['0186','2029-10-06'],['193','2029-10-25']])
    f=io.StringIO(newline='');w=csv.writer(f,delimiter=';');w.writerow(headers+([''] if trailing else []));w.writerows([r+([''] if trailing else []) for r in rows]);return f.getvalue().encode('utf-8-sig')
class TfKnowledgeTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown
    def preview(self,kind,data=None,client=None):return (client or self.driver).post('/api/v1/tf/knowledge/'+kind+'/preview',files={'file':('Inventar.csv',data or raw(kind),'text/csv')})
    def apply(self,kind,preview,data=None,client=None,**changes):
        form=dict(confirmed='true',owner_token=preview['owner_token'],expected_sha256=preview['summary']['file_sha256']);form.update(changes)
        return (client or self.driver).post('/api/v1/tf/knowledge/'+kind,data=form,files={'file':('Inventar.csv',data or raw(kind),'text/csv')})
    def count(self):
        with Session(self.engine) as db:return tuple(db.scalar(select(func.count()).select_from(m)) for m in [TfLocationKnowledge,TfRollingStockKnowledge])
    def test_both_exact_schemas_readonly_preview_confirmation_and_idempotence(self):
        for kind,count in [('places',(2,0)),('classes',(2,2))]:
            p=self.preview(kind);self.assertEqual(p.status_code,200,p.text);p=p.json();self.assertEqual(len(p['items']),2)
            self.assertEqual(self.apply(kind,p,confirmed='false').status_code,422)
            r=self.apply(kind,p);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.count(),count)
            self.assertEqual(self.apply(kind,p).json()['summary']['added'],0)
        items=self.driver.get('/api/v1/tf/knowledge/classes').json()['items'];self.assertEqual(items[0]['series'],'0186')
        places=self.driver.get('/api/v1/tf/knowledge/places').json()['items'];self.assertEqual(places[0]['ds100'],'AA G');self.assertEqual(places[1]['ds100'],'AAG');self.assertEqual(places[1]['known_until'],'0000-00-00')
    def test_owner_isolation_and_hash_binding_and_no_overwrite(self):
        p=self.preview('places').json();self.assertEqual(self.apply('places',p,owner_token='bad').status_code,409);self.assertEqual(self.apply('places',p,expected_sha256='bad').status_code,409);self.assertEqual(self.count(),(0,0))
        self.create_tf('787101','P-INV-OTHER');other=TestClient(app,base_url='https://testserver');self.staff_clients.append(other);other.post('/api/v1/account/login',json={'username':'787101','password':'tf-secret-12345'})
        self.assertEqual(self.apply('places',p,client=other).status_code,409);self.assertEqual(self.apply('places',p).status_code,200)
        self.assertEqual(other.get('/api/v1/tf/knowledge/places').json()['items'],[]);self.assertEqual(self.client.get('/api/v1/tf/knowledge/places').status_code,403)
        changed=raw(rows=[['Umbenannt','AA G','2030-01-01']]);p=self.preview('places',changed).json();self.assertEqual(p['summary']['conflicts'],1);self.assertEqual(self.apply('places',p,changed).json()['summary']['added'],0)
        self.assertEqual(self.driver.get('/api/v1/tf/knowledge/places').json()['items'][0]['station_name'],'Test Bahnhof')
    def test_invalid_and_wrong_schema_and_dates_rejected_atomically(self):
        self.assertEqual(self.preview('places',raw('classes')).status_code,422)
        self.assertEqual(self.preview('classes',raw('classes',[['193','2027-02-30']])).status_code,422)
        self.assertEqual(self.preview('places',raw(rows=[['A','AAA','2027-01-01'],['B','AAA','2028-01-01']])).status_code,422)
        self.assertEqual(self.preview('places',raw()+b'x;y;z;NONEMPTY\n').status_code,422);self.assertEqual(self.count(),(0,0))
        self.assertEqual(len(parse(raw(trailing=False),'places')['records']),2)
