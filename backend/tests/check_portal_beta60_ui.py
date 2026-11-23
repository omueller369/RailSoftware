# Browserprüfung für gemeinsame Portaloberfläche.
"""Real DOM: pause/fullscreen, readable share icon, route geometry and traffic badge."""
import json
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html


def fixture():
    base=runner.STATIC
    brake=localize_html((base/'brake-sheet.html').read_text())
    brake=re.sub(r'<script\b[^>]*>.*?</script>','',brake,flags=re.S)
    brake=re.sub(r'<link\b[^>]*>','',brake)
    brake_mock=r'''
window.I18n={t:s=>s,locale:'de-DE'};
window.fetch=async(path,options={})=>{let data={};if(path.endsWith('/account/me'))data={id:7,role:'tf'};else if(path.endsWith('/vehicles'))data=[];else if(path.endsWith('/import-wagons')){window.importedFile=options.body.get('file').name;data={station_from:'A',station_to:'B',first_vehicle:'123456789012',last_vehicle:'123456789013',brake_mode:'G',wagon:{count:2,length:30,weight:100,brake:80},wagon_import:{sheet:'Wagenliste',first_row:2,last_row:3,total_row:4,rows:[{length:15},{length:15}]}};}else if(path.endsWith('/preview'))data={lines:[],wagon:{},totals:{},preview_missing:[],holding:{}};return {ok:true,status:200,json:async()=>data};};
'''
    brake+='\n<script>'+(base/'messages.js').read_text()+brake_mock+(base/'android-portal.js').read_text()+(base/'brake-sheet.js').read_text()+'</script>'
    mock=r'''
window.I18n={t:s=>s,locale:'de-DE'};let nativePaused=false,externalCalls=0;
window.AndroidPortal={version:Promise.resolve('0.26.60-test'),request:async method=>{if(method==='external.db')externalCalls++;if(method==='traffic.status')return {upload:2048,download:4096};return {};},gps:async(method,data)=>{if(method==='pause')nativePaused=data.paused;return {running:true,paused:nativePaused,points:[]};},saveBlob:async()=>{},printHelp:async()=>{}};
const apiCalls=[];window.fetch=async(path,options={})=>{apiCalls.push(path);let data={};if(path.includes('gps-settings'))data={owner_id:7,stop_minutes:2,marker:'electric',share_enabled:true};else if(path.includes('gps-shared'))data={positions:[]};else if(path.includes('route-knowledge'))data={owner_id:7,items:[{journey_id:'server',segments:[[[50,9],[50.1,9.1]]]}],next_offset:null};else if(path.includes('/gps/'))return new Response('{}',{status:404});return new Response(JSON.stringify(data));};
window.RouteKnowledgeTileUrl=window.GpsTileUrl='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1ioAAAAASUVORK5CYII=';
'''
    checks=r'''
(async()=>{
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);},until=async(fn,msg)=>{for(let i=0;i<200;i++){if(await fn())return;await new Promise(r=>setTimeout(r,10));}throw Error(msg);};
 const recorder=window.GpsRecorder.mount({userId:7,journeyId:'00000000-0000-4000-8000-000000000001',container:document.getElementById('recording'),trainNumber:()=> '123',readonly:()=>false,stations(){}});
 recorder.record={train_number:'123',points:[{t:Date.now(),lat:52,lon:13,accuracy:5,speed:0}],manual_stops:[],ended:false};await recorder.readyPromise;await recorder.nativeRead();recorder.setExpanded(true);
 await window.GpsPreferences.load(7);recorder.freeze();const share=recorder.box.querySelector('.gps-share-icon svg');assert(share,'Share SVG exists');const size=share.getBoundingClientRect();assert(size.width>=22&&size.width<=26&&size.height>=22&&size.height<=26,'Share icon is 24px, not a map-sized square');
 window.TrainWorkspace.fullscreen(recorder);assert(document.querySelector('.train-map-fullscreen[open] .gps-pause'),'Pause visible in fullscreen');assert(recorder.digiButton.closest('dialog[open]'),'DB command visible in fullscreen');
 await recorder.togglePause();assert(nativePaused&&recorder.record.paused,'Native GPS paused without ending');assert(window.GpsRecorder.isActive()&&!recorder.record.ended,'Pause keeps recording identity');await recorder.togglePause();assert(!nativePaused,'Resume same record');
 window.confirm=()=>false;await recorder.openDigi();assert(!document.querySelector('.train-map-fullscreen[open]'),'DB command exits fullscreen');assert(externalCalls===1,'Native DB command invoked');
 // A same-origin embedded brake form must share the parent adapter and use a real file input.
 const frame=document.createElement('iframe');frame.src=URL.createObjectURL(new Blob([__BRAKE__],{type:'text/html'}));document.body.append(frame);await until(()=>frame.contentWindow?.AndroidPortal&&frame.contentDocument?.getElementById('brakeImport')&&!frame.contentDocument.getElementById('brakeImport').disabled,'Brake overlay ready');
 assert(frame.contentWindow.AndroidPortal.saveBlob===window.AndroidPortal.saveBlob,'Overlay reuses main adapter');const input=frame.contentDocument.getElementById('brakeImportFile'),transfer=new DataTransfer();transfer.items.add(new File(['fixture'],'Wagenliste.xlsx',{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));await until(()=>frame.contentDocument.getElementById('brakeImportDialog').open,'Excel preview opens inside iframe');assert(frame.contentWindow.importedFile==='Wagenliste.xlsx','Excel multipart upload uses selected file');frame.contentDocument.getElementById('brakeImportCancel').click();assert(!frame.contentDocument.getElementById('brakeImportDialog').open,'Preview cancellation');assert(window.GpsRecorder.isActive(),'Excel import preserves native GPS');
 window.GpsRecorder.localRecords=async()=>[{journey_id:'local',dirty:true,points:[{t:1000,lat:52,lon:13,accuracy:5},{t:6000,lat:52.1,lon:13.1,accuracy:5},{t:10000,lat:52.2,lon:13.2,accuracy:5,break_before:true},{t:15000,lat:52.3,lon:13.3,accuracy:5}]}];
 window.GpsRecorder.localSummaries=async(owner,project)=>(await window.GpsRecorder.localRecords(owner)).map(project);
 // This small fixture exercises the raw web fallback without the M1 worker bundle.
 // Android's actual M1/worker rendering is covered by check_android_map_recovery_ui.
 const adapter=window.AndroidPortal;delete window.AndroidPortal;await window.startRouteKnowledge({id:7});window.AndroidPortal=adapter;const paths=[...document.querySelectorAll('[data-route-track]')];assert(paths.length===2,'Local and server tracks combined');assert((paths[0].getAttribute('d').match(/M/g)||[]).length===2,'Paused part not rendered as travelled');
 const du=document.querySelector('.beta-upload'),dl=document.querySelector('.beta-download');await until(()=>document.querySelector('.beta-upload')?.textContent==='DU: 2.0 KB','Native upload counter');assert(getComputedStyle(document.querySelector('.beta-upload')).color==='rgb(7, 95, 190)','Upload blue');assert(getComputedStyle(document.querySelector('.beta-download')).color==='rgb(197, 23, 35)','Download red');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''.replace('__BRAKE__',json.dumps(brake).replace('</script>',r'<\/script>'))
    scripts=(base/'messages.js').read_text()+mock+'\n'+ '\n'.join((base/name).read_text() for name in ['gps.js','gps-settings.js','train-workspace.js','route-knowledge.js','beta-traffic.js'])
    css='\n'.join((base/name).read_text() for name in ['tf-portal.css','work-report.css','portal-theme.css','responsive.css'])
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main id="workReport"><div id="recording"></div><div id="routeKnowledgeWorkspace"></div></main><script>'+scripts+checks+'</script></body></html>'

if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    assets={'/tf/gps-marker-'+name+'.png':runner.STATIC/('gps-marker-'+name+'.png') for name in ['electric','steam','diesel','tank']}
    check_pages(fixture,args.output_dir,assets=assets,label='TF beta 0.26.60')
