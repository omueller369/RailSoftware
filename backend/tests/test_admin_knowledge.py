import unittest,json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_accounts,test_stations
from lokzeitleiste.main import app
from lokzeitleiste.models import User,TfLocationKnowledge,TfRollingStockKnowledge,TrainGpsRecording,AccountPolicy,SystemChangeLog
from test_route_knowledge_import import csv_bytes
from test_tf_knowledge import raw

class AdminKnowledgeTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown
    def staff(self,name,level):
        response=self.client.post('/api/v1/admin/staff',json=test_accounts.AccountsTest.payload(self,name,{'knowledge':level}));self.assertEqual(response.status_code,201,response.text)
        client=TestClient(app,base_url='https://testserver');self.staff_clients.append(client);client.post('/api/v1/admin/login',json={'username':name,'password':'initial-secret-12345'});client.post('/api/v1/account/password',json={'current_password':'initial-secret-12345','new_password':'personal-secret-67890','confirm_password':'personal-secret-67890'});client.post('/api/v1/admin/login',json={'username':name,'password':'personal-secret-67890'});return response.json()['id'],client
    def base(self,owner=None):return '/api/v1/admin/knowledge/'+str(owner or self.tf)
    def test_module_permissions_enumeration_target_isolation_and_target_password_policy(self):
        _,denied=self.staff('know-none',0);_,reader=self.staff('know-reader',1)
        self.assertEqual(denied.get('/api/v1/admin/knowledge/drivers').status_code,403)
        result=reader.get('/api/v1/admin/knowledge/drivers');self.assertEqual(result.status_code,200,result.text);self.assertFalse(result.json()['can_write']);self.assertTrue(any(r['id']==self.tf for r in result.json()['items']))
        self.assertEqual(self.driver.get('/api/v1/admin/knowledge/drivers').status_code,401)
        with Session(self.engine) as db:db.get(AccountPolicy,self.tf).must_change_password=True;db.commit()
        self.assertEqual(reader.get(self.base()+'/knowledge/classes').status_code,200,'Target password reset does not block authorized staff review')
        self.assertEqual(reader.get(self.base()+'/route-knowledge?dates=1').status_code,200)
        denied_write=reader.post(self.base()+'/series',json={'series':'186','valid_until':'2029-01-01'});self.assertEqual(denied_write.status_code,403)
        self.assertEqual(reader.get('/api/v1/admin/knowledge/1/knowledge/classes').status_code,404,'Cannot target staff/admin as TF')
        self.assertIn('no-store',result.headers.get('cache-control',''))
        self.assertEqual(reader.get('/api/v1/admin/tf').status_code,403,'Knowledge permission does not disclose full employee records')
        stations=reader.get('/api/v1/admin/knowledge/stations',params={'q':'B'})
        self.assertEqual(stations.status_code,200,stations.text)
        self.assertTrue(stations.json())
        self.assertEqual(reader.get('/api/v1/admin/knowledge/stations',params={'q':'%'}).json(),[], 'Search wildcards treated literally')
        self.assertIn('admin/knowledge',reader.get('/api/v1/admin/start').text)
        self.assertIn('adminKnowledgeTemplate',reader.get('/admin/knowledge').text)
    def test_class_create_edit_duplicate_stale_cross_target_and_real_audit_actor(self):
        actor,writer=self.staff('know-writer',2);base=self.base();data={'series':'0186','valid_until':'2029-10-06'}
        r=writer.post(base+'/series',json=data);self.assertEqual(r.status_code,200,r.text)
        listing=writer.get(base+'/knowledge/classes').json();item=listing['items'][0];self.assertEqual(item['series'],'0186');self.assertEqual(listing['identity']['owner_id'],self.tf)
        self.assertEqual(writer.post(base+'/series',json=data).status_code,409)
        update={**data,'series':'0187','valid_until':'2030-01-01','expected_revision':item['revision']}
        r=writer.patch(base+'/series/'+str(item['id']),json=update);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(writer.patch(base+'/series/'+str(item['id']),json=update).status_code,409)
        other=self.create_tf('787101','P-KNOW-OTHER').json()['id'];self.assertEqual(writer.get(self.base(other)+'/knowledge/classes').json()['items'],[])
        self.assertEqual(writer.patch(self.base(other)+'/series/'+str(item['id']),json=update).status_code,404)
        self.assertEqual(writer.post(base+'/series',json={'series':'1','valid_until':'2029-02-30'}).status_code,422)
        self.assertEqual(self.driver.get('/api/v1/tf/knowledge/classes').json()['items'][0]['series'],'0187','Admin edits are the actual TF inventory, not a copy')
        with Session(self.engine) as db:
            logs=list(db.scalars(select(SystemChangeLog).where(SystemChangeLog.employee_id==actor)))
            self.assertTrue(any('tf_rolling_stock_knowledge' in row.change for row in logs),'Staff actor preserved in transactional audit')
    def test_shared_imports_and_geometry_are_read_and_written_for_selected_tf_only(self):
        _,writer=self.staff('know-import',2);other=self.create_tf('787101','P-KNOW-IMPORT').json()['id'];base=self.base(other)
        for kind,data in [('places',raw('places')),('classes',raw('classes'))]:
            r=writer.post(base+'/knowledge/'+kind+'/preview',files={'file':('k.csv',data)});self.assertEqual(r.status_code,200,r.text);preview=r.json()
            fields=dict(confirmed='true',expected_sha256=preview['summary']['file_sha256'],owner_token=preview['owner_token'])
            self.assertEqual(writer.post(base+'/knowledge/'+kind,data=fields,files={'file':('k.csv',data)}).status_code,200)
            self.assertEqual(len(writer.get(base+'/knowledge/'+kind).json()['items']),2)
            self.assertEqual(writer.get(self.base()+'/knowledge/'+kind).json()['items'],[])
        data=csv_bytes();r=writer.post(base+'/route-knowledge/imports/preview',files={'file':('r.csv',data)});self.assertEqual(r.status_code,200,r.text);preview=r.json();form=dict(confirmed='true',expected_sha256=preview['summary']['file_sha256'],owner_token=preview['owner_token'])
        self.assertEqual(writer.post(base+'/route-knowledge/imports',data=form,files={'file':('r.csv',data)}).status_code,200)
        self.assertEqual(len(writer.get(base+'/route-knowledge/imports').json()['items']),3)
        self.assertEqual(writer.get(self.base()+'/route-knowledge/imports').json()['items'],[])
        self.assertEqual(writer.post(self.base()+'/route-knowledge/imports',data=form,files={'file':('r.csv',data)}).status_code,409,'Other TF preview token cannot be applied to the current TF')
        with Session(self.engine) as db:
            db.add(TrainGpsRecording(owner_id=other,journey_id=str(uuid4()),revision=1,payload_json=json.dumps({'points':[{'t':1795000000000,'lat':52,'lon':13,'accuracy':5},{'t':1795000010000,'lat':52.001,'lon':13.001,'accuracy':5}]})));db.commit()
        self.assertEqual(len(writer.get(base+'/route-knowledge?dates=1').json()['items']),1)
        self.assertEqual(writer.get(self.base()+'/route-knowledge?dates=1').json()['items'],[])
