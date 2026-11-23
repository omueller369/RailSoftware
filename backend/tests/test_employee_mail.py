# Regressionstests für Postfächer und Nachrichtenversand.
import os
import unittest
from datetime import date
from unittest.mock import patch,MagicMock
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import test_api
from lokzeitleiste.main import app
from lokzeitleiste.employee_mail import local_name,suggest,save_email
from lokzeitleiste.mailbox import service
from lokzeitleiste.mailbox.api import MessageInput
from lokzeitleiste.models import EmployeeEmail,MailboxAccount,MailboxProvision,User


class EmployeeMailTest(unittest.TestCase):
    def setUp(self):
        test_api.ApiFlowTest.setUp(self)
        self.client.post('/api/v1/admin/login',json={'username':'admin','password':'admin-secret-12345'})
        self.create_tf=test_api.ApiFlowTest.create_tf.__get__(self)
        self.env=patch.dict(os.environ,{'CTL_MAIL_DOMAIN':'ctl-software.io-goerlitz.eu','CTL_MAIL_PROVISIONING':'1','MAILBOX_ENCRYPTION_KEY':Fernet.generate_key().decode(),'MAILBOX_IMAP_HOST':'ctl-software.io-goerlitz.eu','MAILBOX_SMTP_HOST':'ctl-software.io-goerlitz.eu'});self.env.start()
    def tearDown(self):self.env.stop();test_api.ApiFlowTest.tearDown(self)
    def test_suggestion_collision_and_managed_mailbox_are_transactional(self):
        first=self.create_tf('787111','MAIL1').json()['id']
        with Session(self.engine) as db:
            user=db.get(User,first)
            address=suggest(db,'Jörg','Müller',date(1980,1,1),'ctl-software.io-goerlitz.eu',first)
            self.assertEqual(address,'joerg.mueller@ctl-software.io-goerlitz.eu')
            save_email(db,user,address,'secret123');db.commit()
            self.assertEqual(db.get(MailboxProvision,first).status,'pending')
            self.assertNotIn('secret123',db.get(MailboxAccount,first).password_encrypted)
            self.assertEqual(suggest(db,'Jörg','Müller',date(1980,1,1),'ctl-software.io-goerlitz.eu'),'joerg.mueller80@ctl-software.io-goerlitz.eu')
            self.assertEqual(local_name('Anna Maria','Groß'),'annamaria.gross')
        rows=self.client.get('/api/v1/admin/email/employees')
        self.assertEqual(rows.status_code,200,rows.text)
        self.assertEqual(next(r for r in rows.json() if r['id']==first)['email'],address)
    def test_domain_validation_external_email_and_unready_send(self):
        self.assertEqual(self.client.get('/api/v1/admin/email-domains').status_code,200)
        self.assertEqual(self.client.post('/api/v1/admin/app-defaults/email-domains',json={'name':'bad domain'}).status_code,422)
        self.assertEqual(self.client.post('/api/v1/admin/app-defaults/email-domains',json={'name':'EXAMPLE.ORG'}).status_code,201)
        uid=self.create_tf('787112','MAIL2').json()['id']
        result=self.client.post('/api/v1/admin/email/employees/'+str(uid)+'/send',json={'to':['a@example.org'],'subject':'Hi','body':'Test'})
        self.assertEqual(result.status_code,409)
    def test_same_browser_admin_cookie_and_tf_bearer_are_independent(self):
        uid=self.create_tf('787113','MAIL3').json()['id']
        result=self.client.post('/api/v1/account/login',json={'username':'787113','password':'tf-secret-12345'})
        self.assertEqual(result.status_code,200,result.text)
        token=result.json()['access_token']
        self.assertEqual(self.client.get('/api/v1/admin/me').json()['role'],'admin')
        self.assertEqual(self.client.get('/tf',follow_redirects=False).status_code,200)
        self.assertEqual(self.client.get('/api/v1/account/me',headers={'Authorization':'Bearer '+token}).json()['id'],uid)
        self.assertEqual(self.client.get('/api/v1/admin/me',headers={'Authorization':'Bearer '+token}).status_code,401)
        self.assertEqual(self.client.get('/api/v1/account/me',headers={'Authorization':'Bearer invalid'}).status_code,401)
    def test_new_staff_gets_personal_mailbox_with_portal_initial_password(self):
        payload=dict(username='office-new',initial_password='initial123',first_name='Lea',last_name='Müller',nationality='DE',birth_date='1985-04-03',cost_center='A',addresses=[dict(street='Weg',house_number='1',postal_code='12345',city='Berlin')],permissions={})
        result=self.client.post('/api/v1/admin/staff',json=payload)
        self.assertEqual(result.status_code,201,result.text)
        uid=result.json()['id']
        with Session(self.engine) as db:
            account=db.get(MailboxAccount,uid)
            self.assertEqual(account.address,'lea.mueller@ctl-software.io-goerlitz.eu')
            self.assertEqual(Fernet(os.environ['MAILBOX_ENCRYPTION_KEY'].encode()).decrypt(account.password_encrypted.encode()).decode(),'initial123')

    def test_cc_and_bcc_use_envelope_without_exposing_bcc_in_saved_copy(self):
        uid=self.create_tf('787114','MAIL4').json()['id']
        with Session(self.engine) as db:
            save_email(db,db.get(User,uid),'mira.mail@ctl-software.io-goerlitz.eu','secret123');db.commit()
            account=db.get(MailboxAccount,uid)
            from lokzeitleiste.models import MailboxSettings
            account._settings=db.get(MailboxSettings,uid)
            smtp=MagicMock();smtp.__enter__.return_value=smtp;smtp.send_message.return_value={}
            imap=MagicMock();imap.__enter__.return_value=imap;imap.append.return_value=('OK',[])
            with patch.object(service.smtplib,'SMTP_SSL',return_value=smtp),patch.object(service,'connection',return_value=imap):
                service.send(account,MessageInput(to=['one@example.org'],cc=['copy@example.org'],bcc=['hidden@example.org'],subject='Test',body='Text'))
            message=smtp.send_message.call_args.args[0]
            self.assertIsNone(message.get('Bcc'))
            self.assertEqual(message['Cc'],'copy@example.org')
            self.assertEqual(smtp.send_message.call_args.kwargs['to_addrs'],['one@example.org','copy@example.org','hidden@example.org'])
            self.assertNotIn(b'hidden@example.org',imap.append.call_args.args[3])

    def test_tf_creation_with_hosted_domain_queues_mailbox(self):
        self.create_tf('787115','MAIL5')
        profile=self.client.get('/api/v1/admin/tf').json()[0]
        profile.update(username='787116',personnel_number='MAIL6',password='secret123',email='mira.beispiel@ctl-software.io-goerlitz.eu')
        created=self.client.post('/api/v1/admin/tf',json=profile)
        self.assertEqual(created.status_code,201,created.text)
        with Session(self.engine) as db:
            job=db.get(MailboxProvision,created.json()['id'])
            self.assertEqual(job.status,'pending')
            self.assertEqual(job.address,profile['email'])

    def test_dashboard_omits_external_administrator_tools(self):
        modules=self.client.get('/api/v1/admin/start').json()['modules']
        self.assertFalse({'/phpmyadmin','/webmailer'} & {r['url'] for r in modules})
        self.assertEqual(self.client.get('/api/v1/admin/start').json()['admin_tools'],[])

    def test_tf_and_wgm_creation_queue_entered_address_and_initial_password(self):
        # Die TF-Eingabe entspricht dem regulären Anlageformular und verwendet eine verwaltete Adresse.
        from unittest.mock import patch as mock_patch
        original=self.client.post
        def post(url,**kwargs):
            if url=='/api/v1/admin/tf':kwargs['json']['email']='mira.tf@ctl-software.io-goerlitz.eu'
            return original(url,**kwargs)
        with mock_patch.object(self.client,'post',side_effect=post):
            result=self.create_tf('787119','MAIL-TF')
        self.assertEqual(result.status_code,201,result.text)
        tf_id=result.json()['id']
        payload=dict(username='wgm.mail',password='wgm-secret-12345',first_name='Anna',last_name='Wagen',personnel_number='W-MAIL',birth_date='1990-05-12',vacation_days=30,email='anna.wgm@ctl-software.io-goerlitz.eu',gender='female',nationality='DE',weekly_minutes=2400,entry_date='2020-01-01',addresses=[dict(street='Hauptstraße',house_number='1',postal_code='01234',city='Berlin',federal_state='BE',is_postal=True)])
        result=self.client.post('/api/v1/admin/wgm',json=payload)
        self.assertEqual(result.status_code,201,result.text)
        with Session(self.engine) as db:
            for uid,address,password in [(tf_id,'mira.tf@ctl-software.io-goerlitz.eu','tf-secret-12345'),(result.json()['id'],payload['email'],payload['password'])]:
                job=db.get(MailboxProvision,uid)
                self.assertEqual(job.address,address);self.assertEqual(job.status,'pending')
                self.assertEqual(service.cipher().decrypt(job.password_encrypted.encode()).decode(),password)
                before=job.password_encrypted
                save_email(db,db.get(User,uid),address)
                self.assertEqual(job.password_encrypted,before,'Profile edits must not reset mail passwords')

    def test_unconfigured_managed_mailbox_rolls_back_employee_creation(self):
        with patch.dict(os.environ,{'CTL_MAIL_PROVISIONING':''}):
            result=self.client.post('/api/v1/admin/staff',json=dict(username='missing-mail',initial_password='initial123',first_name='No',last_name='Mail',nationality='DE',birth_date='1985-04-03',cost_center='A',addresses=[dict(street='Weg',house_number='1',postal_code='12345',city='Berlin')],permissions={},email='no.mail@ctl-software.io-goerlitz.eu'))
            self.assertEqual(result.status_code,503,result.text)
        with Session(self.engine) as db:
            self.assertIsNone(db.scalar(select(User).where(User.username=='missing-mail')))
