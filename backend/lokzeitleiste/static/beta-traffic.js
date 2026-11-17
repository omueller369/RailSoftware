/* Beta counters: Android UID counters, or explicitly labelled browser estimates. */
(()=>{
if(window.CtlTraffic)return;
const S={"upload":globalThis.CtlText.source("portal_beta60.text_bfb52ee297ae"),"download":globalThis.CtlText.source("portal_beta60.text_05f662d2e9f4"),"webmeter":globalThis.CtlText.source("portal_beta60.text_d754e9f36f12"),"nativemeter":globalThis.CtlText.source("portal_beta60.text_571a74ee9c6d")},t=k=>window.I18n?.t(S[k])||S[k];
let owner=window;try{if(window.parent!==window&&window.parent.location.origin===location.origin&&window.parent.CtlTraffic)owner=window.parent;}catch{}
let totals={upload:0,download:0};try{totals=JSON.parse(sessionStorage.getItem('rail.beta.traffic')||'null')||totals;}catch{}
const save=()=>{try{sessionStorage.setItem('rail.beta.traffic',JSON.stringify(totals));}catch{}};
const record=(upload=0,download=0)=>{if(owner!==window){owner.CtlTraffic.record(upload,download);return;}totals.upload+=Math.max(0,upload);totals.download+=Math.max(0,download);save();};
window.CtlTraffic={record};
const size=body=>{if(body==null)return 0;if(typeof body==='string')return new TextEncoder().encode(body).length;if(body instanceof Blob)return body.size;if(body instanceof ArrayBuffer||ArrayBuffer.isView(body))return body.byteLength;if(body instanceof URLSearchParams)return new TextEncoder().encode(body.toString()).length;if(body instanceof FormData){let bytes=0;for(const [key,value]of body.entries())bytes+=size(key)+size(value);return bytes;}return 0;};
const original=window.fetch.bind(window);window.fetch=async(input,options={})=>{const response=await original(input,options);if(!response.headers?.get('X-LokZeitleiste-Offline')){record(size(options.body));response.clone().blob().then(body=>record(0,body.size)).catch(()=>{});}return response;};
try{new PerformanceObserver(list=>{for(const r of list.getEntries())if(r.initiatorType!=='fetch')record(0,r.transferSize||0);}).observe({type:'resource',buffered:true});}catch{}
if(owner!==window)return;
const format=bytes=>{if(bytes<1024)return Math.round(bytes)+' B';if(bytes<1048576)return(bytes/1024).toFixed(1)+' KB';return(bytes/1048576).toFixed(2)+' MB';};
let polling=false,native=false;
async function render(){if(polling)return;polling=true;try{if(window.AndroidPortal?.request){const result=await window.AndroidPortal.request('traffic.status');if(result.upload>=0&&result.download>=0){totals=result;native=true;}}}catch{}finally{polling=false;}
 const hosts=[document.body,...document.querySelectorAll('dialog[open]')];for(const host of hosts){let meter=[...host.children].find(node=>node.classList?.contains('beta-traffic'));if(!meter){meter=document.createElement('aside');meter.className='beta-traffic';meter.setAttribute('data-i18n-ignore','');host.append(meter);}meter.title=t(native?'nativemeter':'webmeter');const up=document.createElement('span'),down=document.createElement('span');up.className='beta-upload';down.className='beta-download';up.textContent='DU: '+format(totals.upload);down.textContent='DL: '+format(totals.download);up.setAttribute('aria-label',t('upload')+' '+format(totals.upload));down.setAttribute('aria-label',t('download')+' '+format(totals.download));meter.replaceChildren(up,document.createTextNode(' / '),down);}
}
const start=()=>{render();setInterval(render,2000);};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();window.addEventListener('languagechange',render);
})();
