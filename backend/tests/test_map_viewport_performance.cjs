/* Der Ausschnitt darf weder den ganzen Katalog erneut durchsuchen noch unsichtbare Koordinaten ausgeben. */
const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict'),{performance}=require('node:perf_hooks');
const window={},context={window,console};for(const file of ['rail-network-data.js','rail-network.js','station-catalog-data.js','m1-map.js'])vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/'+file,'utf8'),context);
const seed=window.RailNetworkSeed,api=window.RailNetwork;let reads=0;const data={...seed,lines:new Proxy(seed.lines,{get(rows,key){if(/^\d+$/.test(String(key)))reads++;return Reflect.get(rows,key);}})};
const size=256*2**13,p=window.M1Map.project({lat:52.52,lon:13.4}),view={zoom:13,size,left:p.x*size-300,top:p.y*size-325,width:600,height:650};
const before=JSON.stringify(seed);api.paths(data,view);reads=0;const start=performance.now(),shifted={...view,left:view.left+90};const path=api.paths(data,shifted),pan=performance.now()-start;
assert(path.visible>0,'The fixture includes actual visible railway lines');assert(reads<seed.lines.length/10,'A warm pan queries nearby indexed lines instead of the full network: '+reads);
for(const d of path.paths)for(const point of d.matchAll(/[ML](-?[\d.]+) (-?[\d.]+)/g)){assert(Number(point[1])>=-8.1&&Number(point[1])<=608.1);assert(Number(point[2])>=-8.1&&Number(point[2])<=658.1);}
reads=0;assert.equal(api.paths(data,shifted),path,'Identical views reuse prepared paths');assert.equal(reads,0,'A repeated view does not inspect reference geometry');
assert.notEqual(api.paths(data,{...shifted,width:300}),path,'Resizing invalidates the view cache');
const refs=window.M1Map.points(),points=window.M1Map.visiblePoints(view);assert(points.length<refs.projected.length/10);assert(points.every(p=>p.x*size>=view.left&&p.x*size<=view.left+600&&p.y*size>=view.top&&p.y*size<=view.top+650));assert.equal(JSON.stringify(seed),before,'Public geometry stays unchanged');
console.log('Full M1 viewport: '+path.visible+' visible lines, warm pan '+pan.toFixed(1)+' ms, spatial points and bounded SVG coordinates: PASS');
