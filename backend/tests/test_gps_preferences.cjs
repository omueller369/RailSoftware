/* Regressionstests für GPS-Erfassung und Kartendarstellung. */
const fs=require('fs'),vm=require('./localized-vm.cjs'),assert=require('assert');
const context={window:{addEventListener(){}}};
vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/gps.js','utf8'),context);
const live=context.window.GpsRecorder.liveStops,base=1794744000000;
for(const minutes of [1,2,4,5,10,15]){
 const points=Array.from({length:minutes*12+1},(_,i)=>({t:base+i*5000,lat:52,lon:13,accuracy:5,speed:0}));
 const totals={moving:0,stopped:0,intervals:[]};
 assert.equal(live(points.slice(0,-1),false,{},false,false,false,false,null,totals,minutes).length,0);
 assert.equal(totals.stopped,0,'Short stand not counted before selected threshold');
 const full={moving:0,stopped:0,intervals:[]};
 assert.equal(live(points,false,{},false,false,false,false,null,full,minutes).length,1);
 assert.equal(full.stopped,minutes*60000,'Threshold registers entire stand duration');
}
assert.equal(live([{t:base,lat:52,lon:13,accuracy:5,speed:0},{t:base+120000,lat:52,lon:13,accuracy:5,speed:0}],false,{},false,false,false,false,null,null,1).length,0);
console.log('GPS preferences: all six inclusive thresholds, short-stand exclusion and GPS-gap exclusion: PASS');
