/* Read-only live feed: no device cache, no historical GPS access. */
(()=>{
const S={"tracking": globalThis.CtlText.source("dispatch_tracking.text_5a95db2aa8e5"), "count": globalThis.CtlText.source("dispatch_tracking.text_6c35493a2b93"), "error": globalThis.CtlText.source("dispatch_tracking.text_ca00fccfb408"), "refresh": globalThis.CtlText.source("dispatch_tracking.text_d6cc0a088c07")},t=k=>window.I18n?.t(S[k])||S[k],el=id=>document.getElementById(id),map=el('trackingMap');
if(!map)return;
const project=([lat,lon])=>({x:(lon+180)/360,y:(1-Math.asinh(Math.tan(lat*Math.PI/180))/Math.PI)/2});
let center=project([51.15,10.4]),zoom=6,network=null,positions=[],busy=false,stopped=false,error=false,controller=null;
function live(){return positions.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&Math.abs(p.lat)<85&&Number.isFinite(p.t)&&p.t>Date.now()-600000);}
function draw(){
 const ns='http://www.w3.org/2000/svg',make=tag=>document.createElementNS(ns,tag),svg=make('svg'),size=256*2**zoom,left=center.x*size-300,top=center.y*size-325;svg.setAttribute('viewBox','0 0 600 650');svg.setAttribute('role','img');svg.setAttribute('aria-label',t('tracking'));
 if(network)window.RailNetwork.draw(svg,make,network,{zoom,size,left,top});
 for(const p of live()){const at=project([p.lat,p.lon]),x=at.x*size-left,y=at.y*size-top;if(x<0||x>600||y<0||y>650)continue;const group=make('g');group.setAttribute('data-tracking-position',String(p.id));const image=make('image');for(const [key,value]of Object.entries({href:'/tf/gps-marker-electric.png',x:x-16,y:y-16,width:32,height:32}))image.setAttribute(key,value);group.append(image);
 for(const [field,dy]of [['train_number',-22],['first_name',30]]){if(typeof p[field]!=='string'||!p[field])continue;const text=make('text');text.setAttribute('x',x);text.setAttribute('y',y+dy);text.setAttribute('text-anchor','middle');text.setAttribute('data-tracking-label',field);text.textContent=p[field];group.append(text);}svg.append(group);}
 let drag=null;svg.onpointerdown=e=>{if(!e.isPrimary)return;drag={x:e.clientX,y:e.clientY,center:{...center}};svg.setPointerCapture(e.pointerId);};svg.onpointerup=e=>{if(!drag)return;const factor=600/svg.getBoundingClientRect().width;center={x:drag.center.x-(e.clientX-drag.x)*factor/size,y:Math.max(0,Math.min(1,drag.center.y-(e.clientY-drag.y)*factor/size))};drag=null;draw();};svg.onpointercancel=()=>drag=null;
 map.replaceChildren(svg);el('trackingStatus').textContent=error?t('error'):t('count')+': '+live().length;el('trackingMinus').disabled=zoom<=5;el('trackingPlus').disabled=zoom>=18;
}
async function load(){if(busy||stopped)return;busy=true;el('trackingRefresh').disabled=true;controller=new AbortController();try{const r=await fetch('/api/v1/admin/tracking/positions',{credentials:'same-origin',cache:'no-store',signal:controller.signal});if([401,403].includes(r.status)){positions=[];error=true;draw();stop();if(r.status===401)location.href='/admin';return;}if(!r.ok)throw Error();const data=await r.json();if(!Array.isArray(data.positions))throw Error();if(stopped)return;positions=data.positions;error=false;}catch(e){if(e.name!=='AbortError')error=true;}finally{busy=false;el('trackingRefresh').disabled=stopped;draw();}}
async function reload(){if(stopped)return;await Promise.all([load(),network?Promise.resolve():window.RailNetwork.load().then(data=>{network=data;draw();}).catch(()=>{error=true;draw();})]);}
function stop(){stopped=true;controller?.abort();clearInterval(poll);clearInterval(expiry);positions=[];draw();}
el('trackingRefresh').onclick=reload;el('trackingMinus').onclick=()=>{zoom=Math.max(5,zoom-1);draw();};el('trackingPlus').onclick=()=>{zoom=Math.min(18,zoom+1);draw();};el('trackingHome').onclick=()=>{center=project([51.15,10.4]);zoom=6;draw();};
const poll=setInterval(load,30000),expiry=setInterval(()=>{const current=live();if(current.length!==positions.length){positions=current;draw();}},1000);
window.addEventListener('pagehide',stop,{once:true});window.addEventListener('offline',()=>{error=true;draw();});window.addEventListener('online',reload);window.addEventListener('languagechange',()=>{el('trackingRefresh').textContent=t('refresh');draw();});
window.TrainTracking={reload,stop};draw();reload();
})();
