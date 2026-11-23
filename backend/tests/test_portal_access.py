# Regressionstests für Zugriffsrechte der Verwaltungsbereiche.
"""Telemetry only accepts an authenticated TF identity and bounded page/version data."""
import unittest
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_api
from lokzeitleiste.models import TfPortalAccess, User, ModulePermission


class PortalAccessTest(unittest.TestCase):
    def setUp(self):
        test_api.ApiFlowTest.setUp(self)
        self.client.post('/api/v1/admin/login',json={'username':'admin','password':'admin-secret-12345'})
        self.uid=test_api.ApiFlowTest.create_tf(self,'787123','ACCESS').json()['id']
    def tearDown(self):test_api.ApiFlowTest.tearDown(self)

    def test_successful_login_and_page_identity_version_and_access_control(self):
        payload={'username':'787123','password':'tf-secret-12345'}
        self.assertEqual(self.client.post('/api/v1/account/login',json={**payload,'password':'wrong'}).status_code,401)
        response=self.client.post('/api/v1/account/login',json=payload,headers={'X-Rail-Android-Version':'0.27.13.17'})
        self.assertEqual(response.status_code,200,response.text)
        token=response.json()['access_token'];headers={'Authorization':'Bearer '+token}
        self.assertEqual(self.client.post('/api/v1/tf/portal-access',headers=headers,json={'path':'/tf/gps-demo','android_version':'0.27.13.17'}).status_code,204)
        self.assertEqual(self.client.get('/api/v1/admin/portal-access',headers=headers).status_code,401)
        response=self.client.get('/api/v1/admin/portal-access');self.assertEqual(response.status_code,200,response.text)
        rows=response.json();self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['tf_number'],'787123');self.assertEqual(rows[0]['first_name'],'Mira');self.assertEqual(rows[0]['android_version'],'0.27.13.17')
        self.assertRegex(rows[0]['date'],r'^\d{2}\.\d{2}\.\d{4}$');self.assertRegex(rows[0]['time'],r'^\d{2}:\d{2}:\d{2}$')
        self.assertNotIn(token,response.text);self.assertNotIn(payload['password'],response.text)
        self.assertEqual(self.client.post('/api/v1/tf/portal-access',headers=headers,json={'path':'/tf?token=secret'}).status_code,422)
        self.assertEqual(self.client.post('/api/v1/tf/portal-access',headers=headers,json={'path':'/admin'}).status_code,422)
        self.client.post('/api/v1/tf/portal-access',headers=headers,json={'path':'/tf','android_version':'<script>bad</script>'})
        self.assertEqual(self.client.get('/api/v1/admin/portal-access').json()[0]['android_version'],'')
        with Session(self.engine) as db:
            records=list(db.scalars(select(TfPortalAccess)));self.assertEqual(len(records),3)
            self.assertTrue(all(row.user_id==self.uid for row in records))
        modules=self.client.get('/api/v1/admin/start').json()['modules'];self.assertIn('portal_access',{m['id'] for m in modules})

    def test_anonymous_visit_and_staff_without_permission_rejected(self):
        from fastapi.testclient import TestClient
        from lokzeitleiste.main import app
        from lokzeitleiste.security import hash_password,issue_token
        with TestClient(app,base_url='https://testserver') as outsider:
            self.assertEqual(outsider.post('/api/v1/tf/portal-access',json={'path':'/tf'}).status_code,401)
        with Session(self.engine) as db:
            user=User(username='reader',role='staff',password_hash=hash_password('secret123456'));db.add(user);db.flush();staff_id=user.id;token=issue_token(db,user)
        headers={'Authorization':'Bearer '+token}
        self.assertEqual(self.client.get('/api/v1/admin/portal-access',headers=headers).status_code,403)
        with Session(self.engine) as db:
            db.add(ModulePermission(user_id=staff_id,module='portal_access',level=1));db.commit()
        self.assertEqual(self.client.get('/api/v1/admin/portal-access',headers=headers).status_code,200)

    def test_native_login_records_version(self):
        result=self.client.post('/api/v1/tf/login',json={'username':'787123','password':'tf-secret-12345'},headers={'X-Rail-Android-Version':'0.27.13.17'})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.client.get('/api/v1/admin/portal-access').json()[0]['android_version'],'0.27.13.17')
