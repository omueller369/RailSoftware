# Browserprüfung für die gemeinsamen Anwendungsabläufe.
"""Real PDF.js page rendering, regions, offline isolation and inert portal login."""
import argparse,re,json,base64,hashlib
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html
from la_sample import sample_pdf

def fixture():
    source=localize_html((STATIC/'tf-portal.html').read_text());source=re.sub(r'<script\b[^>]*>.*?</script>|<link\b[^>]*>','',source,flags=re.S)
    css='\n'.join((STATIC/f).read_text() for f in ['tf-portal.css','portal-theme.css','responsive.css','la-instructions.css'])
    scripts='\n'.join((STATIC/f).read_text() for f in ['messages.js','la-instructions.js'])
    setup='const samplePdf='+json.dumps(base64.b64encode(sample_pdf()).decode())+',hash='+json.dumps(hashlib.sha256(sample_pdf()).hexdigest())+';'
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},root=document.getElementById('laInstructionsWorkspace');document.getElementById('laInstructions').hidden=false;
 window.I18n={t:s=>s,locale:'de-DE'};let mode='online',owner=7,pdfRequests=0;const nativeFetch=window.fetch.bind(window),requests=[],data=[{id:1,region:'nord',title:'La Nord Test',edition:'Test 1',valid_from:'2020-01-01',valid_until:'2099-12-31',filename:'La Nord – gültig.pdf',content_sha256:hash},{id:2,region:'ost',title:'La Ost alt',edition:'Alt',valid_from:'2000-01-01',valid_until:'2000-01-02',filename:'Alt.pdf',content_sha256:hash}];
 window.fetch=async(url,options={})=>{if(typeof url!=='string'||!url.startsWith('/api/'))return nativeFetch(url,options);requests.push(url);if(mode==='offline')throw Error('offline');if(mode==='denied')return new Response('{}',{status:403,headers:{'Content-Type':'application/json'}});if(url.endsWith('/pdf')){pdfRequests++;return new Response(Uint8Array.from(atob(samplePdf),c=>c.charCodeAt(0)),{headers:{'Content-Type':'application/pdf'}});}return new Response(JSON.stringify({owner_id:owner,can_write:false,items:data}),{headers:{'Content-Type':'application/json'}});};
 let exported=null;window.AndroidPortal={saveBlob:async(name,blob)=>exported={name,blob}};
 let module=await window.startLaInstructions({id:7},root);const select=root.querySelector('[data-la-region]');assert(select.options.length===8,'All seven regions plus all-regions filter');assert(root.querySelectorAll('[data-la-id]').length===2,'Published PDFs visible');assert(root.querySelector('[data-la-id="2"]').dataset.validity==='expired','Expired PDF clearly labelled');select.value='nord';select.onchange();assert(root.querySelectorAll('[data-la-id]').length===1,'Region filter');
 const portal=root.querySelector('[data-la-login]');assert(portal.disabled&&portal.querySelector('button').disabled&&[...portal.querySelectorAll('input')].every(n=>n.disabled&&!n.name),'DB login and fields inert, no credential fields submitted');
 await module.show(data[0]);const canvas=root.querySelector('canvas');assert(canvas.width>0&&canvas.dataset.laPage==='1','Actual PDF.js renders page 1 inside Android-style adapter');const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let ink=0;for(let i=0;i<pixels.length;i+=4)if(pixels[i+3]&&pixels[i]<100&&pixels[i+1]<100)ink++;assert(ink>30,'Text ink actually drawn, not empty iframe or fake preview');
 const next=[...root.querySelectorAll('.la-preview button')].find(n=>n.textContent==='Nächste Seite');await next.onclick();assert(canvas.dataset.laPage==='2','Page navigation renders second page');
 await module.action(data[0],'save');await module.action(data[0],'download');assert(exported.name==='La Nord – gültig.pdf'&&exported.blob.type==='application/pdf','Native save dialog receives PDF and full UTF-8 filename');
 const fetched=pdfRequests;await module.dispose();mode='offline';module=await window.startLaInstructions({id:7},root);assert(root.textContent.includes('Offline-Bestand'),'Explicit offline catalogue banner');await module.show(data[0]);assert(root.querySelector('canvas').dataset.laPage==='1'&&pdfRequests===fetched,'Saved PDF preview works offline without server or external viewer');
 await module.dispose();owner=8;module=await window.startLaInstructions({id:8},root);assert(!root.querySelector('[data-la-id]'),'Other account never receives this device catalogue');await module.show(data[0]);assert(!root.querySelector('canvas').width,'Other account never reads saved PDF');
 await module.dispose();owner=7;mode='online';module=await window.startLaInstructions({id:7},root);mode='denied';await module.reload();assert(!root.querySelector('[data-la-id]')&&root.querySelector('[data-la-preview]').hidden,'Revoked access clears displayed catalogue and preview');await module.dispose();mode='offline';module=await window.startLaInstructions({id:7},root);assert(!root.querySelector('[data-la-id]'),'Revoked account cache was purged');await module.dispose();
 mode='online';module=await window.startLaInstructions({id:7},root);await module.show(data[0]);assert(root.querySelector('canvas').getBoundingClientRect().width<=innerWidth,'PDF fits tablet and phone viewport');assert(!requests.some(url=>url.includes('login')),'No DB login request issued');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return source.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+setup+checks+'</script></body>')


