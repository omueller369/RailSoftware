# Browserprüfung für Portalnavigation und Berechtigungen.
"""Real DOM: server field paths, hidden train rows, stale errors and portal tiles."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html

def shell():
    page=localize_html((runner.STATIC/'tf-portal.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['portal-theme.css','tf-portal.css','work-report.css','responsive.css'])
    return page.replace('</head>','<style>'+css+'</style></head>')

def fixture():
    raw=(runner.STATIC/'work-report.js').read_text();source,blocks=raw.split('// Die Klappschalter',1)
    source=re.sub(r'\}\)\(\);\s*$',r'''window.FieldNavFixture={setup(editor){state={client_id:'test-report'};trainEditor=editor;window.CtlValidation.registerResolver(el('workReport'),reportIssueField);}};})();''',source)
    source+='// Die Klappschalter'+blocks
    validation='/* Gemeinsame Feldrückmeldungen'+(runner.STATIC/'auth-session.js').read_text().split('/* Gemeinsame Feldrückmeldungen',1)[1]
    scripts='\n'.join([(runner.STATIC/'messages.js').read_text(),(runner.STATIC/'infra-go.js').read_text(),validation,(runner.STATIC/'work-report-feedback.js').read_text(),(runner.STATIC/'report-tabs.js').read_text(),(runner.STATIC/'train-journeys.js').read_text(),source])
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},tick=()=>new Promise(resolve=>setTimeout(resolve,100)),el=id=>document.getElementById(id);
 el('workReport').hidden=false;el('reportDetails').hidden=false;el('dutyStart').value='2026-11-18T08:00';el('dutyEnd').value='2026-11-18T16:00';
 const event=(id,time='10:00')=>({id,reason:'V3',reason_detail:'',cause:'DB InfraGo',cause_detail:'',station:'BBB',station_name:'Bahnhof',start_at:'2026-11-18T'+time,end_at:'2026-11-18T10:20'});
 const trains=[1,2].map(n=>({id:'train-'+n,train_number:String(n),start_station:'AAA',start_station_name:'Start',end_station:'BBB',end_station_name:'Ziel',start_at:'2026-11-18T09:00',end_at:'2026-11-18T11:00',events:[event('event-'+n)]}));
 const editor=new TrainJourneyEditor({userId:7,container:el('trainJourneyEditor'),button:el('newTrainJourney'),readonly:()=>false,viewOnly:()=>false,bounds:()=>({start:el('dutyStart').value,end:el('dutyEnd').value}),minute:value=>Date.parse(value)/60000,clock:String,uuid:()=>crypto.randomUUID(),stations(){},resolve:async input=>({code:input.value.split(' · ')[0],name:'Bahnhof'}),changed(){},editingChanged(){},message:value=>ReportFeedback.error(value),block(){}});
 editor.restore(trains);assert(editor.draft()[1].events[0].cause==='DB-InfraGo','Restoring rows preserves the stored choice key');FieldNavFixture.setup(editor);editor.activate('train-1');ReportTabs.activate('duty');ReportBlocks.collapse('trainJourneys');
 const message='Auswahlwert ist nicht mehr verfügbar. Bitte neu auswählen.',payload={client_id:'test-report',train_journeys:editor.draft()},snapshot=CtlValidation.capture({body:JSON.stringify(payload)});
 const fail=async(loc,context={})=>{await CtlValidation.response(new Response(JSON.stringify({detail:message,errors:[{loc:['body',...loc],msg:message,context}]}),{status:422}),snapshot);ReportFeedback.error(message);};
 await fail(['train_journeys',1,'events',0,'reason'],{journey_id:'train-2',event_id:'event-2'});assert(ReportTabs.active==='duty','Error waits for Okay before changing tabs');
 el('reportErrorTitle').parentElement.querySelector('button').click();await tick();const item=editor.items[1],field=item.eventFields.reason;
 assert(ReportTabs.active==='train'&&editor.active==='train-2','Okay opens correct report and train tabs');assert(!field.closest('[hidden]'),'Collapsed section and row editor are revealed');assert(document.activeElement===field,'Invalid value receives focus');assert(field.getAttribute('aria-invalid')==='true','Exact rejected value is marked red');assert(!editor.items[0].eventFields.reason.hasAttribute('data-ctl-invalid'),'Same value in other train stays unmarked');
 field.value='V1';field.dispatchEvent(new Event('change',{bubbles:true}));assert(!field.hasAttribute('data-ctl-invalid'),'Correction clears server highlight');
 await fail(['train_journeys',1,'events',0,'reason'],{journey_id:'train-2',event_id:'event-2'});el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(field.value==='V1'&&!field.hasAttribute('data-ctl-invalid'),'Delayed error never overwrites or re-marks corrected input');
 item.eventFields.reason_detail.value='KEEP CURRENT EDIT';await fail(['train_journeys',1,'events',0,'cause'],{journey_id:'train-2',event_id:'event-2'});el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(item.eventFields.reason_detail.value==='KEEP CURRENT EDIT'&&field.value==='V1','Jumping to the same row preserves its other unsaved inputs');
 editor.clearEvent(item);item.events.push(event('later-event','10:10'));editor.table(item);item.rows.children[0].click();item.eventFields.reason_detail.value='UNSAVED TEXT';
 const pendingSnapshot=CtlValidation.capture({body:JSON.stringify({client_id:'test-report',train_journeys:editor.draft()})});await CtlValidation.response(new Response(JSON.stringify({detail:message,errors:[{loc:['body','train_journeys',1,'events',1,'reason'],msg:message,context:{journey_id:'train-2',event_id:'later-event'}}]}),{status:422}),pendingSnapshot);ReportFeedback.error(message);el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(item.eventFields.reason_detail.value==='UNSAVED TEXT'&&item.editing==='event-2','Another pending row is preserved');assert(item.rows.children[1].children[1].getAttribute('data-ctl-invalid')==='true','Rejected table cell is highlighted when another row is pending');
 const root=CtlValidation.capture({body:JSON.stringify({client_id:'test-report',end_at:el('dutyEnd').value})});await CtlValidation.response(new Response(JSON.stringify({detail:'Eingaben prüfen',fields:[{field:'body.end_at',type:'value_error'}]}),{status:422}),root);ReportFeedback.error('Eingaben prüfen');el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(ReportTabs.active==='duty'&&document.activeElement===el('dutyEnd'),'Other server validation errors navigate to duty field');
 editor.restore(trains);editor.items[1].events[0].end_at='2026-11-18T18:00';editor.clearEvent(editor.items[1]);let rangeError;try{await editor.validate();}catch(error){rangeError=error;}assert(rangeError,'Local duty-range validation fails');ReportFeedback.error(rangeError.message);el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(editor.active==='train-2'&&document.activeElement===editor.items[1].eventFields.end_at,'Local validation also navigates to the actual stop');
 editor.clearEvent(editor.items[1]);editor.items[1].eventFields.reason.value='V3';const pendingMessage='Bitte die angefangene Zeile speichern.';editor.rememberPending(pendingMessage);ReportFeedback.error(pendingMessage);el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(editor.active==='train-2'&&document.activeElement.closest('form')===editor.items[1].form,'Unfinished-row guard navigates to pending inputs');
 ReportFeedback.error('Network unavailable');el('reportErrorTitle').parentElement.querySelector('button').click();await tick();assert(!el('syncReport').hasAttribute('data-ctl-invalid'),'Transport errors never invent an invalid form field');
 parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return shell().replace('</body>','<script>'+scripts+checks+'</script></body>')

def tiles(native=False):
    mock="history.replaceState(null,'','/tf');"+('window.AndroidPortal={};' if native else '')+"window.fetch=async url=>({ok:true,status:200,json:async()=>String(url).endsWith('/account/me')?{id:7,role:'tf'}:{id:7}});"
    check="""(async()=>{for(let i=0;i<100&&document.getElementById('landing').hidden;i++)await new Promise(resolve=>setTimeout(resolve,10));const tile=document.querySelector('a.module[href="/tf/updates"]');if(document.getElementById('landing').hidden||tile.hidden!==NATIVE)throw Error('Wrong update tile visibility');parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));""".replace('NATIVE','false' if native else 'true')
    return shell().replace('</body>','<script>'+(runner.STATIC/'messages.js').read_text()+mock+(runner.STATIC/'tf-portal.js').read_text()+check+'</script></body>')

if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()
    check_pages(fixture,a.output_dir+'/navigation',label='Error field navigation')
    for native in [False,True]:check_pages(lambda:tiles(native),a.output_dir+('/android-tiles' if native else '/web-tiles'),widths=(800,320),label='Android tiles' if native else 'Web tiles')
