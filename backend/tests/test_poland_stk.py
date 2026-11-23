# Regressionstests für polnische Referenznetz und die manuelle Streckenerfassung.
"""Owned Polish STK uses real reference paths, never synthetic GPS or DS100."""
import unittest
from datetime import timedelta
from sqlalchemy import select,func
from sqlalchemy.orm import Session
import test_api
from lokzeitleiste.poland_stk import reference,maximum,today
from lokzeitleiste.models import PolandRouteKnowledge,ManualRouteKnowledge,TrainGpsRecording
class PolandStkTest(unittest.TestCase):
    def setUp(self):
        test_api.ApiFlowTest.setUp(self)
        self.client.post('/api/v1/admin/login',json={'username':'admin','password':'admin-secret-12345'})
        self.uid=test_api.ApiFlowTest.create_tf(self,'787119','POLAND').json()['id']
        token=self.client.post('/api/v1/account/login',json={'username':'787119','password':'tf-secret-12345'}).json()['access_token'];self.headers={'Authorization':'Bearer '+token}
        graph=reference();by_node={p['node']:p['id'] for p in graph['points'] if p['node'] is not None}
        edge=next((i,e) for i,e in enumerate(graph['edges']) if e[0]!=e[1] and e[0] in by_node and e[1] in by_node)
        self.payload=dict(network_revision=graph['revision'],waypoints=[by_node[edge[1][0]],by_node[edge[1][1]]],legs=[[[edge[0]]]],valid_until=maximum(today()).isoformat())
    def tearDown(self):test_api.ApiFlowTest.tearDown(self)
    def request(self,method='POST',suffix='',data=None,headers=None):return self.client.request(method,'/api/v1/tf/poland-route-knowledge/manual'+suffix,json=data if data is not None else self.payload,headers=headers or self.headers)
    def test_save_edit_delete_owned_and_no_gps_or_german_changes(self):
        r=self.request();self.assertEqual(r.status_code,201,r.text);row=r.json()['items'][0];self.assertTrue(row['geometry']);self.assertEqual(r.json()['owner_id'],self.uid)
        self.assertEqual(self.request().status_code,409)
        admin=self.client.get('/api/v1/admin/knowledge/'+str(self.uid)+'/poland-route-knowledge/manual');self.assertEqual(admin.status_code,200,admin.text);self.assertEqual(admin.json()['items'][0]['id'],row['id'])
        suffix='/'+str(row['id']);body={**self.payload,'expected_sha256':row['revision'],'valid_until':today().isoformat()};updated=self.request('PUT',suffix,body);self.assertEqual(updated.status_code,200,updated.text);new=updated.json()['items'][0]
        self.assertEqual(self.request('PUT',suffix,body).status_code,409)
        test_api.ApiFlowTest.create_tf(self,'787120','OTHER')
        token=self.client.post('/api/v1/account/login',json={'username':'787120','password':'tf-secret-12345'}).json()['access_token'];other={'Authorization':'Bearer '+token}
        self.assertEqual(self.request('GET',headers=other).json()['items'],[])
        self.assertEqual(self.request('PUT',suffix,{**body,'expected_sha256':new['revision']},other).status_code,404)
        self.assertEqual(self.request('DELETE',suffix+'?expected_sha256='+new['revision'],headers=other).status_code,404)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(TrainGpsRecording)),0);self.assertEqual(db.scalar(select(func.count()).select_from(ManualRouteKnowledge)),0)
        self.assertEqual(self.request('DELETE',suffix+'?expected_sha256='+row['revision']).status_code,409)
        deleted=self.request('DELETE',suffix+'?expected_sha256='+new['revision']);self.assertEqual(deleted.status_code,200,deleted.text);self.assertEqual(deleted.json()['items'],[])
    def test_invalid_paths_dates_revision_unlinked_and_strict_edges(self):
        g=reference();unlinked=next(p['id'] for p in g['points'] if p['node'] is None)
        cases=[({'network_revision':'0'*64},409),({'valid_until':(maximum(today())+timedelta(days=1)).isoformat()},422),({'valid_until':(today()-timedelta(days=1)).isoformat()},422),({'waypoints':[unlinked,self.payload['waypoints'][1]]},422),({'legs':[[[-1]]]},422),({'legs':[[[True]]]},422),({'legs':[[[999999]]]},422),({'waypoints':['AFW','AFR']},422),({'waypoints':[self.payload['waypoints'][0]]*2},422),({'legs':[]},422),({'legs':[[self.payload['legs'][0][0]]*4]},422)]
        for changes,status in cases:
            r=self.request(data={**self.payload,**changes});self.assertEqual(r.status_code,status,(changes,r.text))
        self.assertEqual(self.request('GET').json()['items'],[])
    def test_old_snapshot_allows_date_only_updates_but_never_remaps_geometry(self):
        from unittest.mock import patch
        row=self.request().json()['items'][0];suffix='/'+str(row['id']);old_geometry=row['geometry']
        changed={**reference(),'revision':'f'*64}
        with patch('lokzeitleiste.poland_stk.reference',return_value=changed):
            body={**self.payload,'valid_until':today().isoformat(),'expected_sha256':row['revision']}
            r=self.request('PUT',suffix,body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['items'][0]['geometry'],old_geometry)
            body['expected_sha256']=r.json()['items'][0]['revision'];body['waypoints']=list(reversed(body['waypoints']))
            self.assertEqual(self.request('PUT',suffix,body).status_code,409)
    def test_public_offline_assets_are_bounded_and_private_requires_account(self):
        for path in ['manifest','topology','geometry-0']:
            r=self.client.get('/tf/poland-stk-data/'+path+'.json');self.assertEqual(r.status_code,200);self.assertEqual(r.json()['schema'],1)
        for path in ['geometry-999','unknown','geometry--1']:
            self.assertEqual(self.client.get('/tf/poland-stk-data/'+path+'.json').status_code,404)
        self.assertEqual(self.client.get('/tf/poland-stk.js').status_code,200)
        self.assertEqual(self.client.get('/tf/poland-stk-worker.js').status_code,200)
if __name__=='__main__':unittest.main()