def fixture_admin():
    source=fixture();start=source.index('(async()=>{\n const assert=')
    checks=r"""
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},root=document.getElementById('laInstructionsWorkspace');document.getElementById('laInstructions').hidden=false;
 window.I18n={t:s=>s,locale:'de-DE'};indexedDB.open=()=>{throw Error('Admin must not read private TF caches');};let writable=true,uploads=0,removed=0;
 const rows=[{id:1,region:'nord',title:'La Nord',edition:'Test',valid_from:'2020-01-01',valid_until:'2099-12-31',filename:'La.pdf',content_sha256:hash}];
 window.fetch=async(url,options={})=>{assert(url.startsWith('/api/v1/admin/la-instructions'),'Admin context on every data request');if(options.method==='POST'){assert(writable,'Reader cannot publish');assert(options.body.get('region')==='west'&&options.body.get('title')==='La West'&&options.body.get('edition')==='Test 2','Metadata in multipart form');assert((await options.body.get('file').text()).startsWith('%PDF-'),'Actual PDF attached');uploads++;rows.push({...rows[0],id:2,region:'west',title:'La West'});return new Response('{"id":2}',{status:201});}if(options.method==='DELETE'){assert(writable,'Reader cannot delete');removed++;rows.splice(0,1);return new Response('{"ok":true}');}return new Response(JSON.stringify({owner_id:1,can_write:writable,items:rows}),{headers:{'Content-Type':'application/json'}});};
 let module=await window.startLaInstructions({id:1},root,{admin:true});const form=root.querySelector('form');assert(!form.hidden,'Publisher form visible');for(const [name,value]of Object.entries({region:'west',name:'La West',edition:'Test 2',from:'2026-11-18',until:'2026-11-24'}))form.elements.namedItem(name).value=value;
 const files=new DataTransfer();files.items.add(new File([Uint8Array.from(atob(samplePdf),c=>c.charCodeAt(0))],'La West.pdf',{type:'application/pdf'}));form.elements.namedItem('file').files=files.files;await form.onsubmit({preventDefault(){}});assert(uploads===1&&root.querySelectorAll('[data-la-id]').length===2,'Published PDF appears in correct catalogue');
 window.confirm=()=>true;await module.action(rows[0],'delete');assert(removed===1&&root.querySelectorAll('[data-la-id]').length===1,'Delete confirmed and catalogue refreshed');assert(!root.querySelector('[data-la-action=save]'),'Administration never stores private offline PDFs');await module.dispose();writable=false;module=await window.startLaInstructions({id:1},root,{admin:true});assert(root.querySelector('form').hidden&&!root.querySelector('[data-la-action=delete]'),'Read-only staff have no publication or deletion controls');await module.dispose();
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
"""
    return source[:start]+checks+'</script></body></html>'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()
    assets={'/tf/la-vendor/'+str(f.relative_to(STATIC/'la-vendor')):f for f in (STATIC/'la-vendor').rglob('*') if f.is_file()}
    check_pages(fixture,a.output_dir+'/tf',assets=assets,label='La PDF preview and offline accounts',timeout=60)
    check_pages(fixture_admin,a.output_dir+'/admin',widths=(800,375),label='La PDF publication and read-only staff')
