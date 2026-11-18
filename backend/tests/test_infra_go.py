import json,unittest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
import test_app_defaults
from lokzeitleiste.infra_go import migrate,normalize,CANONICAL,alias_map
from lokzeitleiste.models import AppDefaultSeed,AppDefaultValue,AppDefaultOrder,DutyReport,DutyReportDraft,DutyReportCorrection,TrainGpsRecording,GpsDemoShare,User

class InfraGoTest(unittest.TestCase):
    def test_database_migration_merges_aliases_and_preserves_recording_and_report_identity(self):
        report=self.create(self.data());rid=report['id']
        with Session(self.engine) as db:
            target=db.scalar(select(AppDefaultValue).where(AppDefaultValue.category=='cause',AppDefaultValue.value==CANONICAL))
            aliases=[AppDefaultValue(category='cause',value=value,label=label,label_key=label.casefold(),active=True,ever_used=True,revision=3) for value,label in [('DB InfraGo','DB InfraGo'),('DB InfraoGo','DB InfraoGo'),('custom-old-infra','DB-InfraoGo')]]
            db.add_all(aliases);db.flush()
            db.add(AppDefaultOrder(scope='cause',ids_json=json.dumps([aliases[0].id,target.id,aliases[1].id,aliases[2].id]),revision=4))
            row=db.get(DutyReport,rid);payload=json.loads(row.payload_json);payload['train_journeys'][0]['events'][0].update(cause='DB InfraGo',cause_label='DB InfraGo',cause_detail='DB InfraoGo im persönlichen Hinweis')
            row.payload_json=json.dumps(payload,ensure_ascii=False);original=row.payload_json
            draft=DutyReportDraft(owner_id=self.tf,client_id=str(uuid4()),payload_json=original,revision=5);db.add(draft)
            gps_data={'train_number':'123','ended':True,'points':[dict(t=1792627200000,lat=52,lon=13,accuracy=5,speed=0)],'stop_edits':{'first':{'cause':'DB InfraoGo'},'second':{'cause':'custom-old-infra'}},'reasons':{'legacy':{'cause':'DB InfraGo'}}}
            gps=TrainGpsRecording(owner_id=self.tf,journey_id=str(uuid4()),payload_json=json.dumps(gps_data),revision=7);db.add(gps);db.flush()
            db.add(GpsDemoShare(recording_id=gps.id,owner_id=self.tf,payload_json=gps.payload_json,source_revision=7))
            actor=db.scalar(select(User.id).where(User.role=='admin'))
            correction=DutyReportCorrection(report_id=rid,owner_id=self.tf,client_id=str(uuid4()),version=1,reason='Test',returned_by=actor,payload_json=original,pdf_content=b'original PDF bytes',submitted_json=json.dumps(payload,separators=(',',':')));db.add(correction);db.flush()
            ids=(gps.id,draft.id,correction.id);db.delete(db.get(AppDefaultSeed,3));db.commit();migrate(db)
            self.assertEqual(len(list(db.scalars(select(AppDefaultValue).where(AppDefaultValue.category=='cause')))),4)
            self.assertEqual(json.loads(db.get(AppDefaultOrder,'cause').ids_json),[target.id])
            self.assertEqual(alias_map(db)['custom-old-infra'],CANONICAL)
            self.assertEqual(json.loads(db.get(DutyReport,rid).payload_json)['train_journeys'][0]['events'][0]['cause'],CANONICAL)
            self.assertEqual(db.get(DutyReport,rid).payload_json,db.get(DutyReportCorrection,ids[2]).payload_json)
            self.assertEqual(db.get(DutyReportCorrection,ids[2]).pdf_content,b'original PDF bytes')
            self.assertEqual(json.loads(db.get(DutyReportCorrection,ids[2]).submitted_json)['train_journeys'][0]['events'][0]['cause_label'],CANONICAL)
            self.assertEqual(db.get(DutyReportDraft,ids[1]).revision,5)
            migrated=json.loads(db.get(TrainGpsRecording,ids[0]).payload_json)
            self.assertEqual(migrated['points'],gps_data['points']);self.assertTrue(all(row['cause']==CANONICAL for row in migrated['stop_edits'].values()))
            self.assertEqual(db.get(TrainGpsRecording,ids[0]).revision,7);self.assertEqual(db.get(GpsDemoShare,ids[0]).source_revision,7)
            self.assertEqual(json.loads(db.get(GpsDemoShare,ids[0]).payload_json),migrated)
            self.assertEqual(json.loads(db.get(DutyReport,rid).payload_json)['train_journeys'][0]['events'][0]['cause_detail'],'DB InfraoGo im persönlichen Hinweis')
            before=target.revision;migrate(db);self.assertEqual(target.revision,before)
        catalogue=self.driver.get('/api/v1/tf/app-defaults').json();self.assertEqual(sum(row['label']==CANONICAL for row in catalogue),1)
        data=json.loads(json.dumps(self.data()).replace('2026-10-12','2026-10-15'));data['train_journeys'][0]['events'][0]['cause']='custom-old-infra'
        accepted=self.driver.post('/api/v1/tf/work-reports',json=data);self.assertEqual(accepted.status_code,201,accepted.text);self.assertEqual(accepted.json()['train_journeys'][0]['events'][0]['cause'],CANONICAL)
        base=1792627200000;key='manual-'+str(base)
        gps_response=self.driver.put('/api/v1/tf/gps/'+str(uuid4()),json=dict(train_number='123',points=[dict(t=base,lat=52,lon=13,accuracy=5,speed=0)],manual_stops=[dict(key=key,start=base,end=base+60000)],stop_edits={key:dict(cause='custom-old-infra',reason='V3')},ended=True,expected_revision=0))
        self.assertEqual(gps_response.status_code,200,gps_response.text);self.assertEqual(gps_response.json()['stop_edits'][key]['cause'],CANONICAL)
        for label in ['DB InfraGo','DB InfraoGo','DB-InfraGo']:
            self.assertEqual(self.client.post('/api/v1/admin/app-defaults/cause',json=dict(label=label,active=True)).status_code,409)

    def test_old_inputs_remain_compatible_and_only_canonical_cause_is_saved(self):
        for index,value in enumerate(['DB InfraGo','DB InfraoGo','DB-InfraGo']):
            data=self.data();data['train_journeys'][0]['events'][0]['cause']=value
            raw=json.dumps(data).replace('2026-10-12','2026-10-'+str(12+index));data=json.loads(raw)
            response=self.driver.post('/api/v1/tf/work-reports',json=data)
            self.assertEqual(response.status_code,201,response.text);self.assertEqual(response.json()['train_journeys'][0]['events'][0]['cause'],CANONICAL)
        self.assertEqual(normalize({'cause':'DB InfraoGo','detail':'DB InfraoGo','station_name':'DB InfraGo AG'}),{'cause':CANONICAL,'detail':'DB InfraoGo','station_name':'DB InfraGo AG'})

for name in ['setUp','tearDown','payload','train','event','data','create']:
    setattr(InfraGoTest,name,getattr(test_app_defaults.AppDefaultsTest,name))
