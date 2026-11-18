"""Offline localStorage and IndexedDB conversion, account isolation and one Art choice."""
import argparse
from browser_realtime import check_pages
from check_field_error_navigation_ui import shell
from check_work_report_layout import STATIC

def fixture():
    scripts='\n'.join((STATIC/name).read_text() for name in ['messages.js','infra-go.js','train-journeys.js','gps.js'])
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};localStorage.clear();window.fetch=async()=>({ok:false,status:404,json:async()=>({})});
 const choices=[{id:1,category:'cause',value:'DB InfraGo',label:'DB InfraGo',active:true},{id:2,category:'cause',value:'DB-InfraGo',label:'DB-InfraGo',active:true},{id:3,category:'cause',value:'custom-old',label:'DB InfraoGo',active:true},{id:4,category:'cause',value:'CTL',label:'CTL',active:true}];localStorage.setItem('lokzeitleiste.app-defaults',JSON.stringify(choices));
 const payload={revision:9,_cloud_revision:4,_cloud_dirty:false,train_journeys:[{events:[{cause:'DB InfraoGo',cause_label:'DB InfraGo',cause_detail:'DB InfraGo im persönlichen Hinweis'}]}],train_editors:[{eventFields:{cause:'custom-old'}}]};
 for(const id of [7,8]){localStorage.setItem('lokzeitleiste.work-report.'+id,JSON.stringify(payload));localStorage.setItem('lokzeitleiste.work-report.'+id+'.error-editor.saved',JSON.stringify({state:payload}));}
 const base=1792627200000,points=Array.from({length:26},(_,i)=>({t:base+i*5000,lat:52,lon:13,accuracy:5,speed:0})),track={train_number:'123',revision:7,dirty:false,detection_version:5,ended:true,points,stop_edits:{['live-'+base]:{cause:'custom-old',reason:'V3'}},manual_stops:[]};
 const database=await new Promise((resolve,reject)=>{const request=indexedDB.open('lokzeitleiste.gps',1);request.onupgradeneeded=()=>request.result.createObjectStore('tracks',{keyPath:'key'});request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
 const write=database.transaction('tracks','readwrite');for(const id of [7,8])write.objectStore('tracks').put({key:id+'.old',value:structuredClone(track)});await new Promise((resolve,reject)=>{write.oncomplete=resolve;write.onerror=()=>reject(write.error);});
 await InfraGo.activate(7);const read=database.transaction('tracks'),request=read.objectStore('tracks').getAll();await new Promise(resolve=>read.oncomplete=resolve);const own=request.result.find(row=>row.key==='7.old').value,other=request.result.find(row=>row.key==='8.old').value;
 assert(own.stop_edits['live-'+base].cause==='DB-InfraGo','Old offline GPS Art updated');assert(other.stop_edits['live-'+base].cause==='custom-old','Other account GPS untouched');assert(own.revision===7&&!own.dirty&&JSON.stringify(own.points)===JSON.stringify(points),'GPS points, revisions and dirty state preserved');
 const local=JSON.parse(localStorage.getItem('lokzeitleiste.work-report.7'));assert(local.train_journeys[0].events[0].cause==='DB-InfraGo'&&local.train_editors[0].eventFields.cause==='DB-InfraGo','Reports and unfinished row values normalized');assert(local.train_journeys[0].events[0].cause_detail==='DB InfraGo im persönlichen Hinweis','Personal free text untouched');assert(local.revision===9&&local._cloud_revision===4&&!local._cloud_dirty,'Cloud revision and dirty state preserved');assert(JSON.parse(localStorage.getItem('lokzeitleiste.work-report.8')).train_journeys[0].events[0].cause==='DB InfraoGo','Other account local reports untouched');
 assert(JSON.parse(localStorage.getItem('lokzeitleiste.work-report.7.error-editor.saved')).state.train_editors[0].eventFields.cause==='DB-InfraGo','Navigation recovery also normalized');
 const catalogue=JSON.parse(localStorage.getItem('lokzeitleiste.app-defaults'));assert(catalogue.filter(row=>row.category==='cause'&&InfraGo.named(row.value)).length===1,'Cached choice list deduplicated');refreshTrainJourneyChoices(catalogue);
 const root=document.createElement('section'),button=document.createElement('button');document.body.append(root,button);const editor=new TrainJourneyEditor({userId:7,container:root,button,readonly:()=>false,bounds:()=>({start:'2026-10-22T08:00',end:'2026-10-22T16:00'}),minute:value=>Date.parse(value)/60000,clock:String,uuid:()=>crypto.randomUUID(),stations(){},changed(){},editingChanged(){},message(){}});
 const original={id:'old',train_number:'123',start_at:'2026-10-22T09:00',end_at:'2026-10-22T11:00',start_station:'AAA',end_station:'BBB',events:[{id:'event',reason:'V3',cause:'DB InfraGo',station:'BBB',start_at:'2026-10-22T10:00',end_at:'2026-10-22T10:10'}]};editor.restore([original]);const item=editor.items[0];assert(editor.draft()[0].events[0].cause==='DB-InfraGo','Old event reopens with canonical value');assert([...item.eventFields.cause.options].filter(option=>InfraGo.named(option.value)).length===1,'Art select has exactly one infrastructure choice');
 await InfraGo.activate(7);assert(JSON.parse(localStorage.getItem('lokzeitleiste.work-report.7'))._cloud_revision===4,'Repeated conversion remains idempotent');database.close();parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return shell().replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,widths=(800,320),label='Offline DB-InfraGo normalization')
