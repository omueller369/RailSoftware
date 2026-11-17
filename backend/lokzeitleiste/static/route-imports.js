/* Explicit imported knowledge on reference lines, separate from GPS passage counts. */
(()=>{
const indexes=new WeakMap(),formatter=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'});let cachedMinute,cachedToday;function today(now){const minute=Math.floor(now/60000);if(minute!==cachedMinute){const parts=Object.fromEntries(formatter.formatToParts(new Date(now)).map(p=>[p.type,p.value]));cachedToday=[parts.year,parts.month,parts.day].join('-');cachedMinute=minute;}return cachedToday;}
function prepare(data){if(indexes.has(data))return indexes.get(data);const routes=new Map();for(const row of data.lines){if(!row[5])continue;const code=String(Number(data.routes[row[0]][0]));if(!routes.has(code))routes.set(code,[]);let total=0;const lengths=[0],coords=row[3];for(let i=2;i<coords.length;i+=2){total+=Math.hypot(coords[i]-coords[i-2],coords[i+1]-coords[i-1]);lengths.push(total);}routes.get(code).push({row,lengths,total});}indexes.set(data,routes);return routes;}
function state(row,now=Date.now()){if(row.status==='abgelaufen')return 'expired';const value=row.valid_until;if(/^\d{4}-\d{2}-\d{2}$/.test(value)&&value!=='0000-00-00'){if(value<today(now))return 'expired';}return row.status==='streckenkundig'?'qualified':'learning';}
function paths(data,items,view,revision,now=Date.now()){
 const groups={expired:'',learning:'',qualified:''},routes=prepare(data),factor=view.size/data.scale;
 for(const item of items){const m=item.map_match;if(!m||!['mapped','partial'].includes(m.status)||m.reference_revision!==revision||!Number.isFinite(m.from_m)||!Number.isFinite(m.to_m))continue;const lo=Math.min(m.from_m,m.to_m),hi=Math.max(m.from_m,m.to_m),kind=state(item,now);
  for(const info of routes.get(String(Number(m.route)))||[]){const row=info.row,mile=row[5],bounds=row[2];if(!info.total||bounds[2]*factor<view.left||bounds[0]*factor>view.left+600||bounds[3]*factor<view.top||bounds[1]*factor>view.top+650||Math.max(...mile)<=lo||Math.min(...mile)>=hi)continue;const coords=row[3];
   for(let i=2;i<coords.length;i+=2){const a=mile[0]+(mile[1]-mile[0])*info.lengths[i/2-1]/info.total,b=mile[0]+(mile[1]-mile[0])*info.lengths[i/2]/info.total;if(a===b)continue;const start=Math.max(lo,Math.min(a,b)),end=Math.min(hi,Math.max(a,b));if(end<=start)continue;const fractions=[(start-a)/(b-a),(end-a)/(b-a)],points=fractions.map(f=>[(coords[i-2]+(coords[i]-coords[i-2])*f)*factor-view.left,(coords[i-1]+(coords[i+1]-coords[i-1])*f)*factor-view.top]);groups[kind]+='M'+points[0].map(v=>v.toFixed(2)).join(' ')+'L'+points[1].map(v=>v.toFixed(2)).join(' ');}
  }
 }return groups;
}
function draw(svg,make,data,items,view,revision,now){const palette={learning:'#1565c0',qualified:'#16803a',expired:'#c62828'};for(const [kind,d]of Object.entries(paths(data,items,view,revision,now))){if(!d)continue;const path=make('path');for(const [k,v]of Object.entries({d,fill:'none',stroke:palette[kind],'stroke-width':'5','stroke-dasharray':'10 4','data-imported-knowledge':kind}))path.setAttribute(k,v);svg.append(path);}}
window.RouteImports={paths,draw,state};
})();
