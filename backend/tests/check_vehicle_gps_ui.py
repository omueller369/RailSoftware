# Browserprüfung der optionalen Tfz-Auswahl und der getrennten Verwaltungsübersicht.
import argparse,re
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def fixture():
    setup=r'''
let connected=true,nativeRunning=false,nativeKey='',nativePoints=[],lastPayload=null,revision=0;
Object.defineProperty(navigator,'onLine',{get:()=>connected});window.I18n={t:s=>s};window.confirm=()=>true;
window.AndroidPortal={gps:async(method,value)=>{if(method==='start'){nativeRunning=true;nativeKey=value.key;const now=Date.now();nativePoints=[{t:now,lat:52,lon:13,accuracy:5},{t:now+5000,lat:52.001,lon:13,accuracy:5}];return {};}if(method==='stop'){nativeRunning=false;return {};}return {running:nativeRunning&&nativeKey===value.key,paused:false,points:nativeKey===value.key?nativePoints.filter(p=>p.t>(value.after||0)):[]};}};
window.fetch=async(url,options={})=>{if(!connected)throw TypeError('offline');if(String(url).endsWith('/brake-sheets/vehicles'))return new Response(JSON.stringify([{id:14,vehicle_number:'91 80 6185 001-2',series:'185'},{id:15,vehicle_number:'91 80 6185 002-0',series:'185'}]));if(options.method==='PUT'){lastPayload=JSON.parse(options.body);return new Response(JSON.stringify({...lastPayload,revision:++revision,analysis:{rows:[],gaps:[]}}));}return new Response('{}',{status:404});};
'''
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},wait=()=>new Promise(r=>setTimeout(r,25)),until=async fn=>{for(let i=0;i<200&&!fn();i++)await wait();assert(fn(),'UI task completed');};
 localStorage.clear();await new Promise((resolve,reject)=>{const open=indexedDB.open('lokzeitleiste.gps',1);open.onupgradeneeded=()=>open.result.createObjectStore('tracks',{keyPath:'key'});open.onerror=()=>reject(open.error);open.onsuccess=()=>{const db=open.result,tx=db.transaction('tracks','readwrite');tx.objectStore('tracks').clear();tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>reject(tx.error);};});
 const opts={userId:7,journeyId:'11111111-1111-4111-8111-111111111111',container:document.getElementById('gps'),trainNumber:()=>'123',readonly:()=>false,stations(){},selectedEndpoint:kind=>({code:kind==='start'?'AAA':'BBB',name:kind})};
 const recorder=GpsRecorder.mount(opts);await recorder.readyPromise;recorder.setExpanded(true);await until(()=>recorder.vehicleSelect.options.length===3);
 assert(!recorder.vehicleSelect.required,'Tfz selection is optional');recorder.vehicleSelect.value='14';recorder.vehicleSelect.dispatchEvent(new Event('change'));connected=false;
 await recorder.start();await recorder.nativeRead();assert(recorder.record.vehicle_id===14,'Vehicle assigned before native GPS starts');assert(recorder.vehicleSelect.disabled,'Assignment locked during recording');
 await recorder.stop(false);let saved=await GpsRecorder.localRecord(7,opts.journeyId);assert(saved.vehicle_id===14&&saved.ended&&saved.dirty,'Offline finish retains selected vehicle durably');
 connected=true;await GpsRecorder.flushAndroid(7);saved=await GpsRecorder.localRecord(7,opts.journeyId);assert(lastPayload.vehicle_id===14&&saved.vehicle_id===14&&!saved.dirty,'Background reconnect transfers the same assignment');
 const second=GpsRecorder.mount({...opts,journeyId:'22222222-2222-4222-8222-222222222222',container:document.getElementById('second')});await second.readyPromise;second.setExpanded(true);await until(()=>second.vehicleSelect.options.length===3);await second.start();await second.nativeRead();assert(second.record.vehicle_id===null,'Recording starts without any vehicle');await second.stop(false);assert(lastPayload.vehicle_id===null,'Unassigned recording remains unassigned');
 connected=false;const third=GpsRecorder.mount({...opts,journeyId:'33333333-3333-4333-8333-333333333333',container:document.getElementById('third')});await third.readyPromise;third.setExpanded(true);await until(()=>third.vehicleSelect.options.length===3);third.vehicleSelect.value='15';third.vehicleSelect.dispatchEvent(new Event('change'));await third.start();await third.nativeRead();await third.stop(false);saved=await GpsRecorder.localRecord(7,third.o.journeyId);assert(saved.vehicle_id===15,'Cached catalogue allows choosing a vehicle while offline');
 parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+(STATIC/'work-report.css').read_text()+'</style></head><body><div id="gps"></div><div id="second"></div><div id="third"></div><script src="/tf/messages.js"></script><script>'+setup+'</script><script src="/tf/gps.js"></script><script>'+checks+'</script></body></html>'

