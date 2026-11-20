const fs=require('fs'),vm=require('./localized-vm.cjs'),assert=require('assert');
const context={window:{},console};vm.createContext(context);
for(const name of ['station-catalog-data.js','rail-network-data.js','rail-network.js','m1-map.js'])vm.runInContext(fs.readFileSync('backend/lokzeitleiste/static/'+name,'utf8'),context);
const m=context.window.M1Map,data=context.window.RailNetworkSeed;
for(const [a,b,expected] of [['ALD','ALD A',true],['ABLZ','AHAR',false]]){const options=m.candidates(a,b,data);assert(options.length>=2);assert.equal(m.parallel(options,data),expected,a+' → '+b);}
// Same end points do not make a detour parallel; real reference above covers this too.
const p=(code,route,km,x,y)=>({code,route,km:km+' + 0',lat:51+y/100,lon:10+x/100,name:code});
const points=[p('A','1',0,0,0),p('B','1',1,1,0),p('C','1',2,2,0),p('B','2',0,1,0),p('D','2',1,1,1)];
context.window.StationCatalogSeed={operating_points:points};const fake={routes:[['1'],['2']],lines:[[0,0,[],[],[],[0,2000]],[1,0,[],[],[],[0,1000]]]};
assert(m.isJunction('B',fake));assert(!m.isJunction('A',fake));assert(!m.isJunction('C',fake));
assert.deepEqual(Array.from(m.suggestions('A',fake,{nodesOnly:true}),r=>r.code),['B']);
assert.deepEqual(Array.from(m.suggestions('B',fake,{selected:['A','B']}),r=>r.code).sort(),['C','D']);
assert.equal(m.suggestions('B',fake,{nodesOnly:true,selected:['A','B']}).length,0,'Filter does not invent a next junction beyond the data');
console.log('M1 navigation: connected junctions, suggestions, backtracking exclusion and real parallel/divergent sections passed.');
