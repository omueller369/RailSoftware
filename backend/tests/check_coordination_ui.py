# Prüft die echten Chat- und Dienstplanoberflächen mit fiktiven Konten und Excel-Zeilen.
import argparse,re,json
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def base(name,setup,checks,assets):
    html=localize_html((STATIC/name).read_text())
    html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S)
    html=re.sub(r'<link\b[^>]*>','',html)
    css=''.join((STATIC/n).read_text() for n in ['portal.css','responsive.css']+(['tf-chat.css'] if 'messages' in name else []))
    html=html.replace('</head>','<style>'+css+'</style></head>')
    harness=r'''const assert=(v,m)=>{if(!v)throw Error(m);},until=async predicate=>{const deadline=Date.now()+10000;while(!predicate()){if(Date.now()>deadline)throw Error('Timeout: '+document.getElementById('rosterStatus')?.textContent);await new Promise(r=>setTimeout(r,20));}};'''
    scripts='<script>'+setup+'</script>'+''.join('<script src="/tf/'+n+'"></script>' for n in ['messages.js']+assets)
    return html.replace('</body>',scripts+'<script>(async()=>{'+harness+checks+"parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));</script></body>")

def chat():
    setup=r'''
localStorage.clear();window.I18n={t:s=>s,locale:'de-DE'};let sent=null;
const incoming={id:10,created_at:'2026-11-24T10:00:00Z',body:'Hallo <img src=x onerror=alert(1)>',mine:false,read:true};
window.fetch=async(url,options={})=>{let data;if(String(url).endsWith('/account/me'))data={id:7,role:'tf',username:'synthetic'};else if(String(url).endsWith('/recipients'))data=[{id:7,name:'Eigenes Konto',group:'TF'},{id:8,name:'Fiktiver Kontakt',group:'TF'}];else if(String(url).endsWith('/chats'))data=[{peer_id:8,last_at:incoming.created_at,unread:1}];else if(String(url).includes('/chats/8'))data={messages:[incoming,...(sent?[{id:11,created_at:'2026-11-24T10:01:00Z',body:sent.body,mine:true,read:false}]:[])],more:false};else if(options.method==='POST'){sent=JSON.parse(options.body.get('payload'));data={id:11};}else data={};return new Response(JSON.stringify(data));};
'''
    checks=r'''
await until(()=>document.querySelector('#chatContacts button'));document.querySelector('#chatContacts button').click();await until(()=>document.querySelector('.chat-bubble'));
assert(!document.querySelector('.chat-bubble img'),'Message text is not interpreted as HTML');assert(document.querySelector('.chat-bubble').textContent.includes('<img'),'Message contents remain visible');
document.getElementById('chatBody').value='Mein privater Entwurf';document.getElementById('chatBody').dispatchEvent(new Event('input'));assert(localStorage.getItem('rail.chat.draft.7.8')==='Mein privater Entwurf','Draft belongs to the selected account and contact');
document.querySelector('.chat-bubble button').click();assert(document.getElementById('chatBody').value.startsWith('> Hallo'),'Reply quote is editable in the composer');
document.getElementById('chatCompose').dispatchEvent(new Event('submit',{cancelable:true}));await until(()=>sent&&document.querySelector('.chat-bubble.mine'));assert(sent.recipients[0]===8&&sent.subject==='Chat','Sending targets exactly the chosen contact');assert(!localStorage.getItem('rail.chat.draft.7.8'),'Successful send clears only this draft');assert(!document.getElementById('chatBody').disabled,'Composer becomes usable after sending');
document.getElementById('chatContactsSearch').value='kein Treffer';document.getElementById('chatContactsSearch').dispatchEvent(new Event('input'));assert(!document.querySelector('#chatContacts button'),'Contact search filters the list');
'''
    return base('tf-messages.html',setup,checks,['tf-chat.js'])

