const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
class E{constructor(tag){this.tag=tag;this.children=[];}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}setAttribute(){} }
const walk=root=>root.children.flatMap(n=>[n,...walk(n)]);
async function boot(native){const root=new E('main'),events={},calls=[];let state={version:'0.26.45-test.13',available:false,checking:false,gps_running:false},poll;
const window={addEventListener:(key,fn)=>events[key]=fn};if(native)window.AndroidPortal={request:async method=>{calls.push(method);if(method==='updates.check')state.available=true;return {...state};}};
const context={window,document:{getElementById:()=>root,createElement:tag=>new E(tag)},fetch:async()=>({ok:true,json:async()=>({version:'0.26.46'})}),setInterval:fn=>(poll=fn,1),clearInterval(){}};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/updates.js','utf8'),context);await window.startUpdates();return {root,calls,state,events,poll};}
(async()=>{
let app=await boot(true);const [check,install]=walk(app.root).filter(n=>n.tag==='button');assert(install.hidden);await check.onclick();assert.equal(install.hidden,false);assert(app.calls.includes('updates.check'));app.state.gps_running=true;await app.poll();assert(check.disabled&&install.disabled);assert.equal(walk(app.root).filter(n=>n.tag==='li').length,6);assert(app.root.children[0].textContent.includes('0.26.46'));assert(app.root.children[1].textContent.includes('0.26.45-test.13'));app.events.pagehide();
app=await boot(false);assert(walk(app.root).filter(n=>n.tag==='button').every(n=>n.hidden));assert.equal(walk(app.root).find(n=>n.tag==='a').href,'https://github.com/omueller369/RailSoftware/releases');
const html=vm.resolveHtml(fs.readFileSync('backend/lokzeitleiste/static/tf-portal.html','utf8'));for(const label of ['Doks.-Verwaltung',"Meine Bhf's",'Mein Konto','Bremszettel Int.','Bremszettel DE'])assert(html.includes(label));assert(html.includes('href="/tf/updates"'));
console.log('Updates module: history, web/native versions, check/install, GPS guard and short tile names: PASS');})().catch(error=>{console.error(error);process.exitCode=1;});
