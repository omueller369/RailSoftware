/* Public graph worker: no account, credentials or qualification data. */
function PolandStkWorker(){
 let graph,adj,points,byNode,revision;
 const normalize=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[łŁ]/g,'l').toLowerCase();
 function value(row){const p={...row};if(p.node!==null){const n=graph.nodes[p.node];p.anchor={lon:n[0]/graph.scale,lat:n[1]/graph.scale};}return p;}
 function init(buffer){graph=JSON.parse(new TextDecoder().decode(buffer));if(graph.schema!==1||graph.scale!==10000000)throw Error('invalid');revision=graph.revision;adj=Array.from({length:graph.nodes.length},()=>[]);for(let i=0;i<graph.edges.length;i++){const [a,b,d]=graph.edges[i];adj[a].push([b,i,d]);adj[b].push([a,i,d]);}points=new Map();byNode=new Map();
 for(const p of graph.stations){const row={id:p[0],name:p[1],kind:p[2],lon:p[3]/graph.scale,lat:p[4]/graph.scale,node:p[5],distance_m:p[6]/10,junction:p[7]};points.set(row.id,row);if(row.node!==null&&!byNode.has(row.node))byNode.set(row.node,row.id);}
 for(const [id,kind,node]of graph.junctions){const n=graph.nodes[node],row={id,name:'',kind,lon:n[0]/graph.scale,lat:n[1]/graph.scale,node,distance_m:0,junction:kind===2};points.set(id,row);if(!byNode.has(node))byNode.set(node,id);}delete graph.stations;delete graph.junctions;return {revision,counts:graph.counts};}
 function distance(a,b){const p=graph.nodes[a],q=graph.nodes[b],lat=(p[1]+q[1])/2/graph.scale*Math.PI/180;return Math.hypot((p[0]-q[0])/graph.scale*111195*Math.cos(lat),(p[1]-q[1])/graph.scale*111195);}
 function shortest(start,end,banned=new Set(),limit=Infinity){const costs=new Float64Array(adj.length);costs.fill(Infinity);const previous=new Int32Array(adj.length),via=new Int32Array(adj.length);previous.fill(-1);via.fill(-1);const heap=[];
 const push=item=>{heap.push(item);let i=heap.length-1;while(i){const parent=(i-1)>>1;if(heap[parent][0]<=item[0])break;heap[i]=heap[parent];i=parent;}heap[i]=item;};
 const pop=()=>{const top=heap[0],last=heap.pop();if(heap.length){let i=0;while(true){let child=i*2+1;if(child>=heap.length)break;if(child+1<heap.length&&heap[child+1][0]<heap[child][0])child++;if(heap[child][0]>=last[0])break;heap[i]=heap[child];i=child;}heap[i]=last;}return top;};costs[start]=0;push([distance(start,end)*0.95,start,0]);let visited=0;
 while(heap.length){const [estimate,node,cost]=pop();if(cost!==costs[node])continue;if(node===end){const edges=[],forward=[],nodes=[end];let n=end;while(n!==start){const e=via[n],p=previous[n];if(e<0)return null;edges.push(e);forward.push(graph.edges[e][0]===p);nodes.push(p);n=p;}edges.reverse();forward.reverse();nodes.reverse();if(edges.length>5000)return null;return {edges,forward,nodes,length:cost};}if(++visited>200000)return null;for(const [next,e,d]of adj[node]){if(banned.has(e))continue;const candidate=cost+d;if(candidate>=costs[next]||candidate>limit)continue;costs[next]=candidate;previous[next]=node;via[next]=e;push([candidate+distance(next,end)*0.95,next,candidate]);}}
 return null;}
 function paths(from,to){const a=points.get(from),b=points.get(to);if(!a||!b)throw Error('invalid');if(a.node===null||b.node===null)throw Error('unlinked');if(a.node===b.node)throw Error('same_position');const first=shortest(a.node,b.node);if(!first)throw Error('not_connected');const results=[first],signatures=new Set([first.edges.join(',')]);const candidates=first.edges.filter(e=>adj[graph.edges[e][0]].length>2||adj[graph.edges[e][1]].length>2),sample=[];for(let i=0;i<Math.min(candidates.length,12);i++)sample.push(candidates[Math.floor(i*candidates.length/Math.min(candidates.length,12))]);
 for(const edge of sample){const result=shortest(a.node,b.node,new Set([edge]),first.length*1.6+2000);if(result&&!signatures.has(result.edges.join(','))){signatures.add(result.edges.join(','));results.push(result);}if(results.length>=3)break;}
 results.sort((a,b)=>a.length-b.length);return results.map(result=>({...result,via:[...new Set(result.nodes.map(n=>points.get(byNode.get(n))).filter(p=>p?.name&&p.id!==from&&p.id!==to).map(p=>p.name))].slice(0,3)}));}
 function inspect(waypoints,legs){return legs.map((choices,i)=>{const a=points.get(waypoints[i]),b=points.get(waypoints[i+1]);if(!a||!b||a.node===null||b.node===null)throw Error('invalid');return choices.map(edges=>{let node=a.node,length=0;const forward=[],nodes=[node];for(const id of edges){const edge=graph.edges[id];if(!edge)throw Error('invalid');if(edge[0]===node){node=edge[1];forward.push(true);}else if(edge[1]===node){node=edge[0];forward.push(false);}else throw Error('not_connected');length+=edge[2];nodes.push(node);}if(node!==b.node)throw Error('not_connected');return {edges,forward,nodes,length,via:[]};});});}
 self.onmessage=event=>{const {id,type,...args}=event.data;try{let result;
 if(type==='init')result=init(args.buffer);
 else if(type==='search'){const q=normalize(args.query);result=[...points.values()].filter(p=>p.kind<2&&(normalize(p.name).includes(q)||normalize(p.id).includes(q))||q.startsWith('pl:')&&normalize(p.id).startsWith(q)).sort((a,b)=>a.kind-b.kind||a.name.localeCompare(b.name,'pl')||a.id.localeCompare(b.id)).slice(0,30).map(value);}
 else if(type==='point')result=points.has(args.point)?value(points.get(args.point)):null;
 else if(type==='points')result=args.ids.map(p=>points.has(p)?value(points.get(p)):null);
 else if(type==='options')result=paths(args.from,args.to);
 else if(type==='inspect')result=inspect(args.waypoints,args.legs);
 else if(type==='neighbors'){const p=points.get(args.point);result=p?.node!==null&&p?[...new Map(adj[p.node].map(([node,e,length])=>[byNode.get(node),{point:value(points.get(byNode.get(node))),edges:[e],forward:[graph.edges[e][0]===p.node],length}])).values()]:[];}
 else throw Error('invalid');self.postMessage({id,ok:true,result});
 }catch(error){self.postMessage({id,ok:false,error:error.message||'invalid'});}};
}
window.PolandStkWorker=PolandStkWorker;