def roster():
    setup=r'''
history.replaceState(null,'','/admin/dienstplan');window.I18n={t:s=>s,locale:'de-DE'};let confirmed=null,previewEmpty=false;
window.fetch=async(url,options={})=>{let data={id:1,role:'admin',permissions:{planning:2}};if(String(url).endsWith('/recipients'))data=[{id:7,number:'787000',name:'Fiktiver TF'}];if(String(url).endsWith('/preview'))data={id:3,sheets:['test'],sheet:0,header:21,columns:['Lf. Nr.','Tf','Typ der Zugfahrt','Dienstbeginn','Umlaufname','Kommentar','Arbeitszeit (Std):','Vorbereitungs- dienst'],rows:[{row:22,values:['1','Fiktiv 186,187 Vorname','Vollzug','2026-11-24T23:00:00','Wichtiger Umlauf','Übergabehinweis','9','V3']}],suggestions:{'22':7},skipped_pauses:1};if(String(url).endsWith('/preview')&&previewEmpty)data={...data,rows:[],skipped_pauses:2,suggestions:{}};if(String(url).endsWith('/confirm')){confirmed=JSON.parse(options.body);data={count:1};}return new Response(JSON.stringify(data));};
'''
    checks=r'''
await until(()=>!document.getElementById('rosterAdmin').hidden);const file=new File(['synthetic spreadsheet fixture'],'plan.xls'),transfer=new DataTransfer();transfer.items.add(file);document.getElementById('rosterFile').files=transfer.files;
document.getElementById('rosterUpload').dispatchEvent(new Event('submit',{cancelable:true}));await until(()=>!document.getElementById('rosterConfirm').hidden);assert(!confirmed,'Preview does not publish data');assert(document.getElementById('rosterStatus').textContent.includes('Pause-Zeilen übersprungen: 1'),'Skipped pause count is visible in the preview');assert(document.getElementById('rosterHeader').value==='21','Detected header displayed');
const selects=[...document.querySelectorAll('#rosterPreview th select')];assert(selects[0].value===''&&selects[1].value===''&&selects[6].value==='','Ignored columns remain excluded');assert(selects[2].value==='activity'&&selects[4].value==='rotation'&&selects[5].value==='comment'&&selects[7].value==='preparation','Approved fields including hyphenated Excel headings proposed');assert(document.querySelector('#rosterPreview td select').value==='7','Unambiguous TF proposal stays visible for confirmation');
document.getElementById('rosterConfirm').click();await until(()=>confirmed);assert(confirmed.assignments[0].tf_user_id===7&&confirmed.columns.rotation===4,'Confirmation sends explicit field and TF assignment');await until(()=>document.getElementById('rosterConfirm').hidden);assert(!document.getElementById('rosterPreview').children.length&&!document.getElementById('rosterFile').value,'Successful confirmation clears preview and file');
previewEmpty=true;const nextTransfer=new DataTransfer();nextTransfer.items.add(file);document.getElementById('rosterFile').files=nextTransfer.files;document.getElementById('rosterUpload').dispatchEvent(new Event('submit',{cancelable:true}));await until(()=>document.getElementById('rosterStatus').textContent.includes('Pause-Zeilen übersprungen: 2'));assert(document.getElementById('rosterConfirm').hidden&&document.getElementById('rosterStatus').textContent.includes('Keine importierbaren Leistungen'),'A file containing only pauses cannot publish an empty import');
'''
    return base('duty-rosters.html',setup,checks,['duty-rosters.js'])

def defaults():
    setup="window.I18n={t:s=>s,locale:'de-DE'};"
    checks=r'''
const catalogue=[{category:'cause',value:'CTL',active:true,label:'CTL',reason_values:['V1']},{category:'cause',value:'DB-InfraGo',active:true,label:'DB-InfraGo',reason_values:['Zugfolge']},...['V1','V3','Zugfolge','Pause'].map(value=>({category:'reason',value,label:value,active:true}))];refreshTrainJourneyChoices(catalogue);
const editor=new TrainJourneyEditor({userId:7,button:document.getElementById('newTrainJourney'),container:document.getElementById('trainJourneyEditor'),readonly:()=>false,viewOnly:()=>false,bounds:()=>({start:'2026-11-24T08:00',end:'2026-11-24T16:00'}),minute:value=>Date.parse(value)/60000,clock:String,uuid:()=>crypto.randomUUID(),stations(){},resolve:async()=>({code:'AAA',name:'Bahnhof'}),changed(){},editingChanged(){},message(){},block(){}});
editor.restore([{id:'train',train_number:'123',start_station:'AAA',start_station_name:'Bahnhof',end_station:'BBB',end_station_name:'Ziel',start_at:'2026-11-24T09:00',end_at:'2026-11-24T10:00',events:[{id:'event',reason:'V3',cause:'CTL',station:'AAA',start_at:'2026-11-24T10:00',end_at:'2026-11-24T10:20'}]}]);const item=editor.items[0],f=item.eventFields;item.rows.children[0].click();assert(f.reason.value==='V3','Saved historical combination remains visible');assert([...f.reason.options].some(o=>o.value==='V1'),'Assigned active reason available');f.cause.value='DB-InfraGo';f.cause.dispatchEvent(new Event('change'));assert(f.reason.value==='','Changing category clears a disallowed reason');assert([...f.reason.options].filter(o=>o.value).map(o=>o.value).join(',')==='Zugfolge','Only assigned reasons offered');assert(item.ctlPause.hidden,'Unavailable CTL/Pause shortcut hidden');assert(!TrainJourneyPairAllowed('CTL','V3')&&TrainJourneyPairAllowed('CTL','V3',item.events[0]),'Historical exemption does not authorize new combinations');
'''
    return base('tf-portal.html',setup,checks,['train-journeys.js'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    assets={'/tf/'+name:STATIC/name for name in ['messages.js','tf-chat.js','duty-rosters.js','train-journeys.js']}
    for name,fixture in [('chat',chat),('roster',roster),('defaults',defaults)]:check_pages(fixture,args.output_dir+'/'+name,widths=(800,375),assets=assets,label='Coordination '+name,timeout=30)
