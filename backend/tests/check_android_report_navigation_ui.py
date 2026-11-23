# Browserprüfung für Berichte und die zugehörigen Prüf- und Versandabläufe.
"""Actual Android adapter + monthly synchronization + report/row correction."""
import json,re
from browser_realtime import check_pages
from check_field_error_navigation_ui import shell
from check_work_report_layout import STATIC

def fixture(legacy=False):
    raw=(STATIC/'work-report.js').read_text();source,blocks=raw.split('// Die Klappschalter',1)
    exported=r'''window.NavFixture={loadReport,synchronize,storeDraft,dropPending:id=>persistPending(pending.filter(row=>row.client_id!==id)),state:()=>state,rows:()=>pending,readonly:()=>busy||reportViewOnly,setup(editor,rows){user={id:7};key='android-report-navigation';trainEditor=editor;state={client_id:'blank',saved_id:null,kind:'Dienstschicht'};pending=rows;monthCache={'2026-11':{reports:[],days:[],work_minutes:0,guest_minutes:0,pause_minutes:0}};plans={};el('reportPeriod').value='2026-11';window.CtlValidation.registerResolver(el('workReport'),reportIssueField);renderMonth();}};})();'''
    source=re.sub(r'\}\)\(\);\s*$',lambda _:exported,source)+'// Die Klappschalter'+blocks
    prelude=r'''
localStorage.clear();history.replaceState(null,'','/tf/arbeitsbericht');
const legacy=LEGACY,sessionId=7;let attempts=0,uploads=0,stored=null,cloud={};
window.NativePortal={postMessage(raw){const job=JSON.parse(raw),value=job.method==='session'?{app_version:'test',account:{id:sessionId,role:'tf'},profile:{id:sessionId},username:'synthetic'}:{};queueMicrotask(()=>NativePortal.onmessage({data:JSON.stringify({id:job.id,ok:true,value})}));}};
const catalogue=[{category:'cause',value:'CTL',label:'CTL',active:true},{category:'cause',value:'DB-InfraGo',label:'DB-InfraGo',active:true},{category:'reason',value:'V3',label:'V3',active:true},{category:'reason',value:'Pause',label:'Pause',active:true}];
window.fetch=async(url,options={})=>{url=String(url);let data={},status=200;
 if(url==='/api/v1/tf/work-reports'&&options.method==='POST'){
  attempts++;const body=JSON.parse(options.body),train=body.train_journeys[0],event=train.events[0];
  if(event.cause==='Alt-Anbieter'){data={detail:'Auswahlwert ist nicht mehr verfügbar. Bitte neu auswählen.'};if(!legacy)data.errors=[{loc:['body','train_journeys',0,'events',0,'cause'],msg:data.detail,context:{journey_id:train.id,event_id:event.id}}];status=422;}
  else {uploads++;stored={...body,id:42,version:1,train_revision:0,train_editable:true,locked:false,duration_minutes:480,credited_minutes:480,documented_pause_minutes:30};data=stored;}
 }else if(url.includes('/train-journeys')&&options.method==='PUT'){stored={...stored,train_journeys:JSON.parse(options.body).train_journeys,train_revision:1};data=stored;}
 else if(url.endsWith('/app-defaults'))data=catalogue;
 else if(url==='/api/v1/tf/work-report-drafts')data={drafts:Object.values(cloud),finalized:[]};
 else if(url.includes('/work-report-drafts/')&&options.method==='PUT'){const body=JSON.parse(options.body),id=url.split('/').at(-1);data=cloud[id]={client_id:id,report:body.report,revision:1,receipt_keys:[],files:[]};}
 else if(url.includes('/work-report-drafts/'))data=cloud[url.split('/').at(-1)]||{files:[]};
 else if(url.includes('/work-reports/month/'))data={reports:stored?[stored]:[],days:[],work_minutes:480,guest_minutes:0,pause_minutes:30};
 else if(url.includes('/portal/plan/'))data={days:[]};
 else if(url.endsWith('/receipts')||url.includes('/stations'))data=[];
 else if(url.endsWith('/work-reports/42'))data=stored;
 else throw Error('Unexpected request '+url);
 return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
};
'''.replace('LEGACY','true' if legacy else 'false')
    scripts=(STATIC/'messages.js').read_text()+prelude+'\n'+(STATIC/'android-portal.js').read_text()+'\n'+(STATIC/'auth-session.js').read_text()+'\n'+'\n'.join((STATIC/name).read_text() for name in ['plan-colors.js','work-report-feedback.js','report-tabs.js','train-journeys.js'])+'\n'+source
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);},el=id=>document.getElementById(id),wait=()=>new Promise(resolve=>setTimeout(resolve,25)),until=async predicate=>{for(let i=0;i<200&&!predicate();i++)await wait();assert(predicate(),'Asynchronous navigation finished');};
 el('workReport').hidden=false;el('reportDetails').hidden=false;
 // A global fetch hook is deliberately bypassed: the report API must retain its own error paths.
 CtlValidation.response=async()=>{};
 const report=(client,day,number,cause)=>({client_id:client,kind:'Dienstschicht',pause_policy:1,actual_pause:30,in_hotel:false,hotel_location:'',hotel_name:'',overrun_reason:'',trips:[],ausbleibe:[],start_at:day+'T08:00',end_at:day+'T16:00',_cloud_dirty:false,_receipt_keys:[],train_journeys:[{id:crypto.randomUUID(),train_number:number,start_station:'AAA',start_station_name:'Bahnhof',end_station:'BBB',end_station_name:'Bahnhof',start_at:day+'T09:00',end_at:day+'T11:00',events:[{id:crypto.randomUUID(),cause,reason:'V3',cause_detail:'',reason_detail:'',station:'BBB',station_name:'Bahnhof',start_at:day+'T10:00',end_at:day+'T10:20'}]}]});
 const a=report(crypto.randomUUID(),'2026-11-18','111','CTL'),b=report(crypto.randomUUID(),'2026-11-17','222','Alt-Anbieter');
 const editor=new TrainJourneyEditor({userId:7,container:el('trainJourneyEditor'),button:el('newTrainJourney'),readonly:()=>NavFixture.readonly(),viewOnly:()=>NavFixture.readonly(),bounds:()=>({start:el('dutyStart').value,end:el('dutyEnd').value}),minute:value=>Date.parse(value)/60000,clock:String,uuid:()=>crypto.randomUUID(),stations(){},resolve:async input=>({code:input.value.split(' · ')[0],name:'Bahnhof'}),changed(){NavFixture.storeDraft();},editingChanged(){NavFixture.storeDraft();},message:value=>ReportFeedback.error(value),block(){}});
 NavFixture.setup(editor,[a,b]);await NavFixture.loadReport(a.client_id,true);if(legacy)NavFixture.dropPending(a.client_id);editor.items[0].fields.train_number.value='111NEW';editor.items[0].rows.children[0].click();editor.items[0].eventFields.station.value='AAA · UNSAVED LOCATION';NavFixture.storeDraft();
 ReportTabs.activate('month');await NavFixture.synchronize([b.client_id]);assert(attempts===1&&uploads===0,'Invalid report is not sent');const dialog=el('reportErrorTitle').parentElement;
 assert(dialog.open&&el('reportErrorText').textContent.includes('17.11.2026')&&el('reportErrorText').textContent.includes('222')&&el('reportErrorText').textContent.includes('Alt-Anbieter'),'Message identifies report, train and rejected value');assert(NavFixture.state().client_id===a.client_id,'No report switch before Okay');
 dialog.querySelector('button').click();await until(()=>NavFixture.state().client_id===b.client_id&&!NavFixture.readonly()&&document.activeElement===editor.items[0].eventFields.cause);
 const item=editor.items[0],field=item.eventFields.cause;assert(ReportTabs.active==='train'&&field.getAttribute('aria-invalid')==='true','Correct monthly report and row are opened with red field');assert(NavFixture.rows().some(row=>row.client_id===a.client_id),'Previously unsaved report remains accessible in the monthly list');assert(field.value==='Alt-Anbieter','Rejected value remains visible without automatic replacement');assert([...field.options].some(option=>option.value==='DB-InfraGo'&&!option.disabled),'Fresh valid choices offered');
 field.value='DB-InfraGo';field.dispatchEvent(new Event('change',{bubbles:true}));await editor.insert(item);await NavFixture.synchronize();assert(uploads===1&&stored.train_journeys[0].events[0].cause==='DB-InfraGo','Corrected report synchronizes once');
 await NavFixture.loadReport(a.client_id,true);assert(editor.items[0].fields.train_number.value==='111NEW','Other report header edits recovered');assert(editor.items[0].eventFields.station.value==='AAA · UNSAVED LOCATION'&&editor.items[0].editing===a.train_journeys[0].events[0].id,'Other report unsaved row and editing identity recovered');
 parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return shell().replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()
    for legacy in [False,True]:check_pages(lambda:fixture(legacy),a.output_dir+('/legacy-server' if legacy else '/structured-server'),widths=(800,320),label='Android monthly error '+('legacy' if legacy else 'structured'))
