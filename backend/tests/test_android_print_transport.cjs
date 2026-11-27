/* Große Druckaufträge passieren die native Grenze in kleinen Paketen und bleiben bytegleich. */
const fs=require('fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
const messages=[],chunks=[];let kind,finished,failChunk=false,loseBegin=false;
const native={postMessage(raw){assert(raw.length<150000,'Every bridge message fits the native limit');const r=JSON.parse(raw);messages.push(r);if(r.method==='print.begin'&&loseBegin)return;let value={},ok=true;
if(r.method==='session')value={account:{id:7},profile:{id:7},app_version:'test'};
if(r.method==='print.begin'){chunks.length=0;kind=r.kind;value={print_id:r.print_id};}
if(r.method==='print.chunk'){if(failChunk)ok=false;else chunks.push(Buffer.from(r.data,'base64'));}
if(r.method==='print.commit')finished={kind,bytes:Buffer.concat(chunks)};
queueMicrotask(()=>native.onmessage({data:JSON.stringify({id:r.id,ok,value,error:'Test failure'})}));}};
class Reader{readAsDataURL(blob){blob.arrayBuffer().then(bytes=>{this.result='data:application/octet-stream;base64,'+Buffer.from(bytes).toString('base64');this.onload();});}}
const window={NativePortal:native,fetch:async()=>new Response('{}'),addEventListener(){}};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/android-portal.js','utf8'),{window,NativePortal:native,sessionStorage:{setItem(){},removeItem(){}},URL,location:{href:'https://testserver/tf',origin:'https://testserver'},Response,Blob,Uint8Array,FileReader:Reader,atob:s=>Buffer.from(s,'base64').toString('binary'),setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,100)),clearTimeout,console});
(async()=>{
const bytes=Buffer.concat([Buffer.from('%PDF-1.4\n'),Buffer.alloc(250000,65)]);
await window.AndroidPortal.printReportPdf({title:'Mehrseitiger Bericht',pdf:bytes.toString('base64')});assert.deepEqual(finished.bytes,bytes);assert.equal(finished.kind,'pdf');assert(messages.filter(r=>r.method==='print.chunk').length>1);
const layout={title:'Lokaler Bericht',text:'Łódź '.repeat(40000),layout:{lines:[['Pflichtfeld','—']]}};
await window.AndroidPortal.printReport(layout);assert.equal(finished.kind,'layout');assert.deepEqual(JSON.parse(finished.bytes.toString('utf8')),layout);
failChunk=true;await assert.rejects(window.AndroidPortal.printReportPdf({title:'Fehler',pdf:bytes.toString('base64')}));assert.equal(messages.at(-1).method,'print.abort','A rejected packet releases the native print transfer');
failChunk=false;loseBegin=true;await assert.rejects(window.AndroidPortal.printReportPdf({title:'Keine Antwort',pdf:bytes.toString('base64')}),/timed out/,'A missing native reply cannot leave Print permanently disabled');assert.equal(messages.at(-1).method,'print.abort','Even a lost begin reply releases its known transfer id');
console.log('Android print transport: large PDFs, UTF-8 layouts, bounded packets, unchanged bytes, abort and missing-reply timeout: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
