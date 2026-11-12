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
function frame(record,position){
 const at=record.points[0].t+position;let lo=0,hi=record.points.length;
 while(lo<hi){const mid=(lo+hi)>>1;if(record.points[mid].t<=at)lo=mid+1;else hi=mid;}
 const result={...record,ended:false,points:record.points.slice(0,Math.max(1,lo)).map(p=>({...p})),manual_stops:(record.manual_stops||[]).filter(row=>row.start<at).map(row=>({...row,end:Math.min(row.end??at,at)})),stop_edits:{}};
 for(const [key,edit] of Object.entries(record.stop_edits||{}))result.stop_edits[key]={...edit,end:edit.end==null?edit.end:Math.min(edit.end,at)};
 return result;
}
window.GpsDemoClock=PlaybackClock;window.GpsDemoFrame=frame;
window.startGpsDemo=async user=>{
 const S={"title":globalThis.CtlText.source("portal_gps_demo.text_d2a6f5151788"),"intro":globalThis.CtlText.source("portal_gps_demo.text_a6049edf9076"),"choose":globalThis.CtlText.source("portal_gps_demo.text_f16c8f77fea5"),"load":globalThis.CtlText.source("portal_gps_demo.text_733ad2485ad5"),"more":globalThis.CtlText.source("portal_gps_demo.text_aad9dcac6b10"),"play":globalThis.CtlText.source("portal_gps_demo.text_04247a96a379"),"pause":globalThis.CtlText.source("portal_gps_demo.text_0dbc3031125b"),"reset":globalThis.CtlText.source("portal_gps_demo.text_eed905d69f7c"),"speed":globalThis.CtlText.source("portal_gps_demo.text_71fd00b93880"),"seek":globalThis.CtlText.source("portal_gps_demo.text_a07eb1f899c9"),"empty":globalThis.CtlText.source("portal_gps_demo.text_925dd49e6aeb"),"loading":globalThis.CtlText.source("portal_gps_demo.text_ae695c6d4099"),"ready":globalThis.CtlText.source("portal_gps_demo.text_0a01bd943ac8"),"running":globalThis.CtlText.source("portal_gps_demo.text_0fd0b42c9bbb"),"paused":globalThis.CtlText.source("portal_gps_demo.text_41d0cba18e6e"),"finished":globalThis.CtlText.source("portal_gps_demo.text_ea3d8f969fb3"),"error":globalThis.CtlText.source("portal_gps_demo.text_cb1011064bf5"),"blocked":globalThis.CtlText.source("portal_gps_demo.text_75343232c7e8"),"short":globalThis.CtlText.source("portal_gps_demo.text_a4c937f3e189"),"hint":globalThis.CtlText.source("portal_gps_demo.text_90ab31825729"),"help_title":globalThis.CtlText.source("portal_gps_demo.text_03151dda472f"),"help_short":globalThis.CtlText.source("portal_gps_demo.text_d409cda4d38e"),"help_steps":globalThis.CtlText.source("portal_gps_demo.text_fc8f9d005ba2"),"help_notes":globalThis.CtlText.source("portal_gps_demo.text_8e157c16c15f")},t=key=>window.I18n?.t(S[key])||S[key],workspace=document.getElementById('gpsDemoWorkspace'),labels=[];
 const node=(tag,key)=>{const element=document.createElement(tag);if(key){element.textContent=t(key);labels.push([element,key]);}return element;};
 const status=node('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 workspace.replaceChildren(status);if(window.GpsRecorder.isActive()){status.textContent=t('blocked');return;}
 const field=(caption,input)=>{const label=node('label'),text=node('span',caption);label.append(text,input);return label;};
 const selection=node('select'),load=node('button','load'),more=node('button','more'),play=node('button','play'),reset=node('button','reset'),speed=node('select'),seek=node('input'),time=node('output');
 selection.setAttribute('aria-label',t('choose'));seek.type='range';seek.min='0';seek.max='1';seek.step='1';seek.value='0';seek.setAttribute('aria-label',t('seek'));
 for(const rate of [1,5,10,30,60,120,300]){const option=node('option');option.value=String(rate);option.textContent=rate+'×';speed.append(option);}
 speed.value='1';for(const button of [load,more,play,reset])button.type='button';
 const loader=node('div');loader.className='gps-demo-controls';loader.append(field('choose',selection),load,more);
 const controls=node('div');controls.className='gps-demo-controls';controls.append(play,reset,field('speed',speed));
 const progress=field('seek',seek),map=node('div'),hint=node('p','hint');
 workspace.append(loader,controls,progress,time,hint,map);for(const control of [play,reset,speed,seek])control.disabled=true;
 let items=[],offset=0,record=null,clock=null,recorder=null,timer=null,busy=false,generation=0;
 const duration=ms=>[Math.floor(ms/3600000),Math.floor(ms/60000)%60,Math.floor(ms/1000)%60].map(n=>String(n).padStart(2,'0')).join(':');
 const date=ms=>new Intl.DateTimeFormat(window.I18n?.locale||'de-DE',{timeZone:'Europe/Berlin',dateStyle:'short',timeStyle:'short'}).format(new Date(ms));
 const fillSelection=()=>{const value=selection.value;selection.replaceChildren();for(const item of items){const option=node('option');option.value=item.journey_id;option.textContent=item.train_number+' · '+date(item.start)+' · '+duration(item.end-item.start);option.setAttribute('data-i18n-ignore','');selection.append(option);}if(items.some(item=>item.journey_id===value))selection.value=value;};
 const get=async url=>{const response=await fetch(url,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error(t('error'));return response.json();};
 const render=()=>{if(!clock||!record)return;clock.update();recorder.record=frame(record,clock.position);recorder.drawMap();seek.value=String(clock.position);seek.setAttribute('aria-valuetext',duration(clock.position)+' / '+duration(clock.duration));time.textContent=duration(clock.position)+' / '+duration(clock.duration)+' · '+date(record.points[0].t+clock.position);play.textContent=t(clock.playing?'pause':'play');const message=t(clock.playing?'running':clock.position>=clock.duration?'finished':'paused');if(status.textContent!==message)status.textContent=message;};
 const stopTimer=()=>{clearInterval(timer);timer=null;};
 const run=()=>{stopTimer();timer=setInterval(()=>{render();if(!clock.playing)stopTimer();},250);};
 const listing=async()=>{if(busy||offset==null)return;busy=true;more.disabled=load.disabled=true;status.textContent=t('loading');try{const data=await get('/api/v1/tf/gps-recordings?offset='+offset);items.push(...data.items);offset=data.next_offset;fillSelection();status.textContent=items.length?'':t('empty');}catch(error){status.textContent=t('error');}finally{busy=false;more.disabled=false;load.disabled=!items.length;more.hidden=offset==null;}};
 more.onclick=listing;
 load.onclick=async()=>{if(busy||!selection.value)return;busy=true;const request=++generation;stopTimer();clock?.pause();record=null;clock=null;map.hidden=true;for(const control of [load,more,play,reset,speed,seek,selection])control.disabled=true;status.textContent=t('loading');try{
  const data=await get('/api/v1/tf/gps/'+encodeURIComponent(selection.value));if(request!==generation)return;
  if(!Array.isArray(data.points)||data.points.length<2||data.points.at(-1).t<=data.points[0].t)throw Error(t('short'));
  record=structuredClone(data);clock=new PlaybackClock(record.points.at(-1).t-record.points[0].t);clock.speed(Number(speed.value));seek.max=String(clock.duration);
  if(!recorder)recorder=window.GpsRecorder.mount({demo:true,userId:user.id,journeyId:'demo',container:map,trainNumber:()=>record.train_number,readonly:()=>true,now:()=>record?record.points[0].t+(clock?.position||0):0});
  recorder.mapState={mode:'follow',zoom:10};recorder.focusedStopKey=null;await recorder.readyPromise;map.hidden=false;render();status.textContent=t('ready');
 }catch(error){status.textContent=error.message===t('short')?t('short'):t('error');}finally{busy=false;for(const control of [load,more,selection])control.disabled=false;for(const control of [play,reset,speed,seek])control.disabled=!clock;}};
 play.onclick=()=>{if(!clock||busy)return;if(clock.playing){clock.pause();stopTimer();}else{clock.play();run();}render();};
 reset.onclick=()=>{clock?.pause();clock?.seek(0);stopTimer();render();};
 speed.onchange=()=>{clock?.speed(Number(speed.value));render();};seek.oninput=()=>{clock?.seek(Number(seek.value));render();};
 const pause=()=>{clock?.pause();stopTimer();render();};
 window.addEventListener('pagehide',()=>{generation++;pause();});document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')pause();});
 window.addEventListener('languagechange',()=>{for(const [element,key] of labels)element.textContent=t(key);selection.setAttribute('aria-label',t('choose'));seek.setAttribute('aria-label',t('seek'));fillSelection();render();});
 await listing();
};
})();
