import csv,io,json,unittest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import test_stations
from lokzeitleiste.main import app
from lokzeitleiste.models import RouteKnowledgeEntry,RouteKnowledgeImport,TrainGpsRecording,TfProfile
from lokzeitleiste.route_knowledge_import import parse_csv,HEADERS,MAX_BYTES

ROWS=[['A - B','1000','streckenkundig','2027-02-03','-','-','AAA','BBB'],['B - C','2000','abgelaufen','0000-00-00','-','-','BBB','CCC'],['Eigenes Ziel','0','wird erworben','','2025-06-03','4','X.001','X.002']]
def csv_bytes(rows=ROWS):
    stream=io.StringIO(newline='');writer=csv.writer(stream,delimiter=';');writer.writerow(HEADERS);writer.writerows(rows);return stream.getvalue().encode('utf-8-sig')

class RouteKnowledgeImportTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown
    path='/api/v1/tf/route-knowledge/imports'
    def preview(self,raw=None,client=None):return (client or self.driver).post(self.path+'/preview',files={'file':('Kenntnisse.csv',raw if raw is not None else csv_bytes(),'text/csv')})
    def apply(self,preview,raw=None,client=None,**changes):
        form=dict(owner_token=preview['owner_token'],expected_sha256=preview['summary']['file_sha256'],confirmed='true');form.update(changes)
        return (client or self.driver).post(self.path,data=form,files={'file':('Kenntnisse.csv',raw if raw is not None else csv_bytes(),'text/csv')})
    def counts(self):
        with Session(self.engine) as db:return tuple(db.scalar(select(func.count()).select_from(model)) for model in [RouteKnowledgeEntry,RouteKnowledgeImport,TrainGpsRecording])
    def test_preview_apply_preserves_all_fields_and_is_idempotent_without_gps(self):
        response=self.preview();self.assertEqual(response.status_code,200,response.text);preview=response.json()
        self.assertEqual(preview['identity']['tf_number'],'787100');self.assertEqual(preview['summary']['added'],3);self.assertEqual(preview['summary']['unknown_dates'],2)
        self.assertEqual(self.counts(),(0,0,0));self.assertIn('map_matches',preview['summary'])
        saved=self.apply(preview);self.assertEqual(saved.status_code,200,saved.text);self.assertEqual(self.counts(),(3,1,0))
        items=self.driver.get(self.path).json()['items']
        self.assertEqual([[row[k] for k in ['section','route_number','status','valid_until','acquired_since','acquisition_trips','from_code','to_code']] for row in items],ROWS)
        again=self.apply(preview);self.assertTrue(all('map_match' in row for row in items));self.assertEqual(again.status_code,200);self.assertEqual(again.json()['summary']['added'],0);self.assertEqual(again.json()['summary']['existing'],3);self.assertEqual(self.counts(),(3,1,0))
    def test_target_identity_and_file_change_and_confirmation_are_authoritative(self):
        preview=self.preview().json()
        self.assertEqual(self.apply(preview,confirmed='false').status_code,422)
        self.assertEqual(self.apply(preview,expected_sha256='0'*64).status_code,409)
        self.assertEqual(self.apply(preview,owner_token='0'*64).status_code,409)
        with Session(self.engine) as db:db.get(TfProfile,self.tf).last_name='Neuer Name';db.commit()
        self.assertEqual(self.apply(preview).status_code,409)
        self.assertEqual(self.counts(),(0,0,0))
    def test_foreign_account_never_reads_or_applies_the_other_owner_preview(self):
        self.create_tf('787101','P-CSV-OTHER')
        other=TestClient(app,base_url='https://testserver');self.staff_clients.append(other);other.post('/api/v1/account/login',json={'username':'787101','password':'tf-secret-12345'})
        preview=self.preview().json();self.assertEqual(self.apply(preview,client=other).status_code,409)
        self.assertEqual(self.apply(preview).status_code,200)
        self.assertEqual(other.get(self.path).json()['items'],[])
        own=self.preview(client=other).json();self.assertEqual(own['summary']['added'],3);self.assertEqual(self.apply(own,client=other).status_code,200)
        self.assertEqual(len(self.driver.get(self.path).json()['items']),3);self.assertEqual(self.counts(),(6,2,0))
        self.assertEqual(self.client.get(self.path).status_code,403)
        self.assertEqual(self.client.post(self.path+'/preview',files={'file':('x.csv',csv_bytes())}).status_code,403)
    def test_existing_conflicts_preserved_new_rows_added_and_formatting_deduplicated(self):
        self.apply(self.preview().json())
        changed=[list(ROWS[0]),['Neu','3000','streckenkundig','2028-01-01','-','-','AAA','CCC']];changed[0][2]='abgelaufen'
        raw=csv_bytes(changed);preview=self.preview(raw).json();self.assertEqual(preview['summary']['conflicts'],1);self.assertEqual(preview['summary']['added'],1)
        self.assertEqual(self.apply(preview,raw).status_code,200)
        items=self.driver.get(self.path).json()['items'];self.assertEqual(len(items),4);self.assertEqual(items[0]['status'],'streckenkundig')
        alternate=csv_bytes().replace(b'\r\n',b'\n');self.assertEqual(self.preview(alternate).json()['summary']['existing'],3);self.assertEqual(self.counts()[-1],0)
    def test_invalid_file_is_rejected_before_any_write(self):
        bad=[list(ROWS[0]),list(ROWS[1])];bad[1][3]='2027-02-30'
        self.assertEqual(self.preview(csv_bytes(bad)).status_code,422)
        self.assertEqual(self.preview(b'wrong;headers\na;b').status_code,422)
        self.assertEqual(self.preview(b'x'*(MAX_BYTES+1)).status_code,413)
        self.assertEqual(self.counts(),(0,0,0))
    def test_parser_duplicate_and_conflict_and_literal_placeholders(self):
        parsed=parse_csv(csv_bytes([ROWS[0],ROWS[0]]));self.assertEqual(parsed['source_rows'],2);self.assertEqual(parsed['duplicates'],1);self.assertEqual(len(parsed['records']),1)
        conflict=list(ROWS[0]);conflict[2]='abgelaufen'
        with self.assertRaises(ValueError):parse_csv(csv_bytes([ROWS[0],conflict]))
        parsed=parse_csv(csv_bytes());self.assertEqual(json.loads(parsed['records'][1]['source_json'])['valid_until'],'0000-00-00')

    def test_reference_endpoint_and_actual_vzg_ds100_mapping_without_gps(self):
        from lokzeitleiste.operating_points import seed_operating_points
        with Session(self.engine) as db:seed_operating_points(db);db.commit()
        refs=self.driver.get('/api/v1/tf/route-knowledge/operating-points',params={'route':'1000'})
        self.assertEqual(refs.status_code,200);self.assertTrue(refs.json()['items']);self.assertEqual(refs.json()['owner_id'],self.tf)
        self.assertEqual(self.client.get('/api/v1/tf/route-knowledge/operating-points',params={'route':'1000'}).status_code,403)
        raw=csv_bytes([['Referenzabschnitt','1000','streckenkundig','2027-01-01','-','-','AFW','AFR']])
        preview=self.preview(raw);self.assertEqual(preview.status_code,200,preview.text)
        self.assertEqual(self.apply(preview.json(),raw).status_code,200)
        item=self.driver.get(self.path).json()['items'][0]
        self.assertIn(item['map_match']['status'],['mapped','partial']);self.assertEqual(item['from_code'],'AFW');self.assertEqual(item['to_code'],'AFR')
        self.assertEqual(item['status'],'streckenkundig');self.assertEqual(self.counts(),(1,1,0))
