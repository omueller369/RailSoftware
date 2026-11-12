const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
let now=0,tick;
const context={window:{},structuredClone,performance:{now:()=>now},setInterval:fn=>(tick=fn,1),clearInterval(){}};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/gps-demo.js','utf8'),context);
const Clock=context.window.GpsDemoClock,clock=new Clock(5*3600000,()=>now);
clock.speed(300);clock.play();now=30000;assert.equal(clock.update(),2.5*3600000);clock.pause();now=60000;assert.equal(clock.update(),2.5*3600000);
clock.speed(60);clock.play();now+=1000;assert.equal(clock.update(),2.5*3600000+60000);clock.seek(0);clock.speed(300);now+=60000;assert.equal(clock.update(),5*3600000);assert.equal(clock.playing,false);clock.play();assert.equal(clock.position,0);clock.seek(-1);assert.equal(clock.position,0);clock.seek(999999999);assert.equal(clock.position,clock.duration);
const source={train_number:'123',ended:true,points:[0,5000,60000].map(t=>({t:1792627200000+t,lat:52,lon:13,accuracy:5,speed:10})),manual_stops:[{key:'manual-1792627210000',start:1792627210000,end:1792627250000}],stop_edits:{'manual-1792627210000':{end:1792627250000}}};
const before=JSON.stringify(source),frame=context.window.GpsDemoFrame(source,20000);assert.equal(frame.points.length,2);assert.equal(frame.manual_stops[0].end,source.points[0].t+20000);assert.equal(frame.stop_edits['manual-1792627210000'].end,source.points[0].t+20000);frame.points[0].lat=0;assert.equal(JSON.stringify(source),before);
class E{constructor(tag){this.tag=tag;this.children=[];this.value='';}append(...items){this.children.push(...items);if(this.tag==='select'&&!this.value&&this.children.length)this.value=this.children[0].value;}replaceChildren(...items){this.children=[];this.value='';this.append(...items);}setAttribute(){} }
const workspace=new E('div'),events={},requests=[];let mounts=0,draws=0;
context.document={getElementById:()=>workspace,createElement:tag=>new E(tag),addEventListener:(key,fn)=>events[key]=fn};
context.window.addEventListener=(key,fn)=>events[key]=fn;
context.window.GpsRecorder={isActive:()=>false,mount:options=>{mounts++;assert(options.demo);assert(options.readonly());return {readyPromise:Promise.resolve(),drawMap(){draws++;}};}};
context.fetch=async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>url.includes('gps-recordings')?{items:[{journey_id:'record',train_number:'123',start:source.points[0].t,end:source.points.at(-1).t}],next_offset:null}:source};};
const walk=root=>root.children.flatMap(child=>[child,...walk(child)]);
(async()=>{await context.window.startGpsDemo({id:1});const [load,more,play,reset]=walk(workspace).filter(e=>e.tag==='button'),[selection,speed]=walk(workspace).filter(e=>e.tag==='select'),seek=walk(workspace).find(e=>e.tag==='input');
assert.equal(load.disabled,false);await load.onclick();assert.equal(mounts,1);assert(draws>0);assert.equal(play.disabled,false);speed.value='300';speed.onchange();play.onclick();now+=100;tick();seek.value='30000';seek.oninput();reset.onclick();assert.equal(seek.value,'0');assert.equal(JSON.stringify(source),before);assert(requests.every(r=>!r.options.method||r.options.method==='GET'));assert.equal(requests.length,2);events.pagehide();
console.log('GPS demo: accelerated clock, pause/seek/speed/end, immutable frame, read-only selection and playback: PASS');})().catch(error=>{console.error(error);process.exitCode=1;});
