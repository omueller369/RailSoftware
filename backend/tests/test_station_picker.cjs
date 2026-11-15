const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
class E {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.events={};this.style={};this.value='';this.isConnected=true;}
 append(...items){this.children.push(...items);for(const item of items)item.parentElement=this;}
 replaceChildren(...items){this.children=[];this.append(...items);}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}
 addEventListener(k,f){(this.events[k]||=[]).push(f);}dispatchEvent(e){for(const f of this.events[e.type]||[])f(e);}
 focus(){if(document.activeElement!==this){document.activeElement=this;this.dispatchEvent({type:'focus'});}}
 closest(){return null;}getBoundingClientRect(){return {left:20,top:50,bottom:90,width:200};}
 querySelectorAll(tag){return this.children.filter(e=>e.tag===tag);}contains(e){return this.children.includes(e);}
}
const document={body:new E('body'),activeElement:null,createElement:tag=>new E(tag)},window={};
const ctx={window,document,innerWidth:800,innerHeight:600,addEventListener(){},Event,fetch(){throw Error('Unexpected network');},setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/station-picker.js','utf8'),ctx);
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 const input=new E('input');input.setAttribute('list','old-native-list');document.body.append(input);
 const pending=new Map();window.StationPicker.mount(input,{frequent:async()=>Array.from({length:7},(_,i)=>({code:'F'+i,name:'Ort '+i})),search:q=>new Promise(resolve=>pending.set(q,resolve))});
 input.focus();await delay(20);const list=document.body.children.find(e=>e.tag==='div');assert.equal(input.attrs.list,undefined);assert.equal(list.querySelectorAll('button').length,5);assert.equal(input.attrs['aria-expanded'],'true');
 input.value='A';input.dispatchEvent({type:'input'});await delay(200);input.value='AB';input.dispatchEvent({type:'input'});await delay(200);
 pending.get('AB')([{code:'AB',name:'Aktuell'}]);await delay(1);pending.get('A')([{code:'A',name:'Veraltet'}]);await delay(1);
 assert.equal(list.querySelectorAll('button')[0].textContent,'AB · Aktuell','Old responses cannot overwrite current suggestions');
 let changed=0;input.addEventListener('change',()=>changed++);list.querySelectorAll('button')[0].onclick();assert.equal(input.value,'AB · Aktuell');assert.equal(changed,1);assert.equal(list.hidden,true);
 input.value='';input.dispatchEvent({type:'input'});await delay(10);assert.equal(list.querySelectorAll('button').length,5,'Frequent places return when field is cleared');
 input.dispatchEvent({type:'keydown',key:'ArrowDown',preventDefault(){}});input.dispatchEvent({type:'keydown',key:'Enter',preventDefault(){},stopPropagation(){}});assert.equal(input.value,'F0 · Ort 0');assert.equal(list.hidden,true);
 console.log('Station picker: five frequent places, native-list replacement, stale-response protection, touch and keyboard selection passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
