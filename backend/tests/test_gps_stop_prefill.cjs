const assert=require('node:assert/strict');
const {context,Element,tracks}=require('./test_gps_live_v26.cjs');
const wait=()=>new Promise(setImmediate),pending=[];
context.fetch=async(path)=>{if(path.startsWith('/api/v1/tf/gps/stop-station?'))return new Promise((resolve,reject)=>pending.push({path,resolve:data=>resolve({ok:true,status:200,json:async()=>data}),reject}));return {ok:false,status:404,json:async()=>({})};};
const base=1792627200000,record=()=>({train_number:'123',ended:false,detection_version:5,stop_minutes:1,stop_edits:{},points:Array.from({length:26},(_,i)=>({t:base+i*5000,lat:52,lon:13,accuracy:5,speed:0}))});
(async()=>{
 const r=context.window.GpsRecorder.mount({userId:7,journeyId:'prefill-test',container:new Element('div'),trainNumber:()=> '123',readonly:()=>false,stations(){}});await r.readyPromise;
 r.record=record();r.draw();await wait();assert.equal(pending.length,1,'Detected stop starts direct lookup');r.draw();await wait();assert.equal(pending.length,1,'Pending request deduplicated');
 let input=r.liveInputs[0];input.station.value='km 42,7';input.station.oninput();pending[0].resolve({station:{code:'BBB',name:'Berlin Beispiel'}});await wait();assert.equal(input.station.value,'km 42,7','Late response preserves manual typing');assert.equal(r.record.stop_edits[input.row.key].station,null);
 r.record=record();r.draw();await wait();assert.equal(pending.length,2);pending[1].resolve({station:{code:'BBB',name:'Berlin Beispiel',distance_m:68}});await wait();input=r.liveInputs[0];
 assert.equal(input.station.value,'BBB · Berlin Beispiel');assert.equal(input.readEdit().station.code,'BBB','Transfer uses same selected station');assert.equal(tracks.get(r.key).value.stop_edits[input.row.key].station.code,'BBB','Suggestion saved locally');
 r.draw();await wait();assert.equal(pending.length,2,'Prefilled station not queried again');
 r.record=record();r.draw();await wait();pending[2].resolve({station:null,ambiguous:true});await wait();assert.equal(r.liveInputs[0].station.value,'');r.draw();await wait();assert.equal(pending.length,3,'No repeated ambiguous lookup');
 context.navigator.onLine=false;r.record=record();r.draw();await wait();assert.equal(pending.length,3,'Offline recording continues without lookup');context.navigator.onLine=true;r.draw();await wait();assert.equal(pending.length,4,'Reconnect retries unresolved stop');
 const previous=r.record;r.record=null;pending[3].resolve({station:{code:'BBB',name:'Berlin Beispiel'}});await wait();assert.equal(r.record,null,'Deleted or replaced recording cannot be restored by response');assert(!previous.stop_edits['live-'+base]);
 r.o.demo=true;r.o.now=()=>base+125000;r.record=record();r.draw();await wait();assert.equal(pending.length,4,'Demo remains read-only');r.o.demo=false;r.o.readonly=()=>true;r.record=record();r.draw();await wait();assert.equal(pending.length,4,'Read-only recordings unchanged');
 console.log('DS100 stop prefill: detection, deduplication, persistent editable suggestion, manual/race safety, ambiguity, offline recovery and demo isolation passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
