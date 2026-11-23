# Browserprüfung für Betriebsstellen und Ortszuordnungen.
"""Real DOM and IndexedDB: explicit consent, offline queue, conflict prompts and private TF overlays."""
import check_work_report_layout as runner


def fixture():
    scripts='\n'.join((runner.STATIC/name).read_text() for name in ['messages.js','station-catalog-data.js','station-catalog.js','station-contributions.js','station-picker.js','gps.js'])
    mocks=r'''
let online=false,serverPoint=null,globalRevision=0,token='a'.repeat(64),writes=[],putAttempts=0,changeOnWrite=false;
Object.defineProperty(navigator,'onLine',{get:()=>online});
const reply=(data,status=200)=>({ok:status>=200&&status<300,status,json:async()=>data});
window.fetch=async(path,options={})=>{
 if(!online)throw Error('Offline');const url=new URL(path,location.href);
 if(url.pathname.endsWith('/coordinate-revision'))return reply({revision:globalRevision});
 if(url.pathname.endsWith('/offline-catalog'))return reply({reference_revision:window.StationCatalogSeed.revision,coordinate_revision:globalRevision,stations:window.StationCatalogSeed.stations.map(row=>row[0]==='AA'?(serverPoint?['AA','Hamburg-Altona',serverPoint.latitude,serverPoint.longitude]:['AA','Hamburg-Altona']):row)});
 if(url.pathname.endsWith('/coordinates')){
  const plan={code:'AA',name:'Hamburg-Altona',coordinate:serverPoint,token,distance_m:serverPoint?2000:null,confirmation_required:!!serverPoint};
  if(options.method!=='PUT')return reply(plan);
  putAttempts++;const body=JSON.parse(options.body);
  if(changeOnWrite){changeOnWrite=false;token='c'.repeat(64);return reply({detail:{code:'coordinate_changed'}},409);}
  if(body.expected_token!==token)return reply({detail:{code:'coordinate_changed'}},409);
  if(serverPoint&&!body.confirm_overwrite)return reply({detail:{code:'confirmation_required'}},409);
  writes.push(body);globalRevision++;serverPoint={latitude:body.latitude,longitude:body.longitude,catalog_name:'Hamburg-Altona'};token='b'.repeat(64);return reply({code:'AA',name:'Hamburg-Altona',coordinate:serverPoint,token,revision:globalRevision});
 }
 return reply({},404);
};
'''
    checks=r'''
(async()=>{
 const assert=(value,message)=>{if(!value)throw Error(message);},wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 async function until(test,message){for(let i=0;i<150;i++){if(await test())return;await wait(20);}throw Error(message);}
 await window.StationCatalog.ready;await window.StationContributions.activate(7);
 const now=Date.now(),recorder=window.GpsRecorder.mount({userId:7,journeyId:'coordinate-ui',container:document.getElementById('recording'),trainNumber:()=> '12345',readonly:()=>false,stations:(input,list,options)=>window.StationPicker.mount(input,{...options,owner:()=>7})});await recorder.readyPromise;
 recorder.record={train_number:'12345',ended:true,detection_version:5,stop_minutes:1,stop_edits:{},points:Array.from({length:26},(_,i)=>({t:now-125000+i*5000,lat:53.55,lon:9.9,accuracy:5,speed:0}))};recorder.collapseButton.click();recorder.draw();
 const raw=JSON.stringify(recorder.record.points),input=recorder.liveInputs[0].station;
 async function select(){input.focus();input.value='AA';input.dispatchEvent(new Event('input',{bubbles:true}));await until(()=>document.querySelector('.station-picker button')?.textContent==='AA · Hamburg-Altona','DS100 option');document.querySelector('.station-picker button').click();await until(()=>document.querySelector('.station-coordinate-confirm[open]'),'Initial consent dialog');}
 const choose=key=>document.querySelector('.station-coordinate-confirm[open] [data-coordinate-choice='+key+']').click();
 await select();choose('no');await wait(30);assert((await window.StationCatalog.pending(7,true)).length===0&&writes.length===0,'No stores nothing');
 await select();choose('yes');await until(async()=> (await window.StationCatalog.pending(7,true)).length===1,'Offline queue saved');
 assert((await window.StationCatalog.getStation('AA',7)).coordinate.latitude===53.55,'Own local position usable offline');assert((await window.StationCatalog.getStation('AA',8)).coordinate===null,'Pending point not leaked to other TF');assert(writes.length===0,'Offline consent never writes server');
 serverPoint={latitude:51,longitude:12,catalog_name:'Hamburg-Altona'};online=true;let sync=window.StationContributions.sync();await until(()=>document.querySelector('.station-coordinate-confirm[open]'),'Second confirmation for far server point');assert(writes.length===0,'No overwrite before second consent');choose('no');await sync;
 assert((await window.StationCatalog.pending(7,true)).length===0,'Rejected far proposal removed');assert((await window.StationCatalog.getStation('AA',7)).coordinate.latitude===51,'Server coordinate restored locally');assert(writes.length===0&&serverPoint.latitude===51,'No preserves server');
 // Reset public cache, then simulate a stale offline catalogue and a concurrent server change.
 serverPoint=null;await wait(30);await window.StationCatalog.refresh(true);online=false;await select();choose('yes');await until(async()=> (await window.StationCatalog.pending(7,true)).length===1,'Second offline proposal');
 serverPoint={latitude:50,longitude:10,catalog_name:'Hamburg-Altona'};changeOnWrite=true;online=true;sync=window.StationContributions.sync();await until(()=>document.querySelector('.station-coordinate-confirm[open]'),'Far consent');choose('yes');
 await until(()=>document.querySelector('.station-coordinate-confirm[open]'),'Fresh consent after compare-and-set conflict');assert(writes.length===0,'Concurrent change not silently overwritten');choose('yes');await sync;
 assert(writes.length===1&&writes[0].confirm_overwrite===true,'Explicit second consent permits replacement');assert((await window.StationCatalog.getStation('AA',8)).coordinate.latitude===53.55,'Accepted position available to other TF');assert((await window.StationCatalog.pending(7,true)).length===0,'Accepted queue item removed');
 assert(JSON.stringify(recorder.record.points)===raw,'Coordinate contribution never changes GPS fixes');assert(input.value==='AA · Hamburg-Altona','Stop input preserved');
 // Another signed-in TF must never upload the prior TF\'s pending location.
 serverPoint=null;await wait(30);await window.StationCatalog.refresh(true);online=false;await select();choose('yes');await until(async()=> (await window.StationCatalog.pending(7,true)).length===1,'Private proposal before account change');await window.StationContributions.activate(8);
 assert((await window.StationCatalog.getStation('AA',8)).coordinate===null,'New account has no private previous-account coordinates');await window.StationContributions.sync();assert(writes.length===1,'New account cannot upload previous queue');
 await window.StationContributions.activate(7,{sync:false});for(const item of await window.StationCatalog.pending(7))await window.StationCatalog.removeProposal(7,item.id);
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    css=(runner.STATIC/'work-report.css').read_text()+(runner.STATIC/'responsive.css').read_text()
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main id="workReport"><div id="recording"></div></main><script>'+mocks+scripts+checks+'</script></body></html>'

if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,label='Station coordinate consent')
