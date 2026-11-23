# Regressionstests für die gemeinsamen Anwendungsabläufe.
"""La publication permission, PDF validation and authenticated TF delivery."""
import unittest,hashlib
import test_accounts
from fastapi.testclient import TestClient
from lokzeitleiste.main import app
from la_sample import sample_pdf
class LaInstructionsTest(unittest.TestCase):
    setUp=test_accounts.AccountsTest.setUp
    tearDown=test_accounts.AccountsTest.tearDown
    payload=test_accounts.AccountsTest.payload
    create_staff=test_accounts.AccountsTest.create_staff
    staff_login=test_accounts.AccountsTest.staff_login
    change=test_accounts.AccountsTest.change
    active_staff=test_accounts.AccountsTest.active_staff
    def fields(self):return dict(region='nord',title='La Nord',edition='18.11.2026',valid_from='2026-11-18',valid_until='2026-11-24')
    def publish(self,client=None,content=None,**fields):return (client or self.client).post('/api/v1/admin/la-instructions',data={**self.fields(),**fields},files={'file':('La Nord – gültig.pdf',content if content is not None else sample_pdf(),'application/pdf')})
    def test_permissions_publication_reading_and_deletion(self):
        _,reader=self.active_staff({'la':1},'la-reader');_,writer=self.active_staff({'la':2},'la-writer');_,none=self.active_staff({},'la-none')
        self.assertEqual(none.get('/api/v1/admin/la-instructions').status_code,403)
        self.assertEqual(self.publish(reader).status_code,403)
        r=self.publish(writer);self.assertEqual(r.status_code,201,r.text);entry=r.json()['id']
        rows=reader.get('/api/v1/admin/la-instructions').json();self.assertFalse(rows['can_write']);self.assertEqual(rows['items'][0]['region'],'nord');self.assertNotIn('content',rows['items'][0])
        self.assertEqual(reader.delete('/api/v1/admin/la-instructions/'+str(entry)).status_code,403)
        driver=TestClient(app,base_url='https://testserver');self.staff_clients.append(driver);driver.post('/api/v1/account/login',json={'username':'787100','password':'tf-secret-12345'})
        listing=driver.get('/api/v1/tf/la-instructions');self.assertEqual(listing.status_code,200,listing.text);self.assertEqual(listing.json()['owner_id'],self.tf)
        pdf=driver.get(f'/api/v1/tf/la-instructions/{entry}/pdf');self.assertEqual(pdf.content,sample_pdf());self.assertEqual(pdf.headers['content-type'],'application/pdf');self.assertIn('filename*=',pdf.headers['content-disposition']);self.assertIn('no-store',pdf.headers['cache-control'])
        self.assertEqual(driver.post('/api/v1/admin/la-instructions',data=self.fields(),files={'file':('a.pdf',sample_pdf())}).status_code,401)
        with TestClient(app,base_url='https://testserver') as public:self.assertEqual(public.get(f'/api/v1/tf/la-instructions/{entry}/pdf').status_code,401)
        self.assertEqual(writer.delete('/api/v1/admin/la-instructions/'+str(entry)).status_code,200)
        self.assertEqual(driver.get(f'/api/v1/tf/la-instructions/{entry}/pdf').status_code,404)
    def test_validation_duplicate_dates_and_no_portal_login(self):
        for args in [dict(content=b'%PDF-garbage'),dict(region='unknown'),dict(valid_until='2026-11-01'),dict(title='   ')]:self.assertEqual(self.publish(**args).status_code,422)
        self.assertEqual(self.publish(content=b'x'*(10*1024*1024+1)).status_code,413)
        first=self.publish();self.assertEqual(first.status_code,201,first.text);self.assertEqual(self.publish().status_code,409)
        self.assertEqual(self.publish(region='ost').status_code,201)
        rows=self.client.get('/api/v1/admin/la-instructions').json()['items'];self.assertEqual(rows[0]['content_sha256'],hashlib.sha256(sample_pdf()).hexdigest())
        self.assertEqual(self.client.post('/api/v1/admin/la-instructions/login',json={'username':'a','password':'b'}).status_code,405)
        self.assertEqual(self.client.get('/tf/la-vendor/manifest.json').status_code,404)
        self.assertEqual(self.client.get('/tf/la-vendor/pdf.mjs').status_code,200)
