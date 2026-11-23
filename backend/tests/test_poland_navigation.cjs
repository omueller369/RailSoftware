/* Prüft den öffentlichen polnischen Graphen ohne Konto und ohne persönliche GPS-Aufzeichnungen. */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const graph={schema:1,scale:10000000,revision:'a'.repeat(64),counts:{},nodes:[[130000000,520000000],[130010000,520000000],[130020000,520000000],[130030000,520000000],[130020000,520010000],[150000000,530000000]],edges:[[0,1,100],[1,2,100],[2,3,100],[2,4,100]],stations:[['PL:N1','Łódź Fabryczna',0,130000000,520000000,0,0,false],['PL:N2','Warszawa Główna',0,130010000,520000000,1,0,false]],junctions:[['PL:J1',2,2],['PL:J2',3,3],['PL:J3',3,4],['PL:J4',3,5]]};
let reply;const self={postMessage:value=>reply=value},window={};vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/poland-stk-worker.js','utf8'),{window,self,TextDecoder});window.PolandStkWorker();let serial=0;function send(type,args={}){reply=null;self.onmessage({data:{id:++serial,type,...args}});return JSON.parse(JSON.stringify(reply));}
assert(send('init',{buffer:new TextEncoder().encode(JSON.stringify(graph)).buffer}).ok);
const names=send('search',{query:'lodz'});assert.equal(names.result[0].id,'PL:N1','Polnische Sonderzeichen sind für die Suche nicht erforderlich');
const ordinary=send('hints',{point:'PL:N1',nodesOnly:false});assert.equal(ordinary.result[0].point.id,'PL:N2');
const nodes=send('hints',{point:'PL:N1',nodesOnly:true});assert.equal(nodes.result[0].point.id,'PL:J1');assert.deepEqual(nodes.result[0].edges,[0,1],'Knotensuche behält alle übersprungenen Gleisabschnitte');
const branches=send('hints',{point:'PL:J1',previous:'PL:N2',nodesOnly:true});assert.deepEqual(branches.result.map(p=>p.point.id).sort(),['PL:J2','PL:J3']);
const path=send('options',{from:'PL:N1',to:'PL:J3'});assert.deepEqual(path.result[0].edges,[0,1,3]);assert.equal(send('options',{from:'PL:N1',to:'PL:J4'}).error,'not_connected');
const first=[130000000,520000000,130100000,520000000],near=[130000000,520000000,130050000,520005000,130100000,520000000],detour=[130000000,520000000,130050000,520100000,130100000,520000000];
assert.equal(send('parallel',{lines:[[first],[near]]}).result,true);assert.equal(send('parallel',{lines:[[first],[detour]]}).result,false,'Gleiche Endpunkte reichen für parallele Verläufe nicht aus');
assert.equal(send('inspect',{waypoints:['PL:N1','PL:J2'],legs:[[[0,2]]]}).error,'not_connected');
assert.equal(graph.stations.length,2,'Die Quelle bleibt unverändert');console.log('Polnische Suche, Knotenvorschläge, echte Verbindungen und Parallelprüfung: PASS');
