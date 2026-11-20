/* Android map interaction: compositor preview, one committed redraw, no data edits. */
(()=>{
const controllers=new WeakMap(),engaged=new Set();
function mount(element,options){
 if(controllers.has(element))return controllers.get(element);
 const pointers=new Map();let base=null,anchor=null,current=null,svg=null,inverse=null,matrix=null,bounds=null,active=false,frame=0,pending=null,suppressUntil=0;
 element.style.touchAction='none';
 const point=e=>{if(inverse){const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(inverse);return {x:p.x,y:p.y};}return {x:(e.clientX-bounds.left)*base.width/bounds.width,y:(e.clientY-bounds.top)*base.height/bounds.height};};
 const begin=()=>{anchor={view:{...current,center:{...current.center}},points:[...pointers.values()].slice(0,2).map(p=>({...p}))};};
 function capture(){active=true;svg.style.willChange='transform';svg.style.transformOrigin='0 0';for(const id of pointers.keys())try{element.setPointerCapture(id);}catch{}}
 function paint(){frame=0;if(!active||!svg||!current)return;const scale=2**(current.zoom-base.zoom),size=256*2**current.zoom,tx=base.width/2*(1-scale)+(base.center.x-current.center.x)*size,ty=base.height/2*(1-scale)+(base.center.y-current.center.y)*size;
 const a=matrix?.a||bounds.width/base.width,d=matrix?.d||bounds.height/base.height,x=tx*a+((matrix?.e??bounds.left)-bounds.left)*(1-scale),y=ty*d+((matrix?.f??bounds.top)-bounds.top)*(1-scale);svg.style.transform=`matrix(${scale},0,0,${scale},${x},${y})`;svg.style.clipPath=`inset(${Math.max(0,-y/scale)}px ${Math.max(0,bounds.width-(bounds.width-x)/scale)}px ${Math.max(0,bounds.height-(bounds.height-y)/scale)}px ${Math.max(0,-x/scale)}px)`;}
 function reset(cancel=false){if(frame)cancelAnimationFrame(frame);frame=0;if(svg){svg.style.transform='';svg.style.clipPath='';svg.style.transformOrigin='';svg.style.willChange='';}const changed=active,view=current,deferred=pending;active=false;base=anchor=current=svg=inverse=matrix=bounds=null;pending=null;const ids=[...pointers.keys()];pointers.clear();for(const id of ids)try{element.releasePointerCapture(id);}catch{}if(changed)suppressUntil=Date.now()+600;engaged.delete(api);if(changed&&!cancel)options.change(view,!!deferred);else if(deferred)requestAnimationFrame(deferred);}
 const down=e=>{if(e.pointerType!=='touch'||options.disabled?.()||e.target.closest?.('button,a,input,select,textarea,label'))return;const target=options.svg();if(!target||!target.contains(e.target))return;const view=options.view();if(!view)return;
 if(!pointers.size){svg=target;bounds=svg.getBoundingClientRect();if(!bounds.width||!bounds.height)return;matrix=svg.getScreenCTM?.();inverse=matrix?.inverse();base={width:600,height:650,minZoom:5,maxZoom:18,...view,center:{...view.center}};current={...base,center:{...base.center}};}
 e.stopPropagation();engaged.add(api);pointers.set(e.pointerId,point(e));begin();if(pointers.size>=2){e.preventDefault();capture();}};
 const move=e=>{if(!pointers.has(e.pointerId)||!anchor)return;e.stopPropagation();pointers.set(e.pointerId,point(e));const ps=[...pointers.values()].slice(0,2),g=anchor;if(ps.length!==g.points.length)return;
 const mid=list=>({x:list.reduce((s,p)=>s+p.x,0)/list.length,y:list.reduce((s,p)=>s+p.y,0)/list.length}),before=mid(g.points),after=mid(ps);let zoom=g.view.zoom;if(ps.length===2){const first=Math.hypot(g.points[0].x-g.points[1].x,g.points[0].y-g.points[1].y),next=Math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y);if(first<2||next<2)return;zoom=Math.max(base.minZoom,Math.min(base.maxZoom,g.view.zoom+Math.log2(next/first)));}
 if(!active&&Math.hypot(after.x-before.x,after.y-before.y)*(matrix?.a||bounds.width/base.width)<5)return;
 e.preventDefault();if(!active)capture();const oldSize=256*2**g.view.zoom,size=256*2**zoom;current={...base,zoom,center:{x:Math.max(0,Math.min(1,g.view.center.x+(before.x-base.width/2)/oldSize-(after.x-base.width/2)/size)),y:Math.max(0,Math.min(1,g.view.center.y+(before.y-base.height/2)/oldSize-(after.y-base.height/2)/size))}};if(!frame)frame=requestAnimationFrame(paint);};
 const up=e=>{if(!pointers.has(e.pointerId))return;e.stopPropagation();pointers.delete(e.pointerId);if(!pointers.size)reset();};
 const cancel=e=>{if(pointers.has(e.pointerId))reset(true);};
 element.addEventListener('pointerdown',down,{capture:true,passive:false});element.addEventListener('pointermove',move,{capture:true,passive:false});element.addEventListener('pointerup',up,true);element.addEventListener('pointercancel',cancel,true);element.addEventListener('lostpointercapture',cancel,true);
 element.addEventListener('click',e=>{if(e.detail&&Date.now()<suppressUntil&&!e.target.closest?.('button,a,input,select,textarea,label')){e.preventDefault();e.stopImmediatePropagation();}},true);
 const api={get active(){return active;},get view(){const value=options.view();return value?{...value,center:{...value.center}}:null;},defer(callback){if(!pointers.size)return false;pending=callback;return true;},cancel:()=>reset(true)};controllers.set(element,api);return api;
}
function tiles(svg,make,view,template='https://tile.openstreetmap.org/{z}/{x}/{y}.png'){
 const z=Math.floor(view.zoom),width=view.width||600,height=view.height||650,tileSize=256*2**(view.zoom-z),count=2**z;
 for(let x=Math.floor(view.left/tileSize);x<=Math.floor((view.left+width)/tileSize);x++)for(let y=Math.floor(view.top/tileSize);y<=Math.floor((view.top+height)/tileSize);y++){if(y<0||y>=count)continue;const image=make('image');for(const [k,v]of Object.entries({x:x*tileSize-view.left,y:y*tileSize-view.top,width:tileSize,height:tileSize,href:template.replace('{z}',z).replace('{x}',((x%count)+count)%count).replace('{y}',y),referrerpolicy:'origin'}))image.setAttribute(k,v);svg.append(image);}
}
for(const event of ['blur','pagehide','resize'])window.addEventListener(event,()=>{for(const controller of [...engaged])controller.cancel();});
window.MapGestures={mount,tiles};
})();
