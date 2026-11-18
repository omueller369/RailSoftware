/* Isolated playback: no location service, report writes or recording mutations. */
(()=>{
class PlaybackClock {
 constructor(duration,now=()=>performance.now()){this.duration=Math.max(0,duration);this.now=now;this.position=0;this.rate=1;this.playing=false;this.last=now();}
 update(){const now=this.now();if(this.playing){this.position=Math.min(this.duration,this.position+Math.max(0,now-this.last)*this.rate);if(this.position>=this.duration)this.playing=false;}this.last=now;return this.position;}
 play(){if(this.position>=this.duration)this.position=0;this.last=this.now();this.playing=this.duration>0;}
 pause(){this.update();this.playing=false;}
 seek(value){this.position=Math.max(0,Math.min(this.duration,Number(value)||0));this.last=this.now();if(this.position>=this.duration)this.playing=false;}
 speed(value){this.update();if([1,5,10,30,60,120,300].includes(Number(value)))this.rate=Number(value);}
}
function frame(record,position,preferences=null){
 const at=record.points[0].t+position;let lo=0,hi=record.points.length;
 while(lo<hi){const mid=(lo+hi)>>1;if(record.points[mid].t<=at)lo=mid+1;else hi=mid;}
 const result={...record,ended:false,points:record.points.slice(0,Math.max(1,lo)).map(p=>({...p})),manual_stops:(record.manual_stops||[]).filter(row=>row.start<at).map(row=>({...row,end:Math.min(row.end??at,at)})),stop_edits:{}};
 if(preferences&&[1,2,4,5,10,15].includes(preferences.stop_minutes))result.stop_minutes=preferences.stop_minutes;
 for(const [key,edit] of Object.entries(record.stop_edits||{}))result.stop_edits[key]={...edit,end:edit.end==null?edit.end:Math.min(edit.end,at)};
 return result;
}
window.GpsDemoClock=PlaybackClock;window.GpsDemoFrame=frame;
window.startGpsDemo=async (user,{administration=false}={})=>{
 const S={"title":globalThis.CtlText.source("portal_gps_demo.text_d2a6f5151788"),"intro":globalThis.CtlText.source("portal_gps_demo.text_a6049edf9076"),"choose":globalThis.CtlText.source("portal_gps_demo.text_f16c8f77fea5"),"load":globalThis.CtlText.source("portal_gps_demo.text_733ad2485ad5"),"more":globalThis.CtlText.source("portal_gps_demo.text_aad9dcac6b10"),"play":globalThis.CtlText.source("portal_gps_demo.text_04247a96a379"),"pause":globalThis.CtlText.source("portal_gps_demo.text_0dbc3031125b"),"reset":globalThis.CtlText.source("portal_gps_demo.text_eed905d69f7c"),"speed":globalThis.CtlText.source("portal_gps_demo.text_71fd00b93880"),"seek":globalThis.CtlText.source("portal_gps_demo.text_a07eb1f899c9"),"empty":globalThis.CtlText.source("portal_gps_demo.text_925dd49e6aeb"),"loading":globalThis.CtlText.source("portal_gps_demo.text_ae695c6d4099"),"ready":globalThis.CtlText.source("portal_gps_demo.text_0a01bd943ac8"),"running":globalThis.CtlText.source("portal_gps_demo.text_0fd0b42c9bbb"),"paused":globalThis.CtlText.source("portal_gps_demo.text_41d0cba18e6e"),"finished":globalThis.CtlText.source("portal_gps_demo.text_ea3d8f969fb3"),"error":globalThis.CtlText.source("portal_gps_demo.text_cb1011064bf5"),"blocked":globalThis.CtlText.source("portal_gps_demo.text_75343232c7e8"),"short":globalThis.CtlText.source("portal_gps_demo.text_a4c937f3e189"),"hint":globalThis.CtlText.source("portal_gps_demo.text_90ab31825729"),"help_title":globalThis.CtlText.source("portal_gps_demo.text_03151dda472f"),"help_short":globalThis.CtlText.source("portal_gps_demo.text_d409cda4d38e"),"help_steps":globalThis.CtlText.source("portal_gps_demo.text_fc8f9d005ba2"),"help_notes":globalThis.CtlText.source("portal_gps_demo.text_8e157c16c15f")},t=key=>window.I18n?.t(S[key])||S[key],workspace=document.getElementById('gpsDemoWorkspace'),labels=[];
 const extra={"shared": "portal_gps_demo.text_b2f44a46c65a", "own": "portal_gps_demo.text_d913c24d2ddc", "consent": "portal_gps_demo.text_7e7c9e351fc5", "share": "portal_gps_demo.text_4f7bc261e46c", "empty_shared": "portal_gps_demo.text_12dc7be1c855", "hide": "portal_gps_demo.text_693f21a2a504", "show": "portal_gps_demo.text_42f75bb1fdbb", "visibility": "portal_gps_demo.text_d2b780035db6", "saved": "portal_gps_demo.text_ca32f61efaa6", "stops": "portal_gps_demo.text_ad810cb32bac", "place": "portal_gps_demo.text_3c2213b2730a", "from": "portal_gps_demo.text_5f73cf19a42c", "until": "portal_gps_demo.text_fe3a916cf501", "duration": "portal_gps_demo.text_ee854a37ae05", "cause": "portal_gps_demo.text_e9dd07af8b9b", "reason": "portal_gps_demo.text_c11618039163", "ds100": "portal_gps_demo.text_8980d205b70f", "ds100_error": "portal_gps_demo.text_3968f2d0f351", "revoked": "portal_gps_demo.text_a811f793d424", "refresh": "portal_gps_demo.text_d3be483bccb7", "history": "portal_gps_demo.text_7a3e2c82488c", "help": "portal_gps_demo.text_fdeb3c706255", "publish": "portal_gps_demo.text_6a5482fbbecb", "pending_selection": "portal_gps_demo.text_50a7abe26d0e", "published": "portal_gps_demo.text_b66e8d1a8006", "publish_failed": "portal_gps_demo.text_3e7d17c329af", "server_update": "portal_gps_demo.text_f36ddd522a48"},base=administration?'/api/v1/admin/gps-demo':'/api/v1/tf/gps-demo';
 Object.assign(S,Object.fromEntries(Object.entries(extra).map(([key,value])=>[key,globalThis.CtlText.source(value)])));
 const node=(tag,key)=>{const element=document.createElement(tag);if(key){element.textContent=t(key);labels.push([element,key]);}return element;};
 const status=node('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 workspace.replaceChildren(status);if(window.GpsRecorder.isActive()){status.textContent=t('blocked');return;}
 if(!administration)await window.GpsPreferences?.load(user.id).catch(()=>{});
 const field=(caption,input)=>{const label=node('label'),text=node('span',caption);label.append(text,input);return label;};
 const selection=node('select'),load=node('button','load'),more=node('button','more'),play=node('button','play'),reset=node('button','reset'),speed=node('select'),seek=node('input'),time=node('output');
 selection.setAttribute('aria-label',t('choose'));seek.type='range';seek.min='0';seek.max='1';seek.step='1';seek.value='0';seek.setAttribute('aria-label',t('seek'));
 for(const rate of [1,5,10,30,60,120,300]){const option=node('option');option.value=String(rate);option.textContent=rate+'×';speed.append(option);}
 speed.value='1';for(const button of [load,more,play,reset])button.type='button';
 const loader=node('div');loader.className='gps-demo-controls';loader.append(field('choose',selection),load,more);
 const controls=node('div');controls.className='gps-demo-controls';controls.append(play,reset,field('speed',speed));
 const progress=field('seek',seek),map=node('div'),hint=node('p','hint');
 const dsHint=node('p','ds100'),stops=node('div'),shareList=node('div'),shareHeading=node('h2','own'),consent=node('p','consent'),refresh=node('button','refresh'),sharedMore=node('button','more'),hide=node('button','hide'),publish=node('button','publish'),shareStatus=node('p');publish.type='button';publish.disabled=true;publish.setAttribute('data-gps-demo-publish','');shareStatus.setAttribute('role','status');
 stops.className='excel-scroll gps-demo-stops';stops.setAttribute('aria-label',t('stops'));shareList.className='gps-demo-share-list';for(const button of [refresh,sharedMore,hide])button.type='button';
 workspace.append(loader,refresh,sharedMore,controls,progress,time,hint,dsHint,map,stops);if(!administration)workspace.append(shareHeading,consent,shareList,publish,shareStatus,hide);
 hide.onclick=async()=>{hide.disabled=true;try{await window.GpsDemoVisibility.set(user.id,true);location.href='/tf';}catch(error){status.textContent=t('error');hide.disabled=false;}};for(const control of [play,reset,speed,seek])control.disabled=true;
 const shareChanges=new Map();let publishing=false;
 let items=[],offset=0,sharedItems=[],sharedOffset=0,selectedShared=null,record=null,clock=null,recorder=null,timer=null,busy=false,generation=0,lastStopSignature='',accessTimer=null;
 const duration=ms=>[Math.floor(ms/3600000),Math.floor(ms/60000)%60,Math.floor(ms/1000)%60].map(n=>String(n).padStart(2,'0')).join(':');
 const date=ms=>new Intl.DateTimeFormat(window.I18n?.locale||'de-DE',{timeZone:'Europe/Berlin',dateStyle:'short',timeStyle:'short'}).format(new Date(ms));
 const stopTime=ms=>new Intl.DateTimeFormat(window.I18n?.locale||'de-DE',{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit'}).format(new Date(ms));
 const fillSelection=()=>{const value=selection.value;selection.replaceChildren();for(const item of items){const option=node('option');option.value=item.journey_id;option.textContent=item.train_number+' · '+date(item.start)+' · '+duration(item.end-item.start);option.setAttribute('data-i18n-ignore','');selection.append(option);}for(const item of sharedItems){const option=node('option');option.value='shared:'+item.id;option.textContent=t('shared')+' · '+item.train_number+' · '+date(item.start)+' · '+duration(item.end-item.start);option.setAttribute('data-i18n-ignore','');selection.append(option);}if([...items.map(item=>item.journey_id),...sharedItems.map(item=>'shared:'+item.id)].includes(value))selection.value=value;};
 const get=async url=>{const response=await fetch(url,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error(t('error'));return response.json();};
 const drawStops=()=>{
  const rows=recorder.rows().filter(row=>!recorder.removed(row)),entries=rows.map(row=>{
   const edit=recorder.stopDraft(row),station=edit.station;
   const end=Math.min(edit.end??row.end??row.observed_end??row.start,record.points[0].t+clock.position);
   return [edit.station_input||[station?.code,station?.name].filter(Boolean).join(' · ')||'—',stopTime(row.start),stopTime(end),duration(Math.max(0,end-row.start)),window.I18n?.t(edit.cause||'')||edit.cause||'—',window.I18n?.t(edit.reason||'')||edit.reason||'—'];
  });
  const signature=JSON.stringify([window.I18n?.locale,entries]);if(signature===lastStopSignature)return;lastStopSignature=signature;
  const heading=node('h2'),table=node('table'),head=node('tr'),body=node('tbody');heading.textContent=t('stops');table.className='excel gps-stop-table';
  for(const key of ['place','from','until','duration','cause','reason']){const cell=node('th');cell.textContent=t(key);head.append(cell);}const thead=node('thead');thead.append(head);table.append(thead,body);
  for(const values of entries){const row=node('tr');for(const value of values){const cell=node('td');cell.textContent=value;cell.setAttribute('data-i18n-ignore','');row.append(cell);}body.append(row);}stops.replaceChildren(heading,table);
 };
 const enrichStops=async(request)=>{
  recorder.record={...record,stop_minutes:window.GpsPreferences?.settings?.stop_minutes??record.stop_minutes};
  const rows=recorder.rows().filter(row=>!recorder.removed(row)),locations=[];
  for(const row of rows){
   // Manual stops without a reliable position must not acquire guessed coordinates.
   const point=row.manual?record.points.find(p=>Math.abs(p.t-row.start)<=30000&&p.accuracy<=50):row;
   if(point&&Number.isFinite(point.lat)&&Number.isFinite(point.lon))locations.push({row,lat:point.lat,lon:point.lon});
  }
  for(let offset=0;offset<locations.length;offset+=100){
   const chunk=locations.slice(offset,offset+100),response=await fetch(base+'/stations',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({points:chunk.map(({lat,lon})=>({lat,lon}))})});
   if(!response.ok)throw Error();const data=await response.json();if(request!==generation)return;
   chunk.forEach(({row},i)=>{const station=data.items[i]?.station;if(!station)return;record.stop_edits||={};const previous=recorder.stopDraft(row);record.stop_edits[row.key]={...previous,station,station_input:station.code+' · '+station.name};});
  }
 };
 const clearShared=()=>{generation++;stopTimer();clock?.pause();clock=null;record=null;selectedShared=null;clearInterval(accessTimer);map.replaceChildren();recorder=null;stops.replaceChildren();for(const control of [play,reset,speed,seek])control.disabled=true;status.textContent=t('revoked');};
 const verifyAccess=async()=>{if(selectedShared==null)return true;const selected=selectedShared,request=generation;try{await get(base+'/shared/'+selected+'/access');return request===generation;}catch(error){if(request===generation)clearShared();return false;}};
 const listingShared=async(reset=false)=>{if(reset){sharedOffset=0;sharedItems=[];}if(sharedOffset==null)return;sharedMore.disabled=true;try{const data=await get(base+'/shared?offset='+sharedOffset);sharedItems.push(...data.items);sharedOffset=data.next_offset;fillSelection();if(!administration)fillShares();if(administration&&!sharedItems.length)status.textContent=t('empty_shared');load.disabled=!items.length&&!sharedItems.length;}catch(error){status.textContent=t('error');}finally{sharedMore.disabled=false;sharedMore.hidden=sharedOffset==null;}};
 const ownItems=()=>[...items,...sharedItems.filter(item=>item.journey_id&&!items.some(own=>own.journey_id===item.journey_id))];
 const fillShares=()=>{shareList.replaceChildren();for(const item of ownItems()){const label=node('label'),check=node('input'),caption=node('span');check.type='checkbox';check.checked=shareChanges.has(item.journey_id)?shareChanges.get(item.journey_id):!!item.shared;check.disabled=publishing;check.setAttribute('aria-label',t('share'));caption.textContent=item.train_number+' · '+date(item.start);caption.setAttribute('data-i18n-ignore','');label.append(check,caption);shareList.append(label);check.onchange=()=>{if(check.checked===!!item.shared)shareChanges.delete(item.journey_id);else shareChanges.set(item.journey_id,check.checked);publish.disabled=publishing||!shareChanges.size;shareStatus.textContent=shareChanges.size?t('pending_selection'):'';};}publish.disabled=publishing||!shareChanges.size;};
 publish.onclick=async()=>{if(publishing||!shareChanges.size)return;publishing=true;fillShares();refresh.disabled=true;const planned=[...shareChanges].map(([journey_id,shared])=>({journey_id,shared,expected_revision:ownItems().find(item=>item.journey_id===journey_id)?.revision}));try{
  if(planned.some(change=>!Number.isInteger(change.expected_revision))){shareStatus.textContent=t('server_update');return;}
  const response=await fetch('/api/v1/tf/gps-demo/shares',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({changes:planned})});
  if(!response.ok){shareStatus.textContent=t(response.status===404?'server_update':'publish_failed');return;}
  for(const change of planned){for(const item of ownItems())if(item.journey_id===change.journey_id)item.shared=change.shared;if(shareChanges.get(change.journey_id)===change.shared)shareChanges.delete(change.journey_id);}
  shareStatus.textContent=t('published');await listingShared(true);if(selectedShared!=null)await verifyAccess();
 }catch(error){shareStatus.textContent=t('publish_failed');}finally{publishing=false;refresh.disabled=false;fillShares();}};

 refresh.onclick=async()=>{await listingShared(true);if(selectedShared!=null)await verifyAccess();};sharedMore.onclick=()=>listingShared();
 const render=()=>{if(!clock||!record)return;clock.update();recorder.record=frame(record,clock.position,window.GpsPreferences?.settings);recorder.drawMap();drawStops();seek.value=String(clock.position);seek.setAttribute('aria-valuetext',duration(clock.position)+' / '+duration(clock.duration));time.textContent=duration(clock.position)+' / '+duration(clock.duration)+' · '+date(record.points[0].t+clock.position);play.textContent=t(clock.playing?'pause':'play');const message=t(clock.playing?'running':clock.position>=clock.duration?'finished':'paused');if(status.textContent!==message)status.textContent=message;};
 const stopTimer=()=>{clearInterval(timer);timer=null;};
 const run=()=>{stopTimer();timer=setInterval(()=>{render();if(!clock.playing)stopTimer();},250);};
 const listing=async()=>{if(busy||offset==null)return;busy=true;more.disabled=load.disabled=true;status.textContent=t('loading');try{const data=await get('/api/v1/tf/gps-recordings?offset='+offset);items.push(...data.items);offset=data.next_offset;fillSelection();fillShares();status.textContent=items.length?'':t('empty');}catch(error){status.textContent=t('error');}finally{busy=false;more.disabled=false;load.disabled=!items.length&&!sharedItems.length;more.hidden=offset==null;}};
 more.onclick=listing;
 load.onclick=async()=>{if(busy||!selection.value)return;busy=true;const request=++generation;clearInterval(accessTimer);selectedShared=null;lastStopSignature='';stops.replaceChildren();stopTimer();clock?.pause();record=null;clock=null;map.hidden=true;for(const control of [load,more,play,reset,speed,seek,selection])control.disabled=true;status.textContent=t('loading');try{
  if(!administration)await window.GpsPreferences?.load(user.id).catch(()=>{});
  selectedShared=selection.value.startsWith('shared:')?Number(selection.value.slice(7)):null;
  const data=await get(selectedShared!=null?base+'/shared/'+selectedShared:'/api/v1/tf/gps/'+encodeURIComponent(selection.value));if(request!==generation)return;
  if(!Array.isArray(data.points)||data.points.length<2||data.points.at(-1).t<=data.points[0].t)throw Error(t('short'));
  record=structuredClone(window.InfraGo?.normalize(data)||data);clock=new PlaybackClock(record.points.at(-1).t-record.points[0].t);clock.speed(Number(speed.value));seek.max=String(clock.duration);
  if(!recorder)recorder=window.GpsRecorder.mount({demo:true,demoShared:()=>selectedShared!=null,userId:user.id,journeyId:'demo',container:map,trainNumber:()=>record.train_number,readonly:()=>true,now:()=>record?record.points[0].t+(clock?.position||0):0});
  recorder.mapState={mode:'follow',zoom:10};recorder.focusedStopKey=null;await recorder.readyPromise;try{await enrichStops(request);dsHint.textContent=t('ds100');}catch(error){dsHint.textContent=t('ds100_error');}if(request!==generation)return;if(selectedShared!=null&&!await verifyAccess())return;map.hidden=false;render();status.textContent=t('ready');if(selectedShared!=null)accessTimer=setInterval(verifyAccess,30000);
 }catch(error){status.textContent=error.message===t('short')?t('short'):t('error');}finally{busy=false;for(const control of [load,more,selection])control.disabled=false;for(const control of [play,reset,speed,seek])control.disabled=!clock;}};
 play.onclick=async()=>{if(!clock||busy)return;if(selectedShared!=null&&!await verifyAccess())return;if(clock.playing){clock.pause();stopTimer();}else{clock.play();run();}render();};
 reset.onclick=()=>{clock?.pause();clock?.seek(0);stopTimer();render();};
 speed.onchange=()=>{clock?.speed(Number(speed.value));render();};seek.oninput=()=>{clock?.seek(Number(seek.value));render();};
 const pause=()=>{clock?.pause();stopTimer();render();};
 window.addEventListener('pagehide',()=>{generation++;pause();clearInterval(accessTimer);});document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')pause();});
 window.addEventListener('languagechange',()=>{for(const [element,key] of labels)element.textContent=t(key);selection.setAttribute('aria-label',t('choose'));seek.setAttribute('aria-label',t('seek'));fillSelection();render();});
 window.addEventListener('focus',()=>{window.GpsPreferences?.load(user.id).then(()=>render()).catch(()=>{});});
 if(administration){more.hidden=true;await listingShared();}else{await listing();await listingShared();}
};
})();
