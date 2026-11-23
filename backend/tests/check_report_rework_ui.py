# Browserprüfung für Berichte und die zugehörigen Prüf- und Versandabläufe.
"""Actual TF editor: yellow correction row, draft bounds and final synchronization."""
import argparse,re
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def fixture():
    page=localize_html((STATIC/'tf-portal.html').read_text());page=re.sub(r'<script\b[^>]*>.*?</script>|<link\b[^>]*>','',page,flags=re.S)
    css='\n'.join((STATIC/f).read_text() for f in ['tf-portal.css','work-report.css','portal-theme.css','responsive.css'])
    source=(STATIC/'work-report.js').read_text().split('// Die Klappschalter')[0]
    source=re.sub(r'\}\)\(\);\s*$',r'''window.ReworkFixture={loadReport,saveLocal,synchronize,rows:()=>pending,isReadonly:()=>reportViewOnly,setup(editor,report,server){user={id:7};key='report-rework-ui';trainEditor=editor;state={client_id:'new',kind:'Dienstschicht'};pending=[report];monthCache={'2026-11':server};plans={};el('reportPeriod').value='2026-11';renderMonth();}};})();''',source)
    scripts='\n'.join((STATIC/f).read_text() for f in ['messages.js','plan-colors.js','report-tabs.js','station-picker.js','train-journeys.js'])+'\n'+source
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},el=id=>document.getElementById(id),errors=[];window.ReportFeedback={error:value=>errors.push(value)};
 el('workReport').hidden=false;el('reportDetails').hidden=false;
 const returned={report_id:1,version:1,reason:'Bitte Dienstbeginn prüfen',client_id:'11111111-1111-4111-8111-111111111111'},journey={id:'22222222-2222-4222-8222-222222222222',train_number:'123',start_station:'AAA',start_station_name:'Start',end_station:'BBB',end_station_name:'Ziel',start_at:'2026-11-18T07:00',end_at:'2026-11-18T15:00',events:[]};
 let draft={client_id:returned.client_id,start_at:'2026-11-18T08:00',end_at:'2026-11-18T16:00',kind:'Dienstschicht',pause_policy:1,actual_pause:30,overrun_reason:'',trips:[],train_journeys:[journey],_returned:returned,_cloud_revision:1,_cloud_dirty:false,_receipt_keys:[]},revision=1,submitted=0,cloud=0;
 let serverReport={...draft,id:1,client_id:'original',train_journeys:[],returned,version:1,duration_minutes:480,credited_minutes:480,documented_pause_minutes:30},server=()=>({reports:[serverReport],days:[],work_minutes:480,guest_minutes:0,pause_minutes:30});
 window.fetch=async(url,options={})=>{let data;if(url.includes('/work-report-drafts')){if(options.method==='PUT'){const body=JSON.parse(options.body);assert(body.expected_revision===revision,'Optimistic cloud revision');draft={...body.report};revision++;cloud++;}data=url.endsWith('/work-report-drafts')?{drafts:[{client_id:draft.client_id,report:draft,returned,revision,receipt_keys:[],files:[]}],finalized:[]}:{client_id:draft.client_id,report:draft,returned,revision,receipt_keys:[],files:[]};}
 else if(url==='/api/v1/tf/work-reports'&&options.method==='POST'){submitted++;const body=JSON.parse(options.body);assert(body.start_at<=journey.start_at&&body.end_at>=journey.end_at,'Final report must fit duty period');serverReport={...body,id:1,version:2,returned:null,train_revision:1,train_editable:true,locked:false,duration_minutes:540,credited_minutes:540};delete serverReport._returned;data=serverReport;}
 else if(url.endsWith('/train-journeys'))data=serverReport;
 else if(url.includes('/work-reports/month/'))data=server();
 else if(url.endsWith('/receipts')||url.includes('/stations'))data=[];
 else if(url.includes('/portal/plan/'))data={days:[]};
 else throw Error('Unexpected API '+url);
 return {ok:true,status:200,json:async()=>structuredClone(data)};};
 const editor=new window.TrainJourneyEditor({userId:7,button:el('newTrainJourney'),container:el('trainJourneyEditor'),readonly:()=>window.ReworkFixture.isReadonly(),viewOnly:()=>window.ReworkFixture.isReadonly(),bounds:()=>({start:el('dutyStart').value,end:el('dutyEnd').value}),minute:value=>Date.parse(value)/60000,clock:n=>String(n),uuid:()=>crypto.randomUUID(),stations(){},resolve:async input=>({code:input.value.split(' · ')[0],name:'Bahnhof'}),changed(){},editingChanged(){},message(){},block(){}});
 window.ReworkFixture.setup(editor,draft,server());let row=el('reportListRows').rows[0];assert(el('reportListRows').rows.length===1&&row.dataset.syncState==='returned','One correction row, never duplicate duty');assert(getComputedStyle(row.cells[0]).backgroundColor==='rgb(255, 242, 168)','Yellow returned report');
 await window.ReworkFixture.loadReport(draft.client_id,true);assert(!el('dutyFields').disabled&&!el('saveReport').hidden&&!el('syncReport').hidden,'Whole returned report editable');assert(el('deleteDraftReport').hidden,'Correction cannot be discarded');assert(el('reportMessage').textContent.includes('Bitte Dienstbeginn prüfen'),'Return reason visible');
 assert(await window.ReworkFixture.saveLocal(false),'Interim save before duty bounds allowed');assert(window.ReworkFixture.rows()[0].train_journeys[0].start_at==='2026-11-18T07:00','No automatic time trimming');assert(cloud>0,'Out-of-duty complete draft also backed up on server');
 await window.ReworkFixture.synchronize();assert(submitted===0&&errors.length>0,'Final synchronization blocked outside duty');
 el('dutyStart').value='2026-11-18T07:00';await window.ReworkFixture.synchronize();assert(submitted===1,'Corrected report submitted exactly once');assert(window.ReworkFixture.rows().length===0,'Correction draft cleared after success');assert(el('reportListRows').rows.length===1&&el('reportListRows').rows[0].dataset.syncState==='synced','Single synchronized row restored');assert(el('reportListRows').rows[0].cells[0].textContent.includes('v2'),'New version visible');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')


