"""Shared personnel form in dispatcher context: defaults, create/edit and read-only."""
import argparse,re
from pathlib import Path
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def fixture():
    raw=(STATIC/'staff.html').read_text()
    # Use the same four substitutions as the server's dispatcher page.
    import hashlib
    def key(name):return 'dispatch_tracking.text_'+hashlib.sha256(name.encode()).hexdigest()[:12]
    for old in ['text_045e24cbddab','text_ae186dd21359','text_a3d928778935']:
        raw=raw.replace('{{backend_staff.'+old+'}}','{{'+key('dispatchers')+'}}')
    raw=raw.replace('{{backend_staff.text_0f51c3a734c4}}','{{'+key('new')+'}}')
    page=localize_html(raw);page=re.sub(r'<script\b[^>]*>.*?</script>|<link\b[^>]*>','',page,flags=re.S)
    setup=r'''
history.replaceState({},'', '/admin/dispatchers');
window.employeeEmailField=async()=>{};window.I18n={t:s=>s,locale:'de-DE'};const inventory=[],calls=[];
window.fetch=async(url,options={})=>{calls.push([url,options.method||'GET']);let data;
 if(url==='/api/v1/account/me')data={password_change_required:false};
 else if(url==='/api/v1/admin/me')data={id:1,role:'admin',permissions:{dispatchers:3,tracking:3,staff:0}};
 else if(url==='/api/v1/admin/modules')data=[{id:'dispatchers',label:'Disponenten',maximum_level:3},{id:'tracking',label:'Zugverfolgung',maximum_level:3}];
 else if(url==='/api/v1/admin/dispatchers'&&!options.method)data=inventory.map(r=>({...r}));
 else if(url.startsWith('/api/v1/admin/dispatchers')&&options.method){const body=JSON.parse(options.body);if(options.method==='POST'){inventory.push({id:42,...body,has_photo:false,password_change_required:true});data={id:42};}else{Object.assign(inventory[0],body);data=inventory[0];}}
 else throw Error('Unexpected or wrong staff context: '+url);
 return {ok:true,status:200,json:async()=>data};};
'''
    scripts='\n'.join((STATIC/f).read_text() for f in ['messages.js','photo-ui.js','staff.js'])
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},tick=()=>new Promise(r=>setTimeout(r,0));while(!me||!modules.length)await tick();await tick();
 assert(document.querySelector('header h1').textContent==='Disponenten','Correct dispatcher page name');assert(!el('new').hidden,'Admin create control');el('new').click();
 const trackingRow=[...el('permissions').rows].find(r=>r.dataset.module==='tracking');assert(trackingRow.querySelector('[data-level="1"]').checked&&!trackingRow.querySelector('[data-level="2"]').checked,'Tracking read defaults to enabled');
 const form=el('staffForm');for(const [key,value]of Object.entries({personnel_number:'007',first_name:'Mira',last_name:'Disposition',username:'dispatch-demo',initial_password:'demo-secret-12345',nationality:'deutsch',birth_date:'1990-05-12',cost_center:'D-01',email:'dispatcher@example.org'}))form.elements[key].value=value;
 const address={street:'Teststraße',house_number:'2',postal_code:'01234',city:'Testort'};for(const input of el('addresses').querySelectorAll('input'))input.value=address[input.dataset.field];
 await form.onsubmit({preventDefault(){},target:form});assert(inventory.length===1&&inventory[0].permissions.tracking===1,'Create targets dispatcher stock and default permission');assert(inventory[0].personnel_number==='007'&&inventory[0].addresses[0].postal_code==='01234','Leading zeros and identical staff fields preserved');assert(el('users').textContent.includes('Mira Disposition'),'Dispatcher listing reloaded');assert([...el('users').querySelectorAll('a')].every(a=>a.getAttribute('href').startsWith('/admin/dispatchers?id=')),'View/edit links retain dispatcher context');
 edit(inventory[0]);form.elements.last_name.value='Disposition Neu';await form.onsubmit({preventDefault(){},target:form});assert(inventory[0].last_name==='Disposition Neu','Existing dispatcher edited');
 me={...me,role:'staff',permissions:{dispatchers:1,tracking:1,staff:0}};edit(inventory[0],true);assert(el('save').hidden&&el('resetAccount').hidden&&form.elements.first_name.disabled,'Reader cannot edit or reset');
 assert(calls.filter(([,method])=>method==='POST'||method==='PUT').every(([url])=>url.startsWith('/api/v1/admin/dispatchers')),'No normal employee stock is mutated');
 assert(document.body.scrollWidth<=innerWidth+1,'Personnel form fits narrow screen');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    css=(STATIC/'responsive.css').read_text()
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+setup+scripts+checks+'</script></body>')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,label='Dispatcher personnel')
