# Echte Browserprüfung der ausdrücklichen Zielzustimmung einschließlich lokaler Speicherung.
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC

def fixture():
    tests=r'''
(async()=>{
 const assert=(value,message)=>{if(!value)throw Error(message);},wait=()=>new Promise(r=>setTimeout(r,30));
 const options={userId:7,journeyId:'11111111-1111-4111-8111-111111111111',container:document.getElementById('gps'),trainNumber:()=>'123',readonly:()=>false,stations(){},resolve:async()=>({code:'BBB',name:'Ziel'})};
 const recorder=GpsRecorder.mount(options);await recorder.readyPromise;
 recorder.record={train_number:'123',points:[{t:1794916800000,lat:52,lon:13,accuracy:5},{t:1794916860000,lat:52.01,lon:13.01,accuracy:5}],manual_stops:[],ended:true,revision:0};
 let task=recorder.confirmEndKnowledge({code:'BBB',name:'Ziel'});await wait();
 let dialog=document.querySelector('[data-location-renewal]');assert(dialog?.open,'Arrival offers a real dialog');assert(dialog.textContent.includes('Soll die Ortskenntnis verlängert werden?'),'Exact question shown');
 assert(dialog.querySelector('[data-location-renewal-yes]').textContent==='Ja'&&dialog.querySelector('[data-location-renewal-no]').textContent==='Nein','Explicit Yes and No buttons');
 dialog.querySelector('[data-location-renewal-no]').click();await task;
 let saved=await GpsRecorder.localRecord(7,options.journeyId);assert(saved.renew_end_location===false&&saved.renew_end_station==='BBB','No is durably stored offline');
 task=recorder.confirmEndKnowledge({code:'BBB',name:'Ziel'});await wait();document.querySelector('[data-location-renewal-yes]').click();await task;
 saved=await GpsRecorder.localRecord(7,options.journeyId);assert(saved.renew_end_location===true&&saved.renew_end_station==='BBB','Yes is durably bound to the destination');
 await recorder.sync();assert(lastPayload.renew_end_location===true&&lastPayload.renew_end_station==='BBB','Synchronization carries explicit Yes');
 task=recorder.confirmEndKnowledge({code:'CCC',name:'Anderer Bahnhof'});await wait();document.querySelector('[data-location-renewal]').dispatchEvent(new Event('cancel',{cancelable:true}));await task;
 saved=await GpsRecorder.localRecord(7,options.journeyId);assert(saved.renew_end_location===false&&saved.renew_end_station==='CCC','Closing the question cannot grant permission');
 await recorder.sync();assert(lastPayload.renew_end_location===false,'Synchronization preserves No');
 await recorder.confirmEndKnowledge({code:'',name:'Freitext'});assert(!document.querySelector('[data-location-renewal]'),'Free text does not grant a station renewal');
 parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    setup=r'''
Object.defineProperty(navigator,'onLine',{get:()=>false});window.I18n={t:s=>s};window.confirm=()=>true;let lastPayload=null;window.fetch=async(url,options={})=>{if(options.method==='PUT'){lastPayload=JSON.parse(options.body);return new Response(JSON.stringify({...lastPayload,revision:1,analysis:{rows:[],gaps:[]}}));}return new Response('{}',{status:404});};
'''
    return '<!doctype html><html><head><meta charset="utf-8"></head><body><div id="gps"></div><script src="/tf/messages.js"></script><script>'+setup+'</script><script src="/tf/gps.js"></script><script>'+tests+'</script></body></html>'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args();check_pages(fixture,args.output_dir,widths=(800,375),assets={'/tf/messages.js':STATIC/'messages.js','/tf/gps.js':STATIC/'gps.js'},label='GPS destination renewal confirmation',timeout=20)