def fixture_admin():
    from check_admin_work_reports_ui import fixture as original
    page=original();start=page.index('const calls=[],person=');end=page.index('(()=>{',start)
    mocks=r'''
let returned=false,posted=0;const calls=[],person={id:7,name:'TF Beispiel',personnel_number:'007',employee_category:'tf'};window.confirm=()=>true;
window.fetch=async(url,options={})=>{calls.push(url);let data;if(options.method==='POST'){const body=JSON.parse(options.body);if(!url.endsWith('/return')||body.expected_version!==1||body.reason!=='Bitte Ankunft prüfen')throw Error('Wrong return request');returned=true;posted++;data={client_id:'correction'};}else if(url.endsWith('/employees'))data=[person];else if(/\/12$/.test(url))data={can_return:true,employee:person,report:{id:12,version:1,returned:returned?{reason:'Bitte Ankunft prüfen'}:null,versions:returned?[{version:1}]:[],start_at:'2026-11-12T08:00',end_at:'2026-11-12T16:00',kind:'Dienstschicht',duration_minutes:480,documented_pause_minutes:30,trips:[],train_journeys:[]}};else data={total:1,items:[{id:12,employee:person,start_at:'2026-11-12T08:00',end_at:'2026-11-12T16:00',kind:'Dienstschicht',duration_minutes:480}]};return {ok:true,status:200,json:async()=>data};};
'''
    page=page[:start]+mocks+page[end:];start=page.index('(async()=>{\n const assert=')
    checks=r'''
(async()=>{const assert=(v,m)=>{if(!v)throw Error(m);};for(let i=0;i<100&&!document.querySelector('#reportRows button');i++)await new Promise(r=>setTimeout(r,0));document.querySelector('#reportRows button').click();await new Promise(r=>setTimeout(r,0));const form=document.getElementById('reportReturnForm');assert(!form.hidden,'Writer can return unlocked TF report');document.getElementById('reportReturnReason').value='Bitte Ankunft prüfen';await form.onsubmit({preventDefault(){},target:form});assert(posted===1&&form.hidden,'Returned report cannot be returned a second time');assert(document.getElementById('reportDetailBody').textContent.includes('Bitte Ankunft prüfen'),'Return reason shown in management');assert([...document.querySelectorAll('#reportDetailBody button')].some(n=>n.textContent==='Version 1 · PDF'),'Previous PDF version can be opened');window.parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page[:start]+checks+'</script></body></html>'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir+'/tf',label='Returned work report',timeout=40)
    check_pages(fixture_admin,a.output_dir+'/admin',widths=(800,375),label='Management report return')
