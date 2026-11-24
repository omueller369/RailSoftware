/* Gemeinsame Verarbeitung für öffentliche Eisenbahn-Referenzdaten. */
/* Öffentliche Offline-Geometrie ohne Einfluss auf die tatsächlich gefahrenen Strecken eines TF. */
(()=>{
const REVISION='46c6219268ba0fb31521540ef19506f6467025ee7663e7bd95909a94771c500a';
const HIDDEN_URBAN_SBAHN=new Set(["1224", "1225", "1226", "1239", "1240", "1241", "1244", "1270", "1271", "6002", "6004", "6005", "6006", "6007", "6008", "6009", "6010", "6011", "6012", "6017", "6018", "6019", "6020", "6021", "6023", "6024", "6025", "6030", "6032", "6033", "6034", "6035", "6036", "6039", "6044"]);
const routeVisible=route=>!HIDDEN_URBAN_SBAHN.has(String(Number(route)));
let loading;
function seed(){const data=window.RailNetworkSeed;if(data?.schema!==2||data.scale!==100000000||!Array.isArray(data.lines)||!Array.isArray(data.routes))throw Error('Invalid rail network bundle');return data;}
function load(){if(window.RailNetworkSeed)return Promise.resolve(seed());if(loading)return loading;loading=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/tf/rail-network-data.js?v='+REVISION;script.onload=()=>{try{resolve(seed());}catch(error){reject(error);}};script.onerror=()=>{script.remove();reject(Error('Rail network unavailable'));};document.head.append(script);}).catch(error=>{loading=null;throw error;});return loading;}
// Der räumliche Index wird je öffentlichem Datenbestand einmal aufgebaut.
const spatialIndexes=new WeakMap();
function spatial(data){let index=spatialIndexes.get(data);if(index)return index;const cell=data.scale/1024,grid=new Map(),broad=[],views=new Map();
 for(let id=0;id<data.lines.length;id++){const b=data.lines[id][2],x0=Math.floor(b[0]/cell),x1=Math.floor(b[2]/cell),y0=Math.floor(b[1]/cell),y1=Math.floor(b[3]/cell);if((x1-x0+1)*(y1-y0+1)>256){broad.push(id);continue;}for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){const key=x+','+y;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(id);}}
 index={cell,grid,broad,views,paths:new Map()};spatialIndexes.set(data,index);return index;
}
function visibleLines(data,view,padding=8){const index=spatial(data),factor=view.size/data.scale,key=[view.size,view.left,view.top,view.width||600,view.height||650,padding].join(':');if(index.views.has(key))return index.views.get(key);const loX=(view.left-padding)/factor,hiX=(view.left+(view.width||600)+padding)/factor,loY=(view.top-padding)/factor,hiY=(view.top+(view.height||650)+padding)/factor,ids=new Set(index.broad),x0=Math.floor(loX/index.cell),x1=Math.floor(hiX/index.cell),y0=Math.floor(loY/index.cell),y1=Math.floor(hiY/index.cell);
 if((x1-x0+1)*(y1-y0+1)>4096){for(let id=0;id<data.lines.length;id++)ids.add(id);}else for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++)for(const id of index.grid.get(x+','+y)||[])ids.add(id);
 const result=[...ids].sort((a,b)=>a-b).filter(id=>{const b=data.lines[id][2];return b[2]>=loX&&b[0]<=hiX&&b[3]>=loY&&b[1]<=hiY;});index.views.set(key,result);if(index.views.size>12)index.views.delete(index.views.keys().next().value);return result;
}
function clipSegment(ax,ay,bx,by,width,height,padding=8){const dx=bx-ax,dy=by-ay;let lo=0,hi=1;for(const [p,q]of [[-dx,ax+padding],[dx,width+padding-ax],[-dy,ay+padding],[dy,height+padding-ay]]){if(p===0){if(q<0)return null;continue;}const t=q/p;if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);if(lo>hi)return null;}return [ax+lo*dx,ay+lo*dy,ax+hi*dx,ay+hi*dy];}
function paths(data,view){
 const index=spatial(data),key=[view.zoom,view.size,view.left,view.top,view.width||600,view.height||650].join(':');if(index.paths.has(key))return index.paths.get(key);
 const paths=['','',''];let visible=0;const factor=view.size/data.scale,left=view.left,top=view.top,width=view.width||600,height=view.height||650;
 for(const id of visibleLines(data,view)){const row=data.lines[id];if(!routeVisible(data.routes[row[0]][0]))continue;const coords=row[view.zoom<=9?4:3],b=row[2];let path='',lastX,lastY;
  if(b[0]*factor-left>=-8&&b[2]*factor-left<=width+8&&b[1]*factor-top>=-8&&b[3]*factor-top<=height+8){for(let i=0;i<coords.length;i+=2)path+=(i?'L':'M')+(coords[i]*factor-left).toFixed(1)+' '+(coords[i+1]*factor-top).toFixed(1);if(path){paths[row[1]]+=path;visible++;}continue;}
  for(let i=2;i<coords.length;i+=2){const part=clipSegment(coords[i-2]*factor-left,coords[i-1]*factor-top,coords[i]*factor-left,coords[i+1]*factor-top,width,height);if(!part){lastX=lastY=undefined;continue;}const [ax,ay,bx,by]=part,x=ax.toFixed(1),y=ay.toFixed(1);if(x!==lastX||y!==lastY)path+='M'+x+' '+y;lastX=bx.toFixed(1);lastY=by.toFixed(1);path+='L'+lastX+' '+lastY;}
  if(path){paths[row[1]]+=path;visible++;}
 }
 const result={paths,visible};index.paths.set(key,result);if(index.paths.size>12)index.paths.delete(index.paths.keys().next().value);return result;
}
// VzG-Beschriftungen zeigen Referenzdaten und vergeben keine Streckenkenntnis.
function labels(svg,make,data,view){
 if(view.zoom<11)return 0;
 const width=view.width||600,height=view.height||650,factor=view.size/data.scale,candidates=new Map(),occupied=[];
 // Bahnhofspunkte und ihre Beschriftungen müssen auch bei hoher Vergrößerung anklickbar bleiben.
 for(const p of window.M1Map?.visiblePoints?.(view,90)||window.M1Map?.points()?.projected||[]){if(!routeVisible(p.point.route))continue;const x=p.x*view.size-view.left,y=p.y*view.size-view.top;if(x<-80||x>width+20||y<-20||y>height+30)continue;occupied.push([x-10,y-(view.zoom>=12?24:10),x+(view.zoom>=12?12+p.point.code.length*7:10),y+10]);}
 function clip(ax,ay,bx,by){const dx=bx-ax,dy=by-ay;let lo=0,hi=1;for(const [p,q]of [[-dx,ax-8],[dx,width-8-ax],[-dy,ay-8],[dy,height-8-ay]]){if(p===0){if(q<0)return null;continue;}const t=q/p;if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);if(lo>hi)return null;}return [ax+lo*dx,ay+lo*dy,ax+hi*dx,ay+hi*dy];}
 for(const id of visibleLines(data,view,0)){const row=data.lines[id];if(!routeVisible(data.routes[row[0]][0]))continue;const box=row[2];if(box[2]*factor<view.left||box[0]*factor>view.left+width||box[3]*factor<view.top||box[1]*factor>view.top+height)continue;const code=String(data.routes[row[0]][0]),coords=row[3],segments=[];let length=0;
  for(let i=2;i<coords.length;i+=2){const part=clip(coords[i-2]*factor-view.left,coords[i-1]*factor-view.top,coords[i]*factor-view.left,coords[i+1]*factor-view.top);if(!part)continue;const size=Math.hypot(part[2]-part[0],part[3]-part[1]);if(size>0){segments.push([...part,size]);length+=size;}}
  if(length<32)continue;if(!candidates.has(code))candidates.set(code,[]);const list=candidates.get(code);list.push({length,segments});list.sort((a,b)=>b.length-a.length);if(list.length>5)list.pop();
 }
 let count=0;
 for(const [code,lines]of [...candidates].sort((a,b)=>b[1][0].length-a[1][0].length||a[0].localeCompare(b[0]))){let placed=false;const half=Math.max(19,code.length*7/2+7);
  for(const line of lines){for(const fraction of [.5,.25,.75]){let at=line.length*fraction,segment=line.segments.at(-1);for(const current of line.segments){segment=current;if(at<=current[4])break;at-=current[4];}const [ax,ay,bx,by,size]=segment,part=Math.min(1,at/size),x=ax+(bx-ax)*part-(by-ay)/size*14,y=ay+(by-ay)*part+(bx-ax)/size*14,box=[x-half,y-11,x+half,y+11];if(box[0]<3||box[1]<3||box[2]>width-3||box[3]>height-3||occupied.some(b=>box[0]<b[2]+4&&box[2]>b[0]-4&&box[1]<b[3]+4&&box[3]>b[1]-4))continue;
    const group=make('g'),back=make('rect'),text=make('text');group.setAttribute('data-rail-route-label',code);group.setAttribute('pointer-events','none');group.setAttribute('aria-hidden','true');for(const [k,v]of Object.entries({x:box[0],y:box[1],width:half*2,height:22,rx:4,fill:'#fff','fill-opacity':'.94',stroke:'#000','stroke-width':.8}))back.setAttribute(k,v);for(const [k,v]of Object.entries({x,y:y+4,'text-anchor':'middle','font-size':12,'font-weight':700,fill:'#ff0000',stroke:'#000','stroke-width':.65,'stroke-linejoin':'round','paint-order':'stroke','data-i18n-ignore':''}))text.setAttribute(k,v);text.textContent=code;group.append(back,text);svg.append(group);occupied.push(box);count++;placed=true;break;
   }if(placed)break;}
  if(count>=100)break;
 }
 return count;
}
function draw(svg,make,data,view){if(data.lines.length)window.PolandRailNetwork?.draw(svg,make,view);const result=paths(data,view);for(const [state,d] of result.paths.entries()){if(!d)continue;const path=make('path');path.setAttribute('d',d);path.setAttribute('fill','none');path.setAttribute('stroke',['#4A4A4A','#8b8378','#ffff00'][state]);path.setAttribute('stroke-width',state===0?'2.7':'3.2');path.setAttribute('stroke-linecap','round');path.setAttribute('stroke-linejoin','round');if(state)path.setAttribute('stroke-dasharray',state===1?'10 6':'4 6');path.setAttribute('data-rail-network',String(state));path.setAttribute('aria-hidden','true');svg.append(path);}labels(svg,make,data,view);return result.visible;}
window.RailNetwork={load,paths,draw,labels,visibleLines,clipSegment,visible:routeVisible,revision:REVISION};
})();
