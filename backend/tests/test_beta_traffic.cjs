/* Regressionstests für Anzeige des Datenverbrauchs im Betatest. */
const fs=require('fs'),vm=require('./localized-vm.cjs'),assert=require('assert');
const values=new Map(),source=fs.readFileSync('backend/lokzeitleiste/static/beta-traffic.js','utf8');
let offline=false;const window={addEventListener(){},fetch:async()=>new Response('abc',{headers:offline?{'X-LokZeitleiste-Offline':'1'}:{}})};
window.parent=window;
const sessionStorage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)};
vm.runInNewContext(source,{window,sessionStorage,location:{origin:'https://testserver'},document:{readyState:'loading',addEventListener(){}},TextEncoder,Blob,ArrayBuffer,URLSearchParams,FormData,console});
const totals=()=>JSON.parse(values.get('rail.beta.traffic'));
(async()=>{
 await window.fetch('/api/test',{method:'POST',body:'ä'});await new Promise(resolve=>setTimeout(resolve,10));
 assert.deepEqual(totals(),{upload:2,download:3},'UTF-8 payload sizes');
 const body=new FormData();body.set('file',new Blob(['12345']),'test.xlsx');
 await window.fetch('/api/import',{method:'POST',body});await new Promise(resolve=>setTimeout(resolve,10));
 assert.deepEqual(totals(),{upload:11,download:6},'Multipart file payload plus key');
 offline=true;await window.fetch('/api/cached',{body:'ignored'});await new Promise(resolve=>setTimeout(resolve,10));
 assert.deepEqual(totals(),{upload:11,download:6},'Offline cache is not counted as a network transfer');
 const child={parent:{location:{origin:'https://testserver'},CtlTraffic:window.CtlTraffic},addEventListener(){},fetch:async()=>new Response('x')};
 vm.runInNewContext(source,{window:child,sessionStorage,location:{origin:'https://testserver'},TextEncoder,Blob,ArrayBuffer,URLSearchParams,FormData,console});
 await child.fetch('/api/overlay',{body:'yy'});await new Promise(resolve=>setTimeout(resolve,10));assert.deepEqual(totals(),{upload:13,download:7},'Iframe transfers contribute once to parent counter');
 console.log('Beta traffic: UTF-8, multipart file sizes, offline exclusion and iframe aggregation passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
