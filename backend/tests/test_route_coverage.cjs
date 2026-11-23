/* Regressionstests für Streckenkenntnisse und Referenzgeometrie. */
const fs=require('fs'),vm=require('./localized-vm.cjs'),assert=require('assert');const window={};vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/route-coverage.js','utf8'),{window,console});
const C=window.RouteCoverage,S=1e8,project=([lat,lon])=>[(lon+180)/360*S,(1-Math.asinh(Math.tan(lat*Math.PI/180))/Math.PI)/2*S],a=[52,13],b=[52,13.02],p=project(a),q=project(b),line=[...p,...q],box=[Math.min(p[0],q[0]),Math.min(p[1],q[1]),Math.max(p[0],q[0]),Math.max(p[1],q[1])];
const data=()=>({schema:2,scale:S,routes:[['1234','Test']],lines:[[0,0,box,line,line,[0,1400]]]});
const forward=()=>[[a,b]],backward=()=>[[b,a]];const records=new Map([['one',forward()]]);let d=data(),cache=new Map(),r=C.calculate(d,records,cache);assert(r.counts.size>=13);assert([...r.counts.values()].every(n=>n[0]===1&&n[1]===0));assert([...r.counts.values()].every(n=>!C.qualified(n)));
records.set('two',forward());records.set('three',backward());r=C.calculate(d,records,cache);assert([...r.counts.values()].every(n=>n[0]===2&&n[1]===1&&!C.qualified(n)));
records.set('four',backward());r=C.calculate(d,records,cache);assert([...r.counts.values()].every(C.qualified),'Only 2 forward + 2 backward is green');
assert.strictEqual(cache.get('one').lines,records.get('one'));r=C.calculate(d,records,cache);assert([...r.counts.values()].every(n=>n[0]===2&&n[1]===2),'Reload and GPS point density do not add passages');
records.delete('four');r=C.calculate(d,records,cache);assert([...r.counts.values()].every(n=>!C.qualified(n)));assert(!cache.has('four'));
const repeated=new Map([['same-journey',[...forward(),...forward(),...backward(),...backward()]]]);r=C.calculate(d,repeated);assert([...r.counts.values()].every(n=>n[0]===1&&n[1]===1),'One journey gives at most one passage per direction');
const raw=JSON.stringify(repeated.get('same-journey'));C.calculate(d,repeated);assert.equal(JSON.stringify(repeated.get('same-journey')),raw,'GPS is never mutated');
const short=[[a,[52,13.0001]]];assert.equal(C.calculate(d,new Map([['short',short]])).counts.size,0,'Tiny partial movement cannot qualify a full 100m bin');
const dense=[Array.from({length:1401},(_,i)=>[52,13+.02*i/1400])];d=data();const sparse=C.calculate(d,new Map([['sparse',forward()]])),denseResult=C.calculate(d,new Map([['dense',dense]]));assert.equal(denseResult.counts.size,sparse.counts.size,'Slow, densely sampled motion must count like the same sparsely sampled path');assert([...denseResult.counts.values()].every(n=>n[0]===1&&n[1]===0));
// Zwei gleich nahe unterschiedliche Streckennummern dürfen nicht automatisch angerechnet werden.
d=data();d.routes.push(['5678','Other']);d.lines.push([1,0,box,line,line,[0,1400]]);assert.equal(C.calculate(d,new Map([['ambiguous',forward()]])).counts.size,0);
d=data();d.lines.push([0,0,box,line,line,[2000,3400]]);assert.equal(C.calculate(d,new Map([['same-route-ambiguous-mileage',forward()]])).counts.size,0,'Same route with ambiguous kilometre position remains blue');
// Parallele Gleise derselben Streckennummer werden nach Streckenkilometer zusammengefasst.
d=data();const parallelA=[52.00005,13],parallelB=[52.00005,13.02],pa=project(parallelA),pb=project(parallelB),parallel=[...pa,...pb];d.lines.push([0,0,[pa[0],pa[1],pb[0],pb[1]],parallel,parallel,[0,1400]]);const trips=new Map([['f1',forward()],['f2',forward()],['b1',[[parallelB,parallelA]]],['b2',[[parallelB,parallelA]]]]);r=C.calculate(d,trips);assert([...r.counts.values()].every(C.qualified),'Same route, other track, opposite direction counts together');
// Reference with disconnected/unknown mileage is visible but earns no invented credit.
d=data();d.lines[0][5]=null;assert.equal(C.calculate(d,new Map([['disconnected',forward()]])).counts.size,0);
console.log('Route coverage: partial bins, distinct journeys, both directions, parallel tracks, ambiguity, deletion/reload and immutable GPS passed.');
