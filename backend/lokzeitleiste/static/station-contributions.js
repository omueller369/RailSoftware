/* Gemeinsame Verarbeitung für Betriebsstellen und Ortszuordnungen. */
/* TF-confirmed station positions: private durable offline queue, server CAS and two prompts. */
(()=>{
const S={"offer":globalThis.CtlText.source("station_contributions.text_7a5424e22744"),"far":globalThis.CtlText.source("station_contributions.text_d32c0afc6290"),"yes":globalThis.CtlText.source("station_contributions.text_baffedd06c2e"),"no":globalThis.CtlText.source("station_contributions.text_500ec634e9d7"),"queued":globalThis.CtlText.source("station_contributions.text_32bd8fa8f72a"),"saved":globalThis.CtlText.source("station_contributions.text_95b68f502613"),"discarded":globalThis.CtlText.source("station_contributions.text_3b8229600b1f"),"no_fix":globalThis.CtlText.source("station_contributions.text_a03343f6b968"),"failed":globalThis.CtlText.source("station_contributions.text_3ac85241b51a"),"retry":globalThis.CtlText.source("station_contributions.text_118cfc015f2f"),"owner":globalThis.CtlText.source("station_contributions.text_209262112731"),"unknown":globalThis.CtlText.source("station_contributions.text_e5d2a953eccc"),"invalid":globalThis.CtlText.source("station_contributions.text_508fd1c00940"),"conflict":globalThis.CtlText.source("station_contributions.text_8d88d1bfad6b"),"idempotency":globalThis.CtlText.source("station_contributions.text_d4430353d852"),"help":globalThis.CtlText.source("station_contributions.text_5c892618829a"),"history":globalThis.CtlText.source("station_contributions.text_114c9b1151de")};
const t=(key,values={})=>{let value=window.I18n?.t(S[key])||S[key];for(const [name,text]of Object.entries(values))value=value.replaceAll('{'+name+'}',String(text));return value;};
let owner=null,enabled=true,task=null,dialogState=null,questions=Promise.resolve();
const visible=()=>document.visibilityState!=='hidden';
function announce(id,key){window.dispatchEvent(new CustomEvent('stationcoordinatefeedback',{detail:{owner:id,message:t(key)}}));}
function ask(key,values,id){const next=questions.then(()=>new Promise(resolve=>{
 if(owner!==id||!visible()){resolve(null);return;}
 const dialog=document.createElement('dialog');dialog.className='station-coordinate-confirm';dialog.setAttribute('aria-label',t(key,values));
 const message=document.createElement('p');message.textContent=t(key,values);const tools=document.createElement('div');tools.className='controls';
 const focus=document.activeElement;let done=false;const finish=value=>{if(done)return;done=true;dialogState=null;dialog.close();dialog.remove();if(focus?.isConnected)focus.focus();resolve(value);};
 for(const [label,value]of [['yes',true],['no',false]]){const button=document.createElement('button');button.type='button';button.textContent=t(label);button.dataset.coordinateChoice=label;button.onclick=()=>finish(value);tools.append(button);}
 dialog.append(message,tools);const parent=document.querySelector('.train-map-fullscreen[open]')||document.body;parent.append(dialog);dialog.addEventListener('cancel',event=>{event.preventDefault();finish(false);});dialogState={finish,owner:id};dialog.showModal();
 }));questions=next.catch(()=>{});return next;}
async function api(path,options={}){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);try{const response=await fetch(path,{credentials:'same-origin',cache:'no-store',...options,signal:controller.signal});const value=await response.json().catch(()=>({}));if(!response.ok){const error=Error(typeof value.detail==='string'?value.detail:t('failed'));error.status=response.status;error.detail=value.detail;throw error;}return value;}finally{clearTimeout(timer);}}
async function accepted(item,value){await window.StationCatalog.acceptServerPoint(value);await window.StationCatalog.removeProposal(item.owner_id,item.id).catch(()=>{});announce(item.owner_id,'saved');window.StationCatalog.refresh(true).then(ok=>{if(!ok)window.StationCatalog.checkCoordinateRevision(true).catch(()=>{});}).catch(()=>{});}
async function sync(){
 const id=owner;if(!id||!enabled||!visible()||navigator.onLine===false||!window.StationCatalog)return;if(task)return task;
 task=(async()=>{for(const item of await window.StationCatalog.pending(id,true)){
  if(owner!==id||!enabled||!visible()||navigator.onLine===false)return;
  for(let attempt=0;attempt<3;attempt++){
   try{
    const path='/api/v1/tf/stations/'+encodeURIComponent(item.code)+'/coordinates';const query='?owner_id='+id+'&latitude='+encodeURIComponent(item.latitude)+'&longitude='+encodeURIComponent(item.longitude)+'&request_id='+encodeURIComponent(item.id);
    const check=await api(path+query);if(owner!==id||!visible())return;
    if(check.already_applied){await accepted(item,check);break;}
    let overwrite=false;
    if(check.confirmation_required){const result=await ask('far',{code:check.code,name:check.name,distance:Math.ceil(check.distance_m)},id);if(owner!==id||result===null)return;if(!result){await window.StationCatalog.removeProposal(id,item.id).catch(()=>{});await window.StationCatalog.acceptServerPoint(check).catch(()=>{});announce(id,'discarded');break;}overwrite=true;}
    if(owner!==id||!visible())return;if(!(await window.StationCatalog.pending(id,true)).some(current=>current.id===item.id))break;
    const result=await api(path,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:item.id,owner_id:id,latitude:item.latitude,longitude:item.longitude,accuracy_m:item.accuracy_m,observed_at:item.observed_at,confirmed:true,expected_token:check.token,confirm_overwrite:overwrite})});
    await accepted(item,result);break;
   }catch(error){
    if(error.status===409&&['coordinate_changed','confirmation_required'].includes(error.detail?.code)){if(attempt<2)continue;announce(id,'retry');return;}
    announce(id,error.status===403||error.status===401?'owner':error.status===404?'unknown':error.status===422?'invalid':error.detail?.code==='request_reused'?'idempotency':'queued');return;
   }
  }
 }})();try{return await task;}finally{task=null;}
}
async function offer({owner_id,choice,point,valid=()=>true}){
 if(!window.StationCatalog||owner!==owner_id||!enabled||!valid())return false;
 const local=await window.StationCatalog.getStation(choice.code,owner_id);if(choice.coordinates||local?.coordinate&&local.name===choice.name)return false;
 if(!point||!Number.isFinite(point.lat)||!Number.isFinite(point.lon)||point.accuracy>50||!Number.isFinite(point.accuracy)||point.lat===0&&point.lon===0){announce(owner_id,'no_fix');return false;}
 const ok=await ask('offer',{code:choice.code,name:choice.name,lat:point.lat.toFixed(6),lon:point.lon.toFixed(6)},owner_id);
 if(!ok||owner!==owner_id||!valid())return false;
 const item={id:crypto.randomUUID(),owner_id,code:choice.code,name:choice.name,latitude:point.lat,longitude:point.lon,accuracy_m:point.accuracy,observed_at:point.t,created_at:Date.now()};
 try{await window.StationCatalog.stageProposal(item);announce(owner_id,'queued');sync().catch(()=>{});return true;}catch{announce(owner_id,'failed');return false;}
}
window.StationContributions={offer,sync,text:t,async activate(value,options={}){if(owner!==value&&dialogState)dialogState.finish(null);owner=Number(value);enabled=options.sync!==false;if(window.StationCatalog)await window.StationCatalog.pending(owner,true);if(enabled)sync().catch(()=>{});},back(){if(!dialogState)return false;dialogState.finish(false);return true;}};
window.addEventListener('online',()=>sync().catch(()=>{}));window.addEventListener('focus',()=>sync().catch(()=>{}));document.addEventListener('visibilitychange',()=>{if(visible())sync().catch(()=>{});});setInterval(()=>sync().catch(()=>{}),300000);
})();
