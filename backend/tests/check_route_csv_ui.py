"""Real file input, preview/apply, original values, private cache and owner isolation."""
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC

def fixture():
    scripts='\n'.join((STATIC/name).read_text() for name in ['messages.js','route-csv.js'])
    checks=r'''
window.I18n={t:s=>s,locale:'de-DE'};
let owner=7,online=true,rows=[],writes=0,previews=0;Object.defineProperty(navigator,'onLine',{get:()=>online});
const records=[{id:1,section:'A <b> B',route_number:'1000',status:'streckenkundig',valid_until:'2027-02-03',acquired_since:'-',acquisition_trips:'-',from_code:'AAA',to_code:'BBB'},{id:2,section:'B - C',route_number:'0',status:'wird erworben',valid_until:'0000-00-00',acquired_since:'2025-06-03',acquisition_trips:'4',from_code:'X.001',to_code:'X.002'}];
const identity=()=>({owner_id:owner,tf_number:owner===7?'787100':'787101',first_name:'Mira',last_name:'Beispiel'}),requests=[];
window.fetch=async(url,options={})=>{requests.push(url);if(!online)throw Error('Network offline');let body;if(options.method==='POST'){const file=options.body.get('file');if(!file||!file.name.endsWith('.csv'))throw Error('Real CSV File required');if(url.endsWith('/preview')){previews++;body={identity:identity(),owner_token:'target-'+owner,summary:{file_sha256:'f'.repeat(64),source_rows:2,added:rows.length?0:2,existing:rows.length,conflicts:0,duplicates:0,unknown_dates:1,statuses:{streckenkundig:1,'wird erworben':1}}};}else{if(options.body.get('confirmed')!=='true'||options.body.get('owner_token')!=='target-'+owner||options.body.get('expected_sha256')!=='f'.repeat(64))throw Error('Binding or confirmation missing');writes++;rows=structuredClone(records);body={identity:identity(),summary:{added:2,existing:0,conflicts:0}};}}else body={identity:identity(),items:structuredClone(rows)};return {ok:true,status:200,json:async()=>body};};
(async()=>{
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);},root=document.getElementById('csv');await window.RouteCsv.mount({id:7},root);
 const file=root.querySelector('[data-route-csv-file]'),inspect=root.querySelector('[data-route-csv-inspect]'),apply=root.querySelector('[data-route-csv-apply]');assert(file,'File input survives translation rendering');
 const transfer=new DataTransfer();transfer.items.add(new File(['Streckenabschnitt;VzG-Nummer;Status;Gültig bis;Erwerb seit;Erwerbsfahrten;Von;Bis\nA;1000;streckenkundig;2027-02-03;-;-;AAA;BBB'],'Kenntnisse.csv',{type:'text/csv'}));file.files=transfer.files;file.dispatchEvent(new Event('change'));await inspect.onclick();
 assert(previews===1&&writes===0,'Preview is read-only');assert(!root.querySelector('[data-route-csv-preview]').hidden,'Preview displayed');assert(root.querySelector('[data-route-csv-preview]').textContent.includes('787100')&&root.querySelector('[data-route-csv-preview]').textContent.includes('Mira Beispiel'),'Target name and TF number visible before applying');
 await apply.onclick();assert(writes===1,'One explicit server import');assert(root.querySelectorAll('tbody tr').length===2,'Imported rows shown');assert(root.querySelector('tbody').textContent.includes('0000-00-00'),'Zero-date placeholder unchanged');assert(root.querySelector('tbody').textContent.includes('A <b> B')&&!root.querySelector('tbody b'),'CSV text is not interpreted as HTML');
 assert((await window.RouteCsv.cache(7)).items.length===2,'Own snapshot saved in real IndexedDB');assert(await window.RouteCsv.cache(8)===null,'Private snapshot never read under other TF');await window.RouteCsv.cache(8,{identity:{owner_id:7},items:[]}).then(()=>{throw Error('Cross-owner cache write accepted');},()=>{});
 const search=root.querySelector('[data-route-csv-search]');search.value='X.001';search.dispatchEvent(new Event('input'));assert(root.querySelectorAll('tbody tr').length===1,'Search by original code');search.value='';search.dispatchEvent(new Event('input'));root.querySelector('[data-route-csv-status]').value='streckenkundig';root.querySelector('[data-route-csv-status]').dispatchEvent(new Event('change'));assert(root.querySelectorAll('tbody tr').length===1,'Status filter');
 online=false;const offline=document.createElement('section');document.body.append(offline);await window.RouteCsv.mount({id:7},offline);assert(offline.querySelectorAll('tbody tr').length===2,'Stored personal list usable offline');assert(offline.querySelector('[data-route-csv-inspect]').disabled,'Offline import unavailable');
 const other=document.createElement('section');document.body.append(other);await window.RouteCsv.mount({id:8},other);assert(other.querySelectorAll('tbody tr').length===0,'Other account has no previous private rows');assert(requests.every(url=>url.includes('/route-knowledge/imports')),'Importer never calls GPS endpoints');assert(document.documentElement.scrollWidth<=innerWidth+1,'CSV table scrolls within the page even on narrow screens');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','portal-theme.css','responsive.css'])
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main><section class="train-panel"><section id="csv"></section></section></main><script>'+scripts+checks+'</script></body></html>'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,label='Private route CSV import')
