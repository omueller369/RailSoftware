const fs=require('fs'),vm=require('./localized-vm.cjs'),assert=require('assert');
let scheduled=[],changes=[],listeners={},globalEvents={};
const svg={style:{},contains:()=>true,getBoundingClientRect:()=>({left:0,top:0,width:600,height:650})},map={style:{},addEventListener:(name,fn)=>listeners[name]=fn,setPointerCapture(){},releasePointerCapture(){}};
map.append=()=>{};
const context={document:{createElement:()=>({style:{},setAttribute(){},remove(){}})},window:{addEventListener:(name,fn)=>globalEvents[name]=fn},requestAnimationFrame:fn=>(scheduled.push(fn),scheduled.length),cancelAnimationFrame(){},Date,Math,Map,Set,WeakMap};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/map-gestures.js','utf8'),context);
let view={zoom:8,center:{x:.5,y:.5},width:600,height:650};const api=context.window.MapGestures.mount(map,{svg:()=>svg,view:()=>view,change:value=>{changes.push(value);view=value;}});
const event=(id,x,y,extra={})=>({pointerId:id,clientX:x,clientY:y,pointerType:'touch',isPrimary:id===1,target:svg,preventDefault(){this.prevented=true;},stopPropagation(){this.stopped=true;},...extra});
const flush=()=>{const work=scheduled;scheduled=[];for(const fn of work)fn();};
listeners.pointerdown(event(1,200,325));listeners.pointerdown(event(2,400,325));assert(api.active,'Second non-primary touch begins pinch');
for(let n=0;n<30;n++){listeners.pointermove(event(1,200-n*2,325));listeners.pointermove(event(2,400+n*2,325));flush();}
assert.equal(changes.length,0,'Sixty move events never rebuild the map');assert(!svg.style.transform&&!svg.style.clipPath&&!svg.style.willChange,'No large GPU transform, clip surface or will-change layer is allocated');
listeners.pointerup(event(1,142,325));assert.equal(changes.length,0);listeners.pointerup(event(2,458,325));assert.equal(changes.length,1,'Gesture commits once after both fingers lift');assert(view.zoom>8&&view.zoom<9,'Smooth fractional zoom survives release');assert(Math.abs(view.center.x-.5)<1e-9,'Geographic pinch midpoint remains anchored');assert.equal(svg.style.transform,'');
const zoom=view.zoom;listeners.pointerdown(event(1,100,325));listeners.pointerdown(event(2,500,325));listeners.pointermove(event(1,200,325));listeners.pointermove(event(2,400,325));listeners.pointerup(event(1,200,325));listeners.pointerup(event(2,400,325));assert(view.zoom<zoom,'Pinch inward zooms out');
const before=changes.length;listeners.pointerdown(event(1,250,325));listeners.pointerup(event(1,250,325));assert.equal(changes.length,before,'Tap does not pan or zoom');
listeners.pointerdown(event(1,200,300));listeners.pointermove(event(1,250,350));listeners.pointercancel(event(1,250,350));assert.equal(changes.length,before,'Cancellation does not commit a partial gesture');assert.equal(svg.style.transform,'');
const images=[],make=()=>({setAttribute(k,v){this[k]=v;}});context.window.MapGestures.tiles({append:x=>images.push(x)},make,{zoom:8.5,left:-10,top:300,width:600,height:300});assert(images.length>0);for(const image of images){assert(image.href.includes('/8/'),'Fractional views request integer tile levels');assert(image.width>256,'Tiles scale to fractional zoom');assert(!image.href.includes('/-'),'Tile x values wrap at the date line');}
console.log('Android maps: two-finger zoom both ways, stable focal point, sixty preview-only moves, one commit, taps, cancellation and fractional tiles passed.');
