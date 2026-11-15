const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
const seedSource=fs.readFileSync('backend/lokzeitleiste/static/station-catalog-data.js','utf8'),source=fs.readFileSync('backend/lokzeitleiste/static/station-catalog.js','utf8');
function runtime(storage=new Map(),broken=false){
 let network=0;const events={},navigator={onLine:false},window={addEventListener:(type,fn)=>events[type]=fn,dispatchEvent:event=>events[event.type]?.()};
 const database={createObjectStore(){},transaction(){const tx={};tx.objectStore=()=>({get(key){const request={result:structuredClone(storage.get(key))};queueMicrotask(()=>tx.oncomplete());return request;},put(value,key){storage.set(key,structuredClone(value));queueMicrotask(()=>tx.oncomplete());return {};}});return tx;}};
 const context={window,navigator,Event,AbortController,setTimeout,clearTimeout,indexedDB:{open(){if(broken)throw Error('Storage disabled');const request={result:database};queueMicrotask(()=>request.onsuccess());return request;}},fetch:async(...args)=>{network++;return context.remote(...args);}};
 context.remote=()=>{throw Error('No offline network request allowed');};vm.runInNewContext(seedSource,context);vm.runInNewContext(source,context);return{context,storage,catalog:window.StationCatalog,get network(){return network;}};
}
(async()=>{
 const r=runtime();await r.catalog.ready;assert.equal(r.catalog.count,14886);assert.equal(r.catalog.coordinateCount,6450);assert.equal(r.network,0,'Cold offline start needs no server');assert(r.catalog.sameCode('AA  G','AA G'),'Repeated internal spaces normalize');assert(!r.catalog.sameCode('AA G','AAG'),'Meaningful spaces remain distinct');
 assert.equal((await r.catalog.search('AAG'))[0].name,'Ascheberg (Holst)');assert.equal((await r.catalog.search('AA G'))[0].name,'Hamburg-Altona Gbf','Spaces in codes retain meaning');
 const point=r.context.window.StationCatalogSeed.stations.find(row=>row[0]==='AABG');assert.equal((await r.catalog.nearest(point[2],point[3])).station.code,'AABG');assert.equal(r.network,0);
 let favoriteCalls=0;r.context.navigator.onLine=true;r.context.remote=async()=>({ok:true,json:async()=>({reference_revision:r.context.window.StationCatalogSeed.revision,stations:[['TEST','Eigener Serverbahnhof',52,13],['NEAR','Nachbar',52,13.0001],['TEXT','Ohne Koordinaten']]})});
 const currentRemote=r.context.remote;r.context.remote=async()=>({ok:true,json:async()=>({stations:[['OLD','Veralteter Server']]})});assert.equal(await r.catalog.refresh(true),false);assert.equal(r.catalog.count,14886,'An older server cannot downgrade the new APK catalogue');r.context.remote=currentRemote;
 assert(await r.catalog.refresh(true));assert.equal(r.catalog.count,3,'Complete server snapshot replaces bundled baseline');assert.equal((await r.catalog.nearest(52,13)).ambiguous,true);
 const choices=await r.catalog.frequent(async()=>{favoriteCalls++;return Array.from({length:7},(_,i)=>({code:'F'+i,name:'Ort '+i}));},7);assert.equal(choices.length,5);assert.equal(favoriteCalls,1);
 r.context.navigator.onLine=false;assert.equal((await r.catalog.search('TEST',()=>{throw Error('Offline remote call');}))[0].name,'Eigener Serverbahnhof');
 const restart=runtime(r.storage);await restart.catalog.ready;assert.equal(restart.catalog.count,3,'Server catalogue survives offline restart');assert.equal(restart.catalog.coordinateCount,2);
 assert.equal((await restart.catalog.search('TEXT'))[0].name,'Ohne Koordinaten','Stations without coordinates remain searchable');
 const cached=await restart.catalog.frequent(()=>{throw Error('No offline favorites request');},7);assert.equal(cached.length,5);assert.equal((await restart.catalog.frequent(()=>[],8)).length,0,'Other TF cannot read previous TF favorites');assert.equal(restart.network,0);
 assert.equal((await restart.catalog.nearest(NaN,13)).station,null);assert.equal((await restart.catalog.nearest(53,13)).station,null);
 const privateMode=runtime(new Map(),true);await privateMode.catalog.ready;assert.equal(privateMode.catalog.count,14886,'Bundled fallback also works with disabled browser storage');
 console.log('Offline DS100: full cold-start catalogue, 6450 coordinates, distinct spaced codes, local nearest lookup, persisted server refresh, station search and user-isolated favorites passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
