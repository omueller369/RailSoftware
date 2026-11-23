/* Regressionstests für Zugfahrten und deren Detailerfassung. */
const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.handlers={};this.attrs={};this.value='';}
 append(...nodes){for(const node of nodes){node.remove();node.parentElement=this;this.children.push(node);}}
 before(node){const p=this.parentElement;node.remove();p.children.splice(p.children.indexOf(this),0,node);node.parentElement=p;}
 replaceWith(node){this.before(node);this.remove();}
 remove(){if(this.parentElement){const p=this.parentElement;p.children.splice(p.children.indexOf(this),1);this.parentElement=null;}}
 setAttribute(k,v){this.attrs[k]=v;}addEventListener(k,f){this.handlers[k]=f;}
 showModal(){this.open=true;}close(){this.open=false;this.onclose?.();}focus(){this.focused=true;}
}
const body=new Element('body'),events={},requests=[];
const document={body,activeElement:new Element('button'),createElement:t=>new Element(t),createComment:()=>new Element('comment'),addEventListener:(e,f)=>events[e]=f};
const window={AndroidPortal:{request:async(method,args)=>{requests.push([method,args]);}},addEventListener(){}};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/train-workspace.js','utf8'),{window,document,URL,location:{origin:'https://example.test'},navigator:{}});
const host=new Element('host'),map=new Element('map'),digiButton=new Element('button'),pauseButton=new Element('button'),manualButton=new Element('button'),manualDuration=new Element('strong');body.append(host);host.append(digiButton,pauseButton,manualButton,manualDuration,map);
let draws=0;const recording={points:[1,2],running:true},recorder={o:{},map,digiButton,pauseButton,manualButton,manualDuration,record:recording,drawMap(){draws++;}};
window.TrainWorkspace.fullscreen(recorder);assert.equal(map.parentElement.tag,'dialog');assert.equal(manualButton.parentElement.parentElement,map.parentElement);assert.equal(recorder.record,recording);assert(recording.running);
assert(window.TrainWorkspace.back());assert.deepEqual(host.children,[digiButton,pauseButton,manualButton,manualDuration,map]);assert.equal(draws,2);assert.equal(requests[0][1].enabled,true);assert.equal(requests[1][1].enabled,false);
window.TrainWorkspace.fullscreen(recorder);window.TrainWorkspace.exitFullscreen(recorder);assert.equal(map.parentElement,host,'External command exits fullscreen before opening');assert.equal(pauseButton.parentElement,host);
const journey={id:'journey-1',fields:{train_number:{value:'00123'},start_at:{value:'2026-11-15T10:00'}}};window.TrainWorkspace.brake(journey);const overlay=body.children.at(-1),iframe=overlay.children[1];assert.equal(overlay.open,true);assert.equal(new URL(iframe.src,'https://example.test').searchParams.get('overlay'),'journey-1');assert(window.TrainWorkspace.back());window.TrainWorkspace.brake(journey);assert.equal(body.children.at(-1),overlay);assert.equal(overlay.children[1],iframe,'Closing and reopening preserves the editing iframe');assert(recording.running);window.TrainWorkspace.back();
window.TrainWorkspace.brake({...journey,id:'journey-2'});assert.notEqual(body.children.at(-1),overlay,'Separate journey draft');window.TrainWorkspace.back();
window.TrainWorkspace.brake({...journey,id:'../invalid'});assert.equal(body.children.filter(e=>e.open).length,0);
recorder.o.demo=true;window.TrainWorkspace.fullscreen(recorder);assert.equal(digiButton.parentElement,host,'Demo does not expose recording controls');window.TrainWorkspace.back();
console.log('Train workspace: same recording DOM, native screen mode, back, per-journey cached brake overlays and demo isolation passed.');
