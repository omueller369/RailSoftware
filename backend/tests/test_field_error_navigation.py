# Regressionstests für Portalnavigation und Berechtigungen.
import unittest
import test_app_defaults

class FieldNavigationTest(unittest.TestCase):
    def test_unavailable_choice_identifies_exact_row_without_saving_report(self):
        reason=self.add('reason','Temporary selection');self.client.delete('/api/v1/admin/app-defaults/value/'+str(reason['id']),params={'expected_revision':reason['revision']})
        data=self.data();train=self.train('SECOND');train['events'][0]['reason']=reason['value'];data['train_journeys'].append(train)
        response=self.driver.post('/api/v1/tf/work-reports',json=data)
        self.assertEqual(response.status_code,422,response.text)
        self.assertIn('Auswahlwert',response.json()['detail'])
        error=response.json()['errors'][0]
        self.assertEqual(error['loc'],['body','train_journeys',1,'events',0,'reason'])
        self.assertEqual(error['context'],dict(journey_id=train['id'],event_id=train['events'][0]['id']))
        self.assertNotIn('input',error)
    def test_other_semantic_station_error_identifies_event(self):
        data=self.data();train=data['train_journeys'][0];train['events'][0]['station']='XXBAD'
        response=self.driver.post('/api/v1/tf/work-reports',json=data)
        self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(response.json()['errors'][0]['loc'],['body','train_journeys',0,'events',0,'station'])
    def test_model_range_errors_are_safe_and_have_field_paths(self):
        data=self.data();data['train_journeys'][0]['events'][0]['end_at']='2026-10-12T10:00'
        response=self.driver.post('/api/v1/tf/work-reports',json=data)
        self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(response.json()['fields'][0]['field'],'body.train_journeys.0.events.0.end_at')
        self.assertNotIn('input',response.text)
        data=self.data();data['end_at']=data['start_at']
        response=self.driver.post('/api/v1/tf/work-reports',json=data)
        self.assertEqual(response.json()['fields'][0]['field'],'body.end_at')

for name in ['setUp','tearDown','payload','train','event','data','catalogue','add']:
    setattr(FieldNavigationTest,name,getattr(test_app_defaults.AppDefaultsTest,name))
