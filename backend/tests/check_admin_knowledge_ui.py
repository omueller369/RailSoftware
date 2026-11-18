"""Shared real map and inventories: TF switching, server-only privacy, staff editing."""
import argparse,re
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def fixture():
    tf=(STATIC/'tf-portal.html').read_text()
    section='<section id="routeKnowledge"'+tf.split('<section id="routeKnowledge"',1)[1].split('<section id="updatesModule"',1)[0]
    section=section.replace('id="routeKnowledge" hidden','id="routeKnowledge"').replace('<h1>{{knowledge_tabs.text_ffad8a8eb545}}</h1>','').replace('<p>{{knowledge_tabs.text_1308485034f1}}</p>','').replace('<p>{{portal_beta60.text_a6fd4b95ede8}}</p>','')
    page=localize_html((STATIC/'admin-knowledge.html').read_text().replace('<!-- KNOWLEDGE -->',section))
    page=re.sub(r'<script\b[^>]*>.*?</script>|<link\b[^>]*>','',page,flags=re.S)
    scripts='\n'.join((STATIC/name).read_text() for name in ['messages.js','station-picker.js','location-editor.js','admin-knowledge.js','knowledge-inventory.js','route-coverage.js','rail-network.js','route-imports.js','route-csv.js','route-knowledge.js'])
    scripts=scripts.replace("document.addEventListener('DOMContentLoaded',init,{once:true});",'')
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','portal-theme.css','responsive.css'])
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},wait=()=>new Promise(r=>setTimeout(r,0));
 window.I18n={t:s=>s,locale:'de-DE'};
 let cacheReads=0;indexedDB.open=()=>{cacheReads++;throw Error('Private TF cache read');};window.GpsRecorder={localRecords:()=>{cacheReads++;throw Error('Private TF GPS read');}};
 window.RouteKnowledgeTileUrl='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1ioAAAAASUVORK5CYII=';
 const people=[{id:7,first_name:'Anna',last_name:'Adler',tf_number:'700007',personnel_number:'P7'},{id:8,first_name:'Bert',last_name:'Bach',tf_number:'800008',personnel_number:'P8'}];let readonly=false,late=null,releaseWrite=null,held=false,requests=[];
 const classes={7:[{id:71,series:'0186',valid_until:'2029-10-06',revision:'a'.repeat(64)}],8:[{id:81,series:'0245',valid_until:'2028-02-01',revision:'b'.repeat(64)}]},response=data=>({ok:true,status:200,json:async()=>data});
 window.fetch=async(url,options={})=>{
  requests.push([url,options.method||'GET']);
  if(url==='/api/v1/admin/me')return response({permissions:{knowledge:readonly?1:2}});
  if(url==='/api/v1/admin/knowledge/drivers')return response({items:people,can_write:!readonly});
  const match=url.match(/^\/api\/v1\/admin\/knowledge\/(7|8)(\/.*)$/);assert(match,'Every employee data request uses the selected administrative context: '+url);const id=+match[1],path=match[2],identity={owner_id:id,first_name:people[id-7].first_name,last_name:people[id-7].last_name,tf_number:people[id-7].tf_number};
  if(options.method){assert(!readonly,'Reader never writes');const body=JSON.parse(options.body);if(path.startsWith('/series')){assert(id===8,'Write remains on selected TF');held=true;await new Promise(resolve=>releaseWrite=resolve);if(options.method==='PATCH')Object.assign(classes[id][0],body,{revision:'c'.repeat(64)});else classes[id].push({id:82,...body,revision:'d'.repeat(64)});return response({identity});}}
  if(path==='/knowledge/classes'){if(id===7&&late){const old=classes[7].map(r=>({...r}));return new Promise(resolve=>late.resolve=()=>resolve(response({identity,items:old})));}return response({identity,items:classes[id]});}
  if(path==='/knowledge/places')return response({identity,items:[{id:id*10,station_name:'Station '+id,ds100:'T'+id,known_until:'2027-03-01'}],date_limits:{today:'2026-11-18',max_until:'2027-11-18',warning_until:'2027-02-18'}});
  if(path.startsWith('/route-knowledge?'))return response({owner_id:id,items:[],next_offset:null});
  if(path==='/route-knowledge/imports')return response({identity,items:[]});
  throw Error('Unexpected request '+url);
 };
 await window.RailNetwork.load();await window.startAdminKnowledge();const picker=document.getElementById('knowledgeDriver'),search=document.getElementById('knowledgeDriverSearch');
 search.value='800008';search.oninput();assert(picker.options.length===2&&picker.options[1].value==='8','Search matches TF number');search.value='';search.oninput();
 picker.value='7';await picker.onchange();assert(document.querySelector('[data-rail-network]'),'Real complete offline reference rendered');
 const expected=['Unbekannt','Im Bau DB InfaGo','Nicht DB InfaGo Netz','Im Erwerb','Streckenkundig','Im Ablauf','abgelaufen'];assert([...document.querySelectorAll('.route-network-legend span')].map(n=>n.textContent).join('|')===expected.join('|'),'Exact requested labels shared with TF');
 const colors=['rgb(74, 74, 74)','rgb(139, 131, 120)','rgb(255, 255, 0)','rgb(67, 110, 238)','rgb(124, 252, 0)','rgb(255, 140, 0)','rgb(255, 0, 0)'];assert([...document.querySelectorAll('.route-network-swatch')].every((n,i)=>getComputedStyle(n).borderTopColor===colors[i]),'All seven legend colors');
 document.getElementById('knowledgeTab-classes').click();assert(document.getElementById('knowledgeClassesWorkspace').textContent.includes('0186'),'A classes loaded');
 late={};const old=picker.onchange();await wait();picker.value='8';await picker.onchange();late.resolve();await old;await wait();
 document.getElementById('knowledgeTab-classes').click();const root=document.getElementById('knowledgeClassesWorkspace');assert(root.textContent.includes('0245')&&!root.textContent.includes('0186'),'Late A response never overwrites B');
 const row=root.querySelector('[data-knowledge-saved] tbody tr');row.click();assert(root.querySelector('[data-series-value]').value==='0245','Click selects existing class');const date=root.querySelector('[data-series-date]');date.value='2029-01-01';const saving=root.querySelector('form').onsubmit({preventDefault(){}});while(!held)await wait();assert(picker.disabled&&search.disabled,'TF selector locked during mutation');releaseWrite();await saving;assert(root.textContent.includes('01.01.2029'),'Edited class reloaded with German date');assert(!picker.disabled,'TF selector restored');
 held=false;root.querySelector('[data-series-reset]').click();root.querySelector('[data-series-value]').value='0012';date.value='2030-01-01';const adding=root.querySelector('form').onsubmit({preventDefault(){}});while(!held)await wait();releaseWrite();await adding;assert(root.textContent.includes('0012'),'New class retains leading zeros');assert(classes[7].length===1,'Other TF inventory unchanged');
 assert(cacheReads===0,'No TF device database or GPS access');
 readonly=true;await window.startAdminKnowledge();picker.value='8';await picker.onchange();document.getElementById('knowledgeTab-classes').click();assert(!document.querySelector('[data-series-value]')&&!document.querySelector('[data-location-code]'),'Reader has no editors');assert([...document.querySelectorAll('input[type=file]')].every(n=>n.closest('label').hidden),'Reader has no import chooser');assert(cacheReads===0,'Reader also server-only');
 assert(document.querySelector('.route-knowledge-map').getBoundingClientRect().width<=innerWidth,'Map fits screen');
 const allowedFetch=window.fetch;window.fetch=async(url,options)=>url.includes('/api/v1/admin/knowledge/8/')?{ok:false,status:403,json:async()=>({})}:allowedFetch(url,options);await picker.onchange();assert(document.getElementById('adminKnowledgeBody').hidden&&picker.disabled&&search.disabled,'Revoked access clears data and locks selection');assert(document.getElementById('adminKnowledgeMessage').textContent.includes('Leserechte'),'Revocation message is retained');
 window.fetch=allowedFetch;await window.startAdminKnowledge();picker.value='8';await picker.onchange();
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()
    check_pages(fixture,a.output_dir,assets={'/tf/rail-network-data.js':STATIC/'rail-network-data.js'},label='Administrative knowledge')
