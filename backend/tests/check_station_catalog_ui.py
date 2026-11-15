"""Real browser: offline cold start, DS100 search, favorites and GPS-stop prefill."""
import check_work_report_layout as runner


def fixture():
    scripts='\n'.join((runner.STATIC/name).read_text() for name in ['messages.js','station-catalog-data.js','station-catalog.js','station-picker.js','gps.js'])
    mocks="let online=false,requests=0;window.fixtureErrors=[];window.addEventListener('error',e=>window.fixtureErrors.push(e.message));Object.defineProperty(navigator,'onLine',{get:()=>online});window.fetch=async()=>{requests++;throw Error('Offline fixture cannot use network');};"
    checks=r'''
(async()=>{
 const assert=(value,message)=>{if(!value)throw Error(message);},wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 await window.StationCatalog.ready;await wait(30);
 assert(window.StationCatalog.count===14886&&window.StationCatalog.coordinateCount===6450,'Full DS100 data available on first offline load');
 assert(requests===0,'Cold start has no server dependency');
 online=true;await window.StationCatalog.frequent(async()=>Array.from({length:7},(_,i)=>({code:'F'+i,name:'Häufig '+i})),7);online=false;
 const input=document.getElementById('lookup');window.StationPicker.mount(input,{owner:()=>7});input.focus();for(let i=0;i<100&&document.querySelectorAll('.station-picker button').length!==5;i++)await wait(20);
 assert(document.querySelectorAll('.station-picker button').length===5,'Five cached frequent places available offline; active='+document.activeElement?.id+' errors='+JSON.stringify(window.fixtureErrors)+' list='+document.querySelector('.station-picker')?.textContent);
 input.value='AABG';input.dispatchEvent(new Event('input'));for(let i=0;i<100&&!document.querySelector('.station-picker button')?.textContent.startsWith('AABG');i++)await wait(20);
 const option=document.querySelector('.station-picker button');assert(option?.textContent==='AABG · Agathenburg','DS100 suggestions work with network disabled');option.click();assert(input.value==='AABG · Agathenburg','Offline suggestion can be selected');input.blur();
 const point=window.StationCatalogSeed.stations.find(row=>row[0]==='AABG'),now=Date.now();
 const recorder=window.GpsRecorder.mount({userId:7,journeyId:'offline-catalog',container:document.getElementById('recording'),trainNumber:()=> '12345',readonly:()=>false,stations:(field)=>window.StationPicker.mount(field,{owner:()=>7})});await recorder.readyPromise;
 recorder.record={train_number:'12345',ended:false,detection_version:5,stop_minutes:1,stop_edits:{},points:Array.from({length:26},(_,i)=>({t:now-125000+i*5000,lat:point[2],lon:point[3],accuracy:5,speed:0}))};recorder.collapseButton.click();recorder.draw();
 for(let i=0;i<50&&!recorder.liveInputs[0]?.station.value;i++)await wait(20);
 assert(recorder.liveInputs[0]?.station.value==='AABG · Agathenburg','Detected stop prefills from local coordinates while offline');
 assert(recorder.liveInputs[0].readEdit().station.code==='AABG','Local suggestion remains usable for transfer');
 assert(requests===0,'Search, favorites and prefill require no network requests');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    css=(runner.STATIC/'work-report.css').read_text()+(runner.STATIC/'responsive.css').read_text()
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main><input id="lookup"><div id="recording"></div></main><script>'+mocks+scripts+checks+'</script></body></html>'


if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,label="Offline DS100")
