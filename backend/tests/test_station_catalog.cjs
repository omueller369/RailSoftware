/* Regressionstests für Betriebsstellen und Ortszuordnungen. */
const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
const seedSource=fs.readFileSync('backend/lokzeitleiste/static/station-catalog-data.js','utf8'),source=fs.readFileSync('backend/lokzeitleiste/static/station-catalog.js','utf8');
function runtime(storage=new Map(),broken=false){
 let network=0;const events={},navigator={onLine:false},window={addEventListener:(type,fn)=>events[type]=fn,dispatchEvent:event=>events[event.type]?.()};
 const database={createObjectStore(){},transaction(){const tx={};tx.objectStore=()=>({get(key){const request={result:structuredClone(storage.get(key))};queueMicrotask(()=>{request.onsuccess?.();queueMicrotask(()=>tx.oncomplete?.());});return request;},put(value,key){storage.set(key,structuredClone(value));queueMicrotask(()=>tx.oncomplete());return {};}});return tx;}};
 const context={window,navigator,Event,AbortController,setTimeout,clearTimeout,setInterval:()=>0,indexedDB:{open(){if(broken)throw Error('Storage disabled');const request={result:database};queueMicrotask(()=>request.onsuccess());return request;}},fetch:async(...args)=>{network++;return context.remote(...args);}};
 context.remote=()=>{throw Error('No offline network request allowed');};vm.runInNewContext(seedSource,context);vm.runInNewContext(source,context);return{context,storage,catalog:window.StationCatalog,get network(){return network;}};
}
(async()=>{
 const r=runtime();await r.catalog.ready;assert.equal(r.catalog.count,14928);assert.equal(r.catalog.coordinateCount,6486);assert.equal(r.network,0,'Cold offline start needs no server');assert(r.catalog.sameCode('AA  G','AA G'),'Repeated internal spaces normalize');assert(!r.catalog.sameCode('AA G','AAG'),'Meaningful spaces remain distinct');
 assert.equal((await r.catalog.search('AAG'))[0].name,'Ascheberg (Holst)');assert.equal((await r.catalog.search('AA G'))[0].name,'Hamburg-Altona Gbf','Spaces in codes retain meaning');
 const point=r.context.window.StationCatalogSeed.stations.find(row=>row[0]==='AABG');assert.equal((await r.catalog.nearest(point[2],point[3])).station.code,'AABG');assert.equal(r.network,0);
 let favoriteCalls=0;r.context.navigator.onLine=true;r.context.remote=async()=>({ok:true,json:async()=>({reference_revision:r.context.window.StationCatalogSeed.revision,stations:[['TEST','Eigener Serverbahnhof',52,13],['NEAR','Nachbar',52,13.0001],['TEXT','Ohne Koordinaten']]})});
 const currentRemote=r.context.remote;r.context.remote=async()=>({ok:true,json:async()=>({stations:[['OLD','Veralteter Server']]})});assert.equal(await r.catalog.refresh(true),false);assert.equal(r.catalog.count,14928,'An older server cannot downgrade the new APK catalogue');r.context.remote=currentRemote;
 assert(await r.catalog.refresh(true));assert.equal(r.catalog.count,3,'Complete server snapshot replaces bundled baseline');assert.equal((await r.catalog.nearest(52,13)).ambiguous,true);
 const choices=await r.catalog.frequent(async()=>{favoriteCalls++;return Array.from({length:7},(_,i)=>({code:'F'+i,name:'Ort '+i}));},7);assert.equal(choices.length,5);assert.equal(favoriteCalls,1);
 r.context.navigator.onLine=false;assert.equal((await r.catalog.search('TEST',()=>{throw Error('Offline remote call');}))[0].name,'Eigener Serverbahnhof');
 const restart=runtime(r.storage);await restart.catalog.ready;assert.equal(restart.catalog.count,3,'Server catalogue survives offline restart');assert.equal(restart.catalog.coordinateCount,2);
 assert.equal((await restart.catalog.search('TEXT'))[0].name,'Ohne Koordinaten','Stations without coordinates remain searchable');
 const cached=await restart.catalog.frequent(()=>{throw Error('No offline favorites request');},7);assert.equal(cached.length,5);assert.equal((await restart.catalog.frequent(()=>[],8)).length,0,'Other TF cannot read previous TF favorites');assert.equal(restart.network,0);
 assert.equal((await restart.catalog.nearest(NaN,13)).station,null);assert.equal((await restart.catalog.nearest(53,13)).station,null);
 const privateMode=runtime(new Map(),true);await privateMode.catalog.ready;assert.equal(privateMode.catalog.count,14928,'Bundled fallback also works with disabled browser storage');
 const proposal={id:'00000000-0000-4000-8000-000000000001',owner_id:7,code:'TEXT',name:'Ohne Koordinaten',latitude:52.3,longitude:13.3,accuracy_m:5,observed_at:1794744000000};
 await restart.catalog.stageProposal(proposal);assert.equal((await restart.catalog.getStation('TEXT',7)).coordinate.latitude,52.3);assert.equal((await restart.catalog.getStation('TEXT',8)).coordinate,null,'Pending point is private to its TF');
 const cold=runtime(r.storage);await cold.catalog.ready;assert.equal((await cold.catalog.getStation('TEXT',7)).coordinate.latitude,52.3,'Private point survives offline restart');assert.equal((await cold.catalog.pending(8)).length,0);
 assert.equal(r.storage.get('snapshot').stations.find(row=>row[0]==='TEXT').length,2,'Unconfirmed point never enters the public snapshot');
 await cold.catalog.acceptServerPoint({code:'TEXT',name:'Ohne Koordinaten',coordinate:{latitude:53,longitude:14}});await cold.catalog.removeProposal(7,proposal.id);assert.equal((await cold.catalog.pending(7,true)).length,0);assert.equal((await cold.catalog.getStation('TEXT',8)).coordinate.latitude,53,'Accepted global point is shared locally');
 await assert.rejects(privateMode.catalog.stageProposal(proposal),'A failed durable save cannot claim to have queued the edit');
 cold.context.navigator.onLine=true;let release;const oldRows=cold.storage.get('snapshot').stations;cold.context.remote=()=>new Promise(resolve=>release=resolve);const refresh=cold.catalog.refresh(true);await new Promise(setImmediate);
 await cold.catalog.acceptServerPoint({code:'TEXT',name:'Ohne Koordinaten',coordinate:{latitude:54,longitude:15}});release({ok:true,json:async()=>({reference_revision:cold.context.window.StationCatalogSeed.revision,stations:oldRows})});assert.equal(await refresh,false);assert.equal((await cold.catalog.getStation('TEXT',8)).coordinate.latitude,54,'Late full snapshot cannot undo a newly accepted coordinate');
 const afterRace=runtime(cold.storage);await afterRace.catalog.ready;assert.equal((await afterRace.catalog.getStation('TEXT',8)).coordinate.latitude,54,'Accepted point survives stale snapshot and restart');
 console.log('Offline DS100: full cold-start catalogue, 6486 coordinates, distinct spaced codes, local nearest lookup, persisted server refresh, station search and user-isolated favorites passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