def fixture_admin():
    page=localize_html((STATIC/'vehicles.html').read_text());page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    setup=r'''
window.I18n={t:s=>s,locale:'de-DE'};window.confirm=()=>true;window.fetch=async url=>{let value;url=String(url);if(url.endsWith('/account/me'))value={id:1,role:'admin'};else if(url.endsWith('/leasing'))value=[];else if(url.includes('/gps-journeys')){const offset=Number(new URL(url,location.href).searchParams.get('offset'));value={items:Array.from({length:offset?1:10},()=>({date:'11.11.2026',time:'00.30',tf_number:'012345',from_code:'AAA',to_code:'BBB',total_km:1.001})),next_offset:offset?null:10,total:11};}else value=[{id:14,vehicle_number:'91 80 6185 001-2',name:'Testlok',status:'ready',status_label:'Verfügbar',has_gps_journeys:true},{id:15,vehicle_number:'91 80 6185 002-0',name:'Andere Lok',status:'ready',status_label:'Verfügbar',has_gps_journeys:false}];return new Response(JSON.stringify(value));};
'''
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},until=async fn=>{for(let i=0;i<200&&!fn();i++)await new Promise(r=>setTimeout(r,20));assert(fn(),'UI finished');};
 await until(()=>document.querySelector('[data-vehicle-gps]'));assert(document.querySelectorAll('[data-vehicle-gps]').length===1,'Only vehicle with data offers the button');document.querySelector('[data-vehicle-gps]').click();await until(()=>document.querySelector('[data-vehicle-gps-dialog] tbody tr'));
 const dialog=document.querySelector('[data-vehicle-gps-dialog]');assert(dialog.open,'Button opens the separate journey table');assert([...dialog.querySelectorAll('th')].map(n=>n.textContent).join('|')==='Datum|Uhrzeit|Tf-Nummer|Von (DS100)|Bis (DS100)|Gesamt km','All requested columns');assert(dialog.querySelector('tbody tr').textContent.includes('00.30')&&dialog.querySelector('tbody tr').textContent.includes('012345'),'Time format and leading-zero TF number retained');assert(dialog.querySelectorAll('tbody tr').length===10,'Default page contains ten rows');[...dialog.querySelectorAll('button')].find(b=>b.textContent==='Weiter').click();await until(()=>dialog.querySelectorAll('tbody tr').length===1);assert([...dialog.querySelectorAll('button')].find(b=>b.textContent==='Weiter').disabled,'Final page stops paging');dialog.querySelector('button').click();await until(()=>!document.querySelector('[data-vehicle-gps-dialog]'));parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</body>','<script src="/tf/messages.js"></script><script>'+setup+'</script><script>'+(STATIC/'vehicles.js').read_text()+'</script><script>'+checks+'</script></body>')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args();assets={'/tf/messages.js':STATIC/'messages.js','/tf/gps.js':STATIC/'gps.js'};check_pages(fixture,args.output_dir+'/tf',widths=(800,375),assets=assets,label='Optional GPS vehicle and offline transfer',timeout=30);check_pages(fixture_admin,args.output_dir+'/admin',widths=(800,375),assets=assets,label='Administrative vehicle GPS table',timeout=20)
