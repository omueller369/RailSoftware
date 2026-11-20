"""Regression: STK editing stays responsive while real GPS history is matched in a worker."""
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from check_manual_route_ui import ASSETS as BASE
ASSETS=['map-gestures.js',*BASE]
def fixture():
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css','portal-theme.css'])
    setup="""window.I18n={t:s=>s};window.AndroidPortal={};Object.defineProperty(navigator,'onLine',{get:()=>false});window.fetch=async()=>new Response(JSON.stringify({owner_id:1,items:[],next_offset:null}),{headers:{'Content-Type':'application/json'}});"""
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},wait=ms=>new Promise(r=>setTimeout(r,ms)),until=async condition=>{const end=performance.now()+45000;while(!condition()){if(performance.now()>end)throw Error('Timed out');await wait(20);}};
 const line=RailNetworkSeed.lines.find(row=>row[5]&&row[3].length>100),points=[];
 for(let repeat=0;repeat<120;repeat++)for(let i=0;i<line[3].length;i+=2){const x=line[3][i]/RailNetworkSeed.scale,y=line[3][i+1]/RailNetworkSeed.scale;points.push({lon:x*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y)))*180/Math.PI,t:1795165200000+points.length*1000,accuracy:5});}
 const original=JSON.stringify(points);window.GpsRecorder={localRecords:async()=>[{journey_id:'large-history',points}]};let mainCalculations=0,jobs=0,lastResult;const costs={};for(const [label,obj,key]of [['m1',M1Map,'draw'],['hints',M1Map,'suggestions'],['rail',RailNetwork,'draw'],['gps',RouteCoverage,'gps'],['ref',RouteCoverage,'reference']]){const fn=obj[key];obj[key]=(...args)=>{const at=performance.now();try{return fn(...args);}finally{costs[label]=Math.max(costs[label]||0,performance.now()-at);}};}
 const sync=RouteCoverage.calculate,create=RouteCoverage.createAsync;RouteCoverage.calculate=()=>{mainCalculations++;throw Error('Main-thread GPS matching forbidden');};RouteCoverage.createAsync=(...args)=>{jobs++;const job=create(...args);job.promise.then(result=>lastResult=result);return job;};
 const imported={status:'streckenkundig',valid_until:'2027-12-31',map_match:M1Map.candidates('AFW','AFR',RailNetworkSeed)[0]};window.RouteCsv={mount:(user,host,callback)=>{setTimeout(()=>callback({items:[imported]}),0);return Promise.resolve();}};
 let editor;const mount=ManualRouteEditor.mount;ManualRouteEditor.mount=(...args)=>(editor=mount(...args));let ticks=0,maxGap=0,last=performance.now();const timer=setInterval(()=>{const now=performance.now();maxGap=Math.max(maxGap,now-last);last=now;ticks++;},25);
 await startRouteKnowledge({id:1});document.getElementById('routeTab-create').click();await until(()=>editor&&!document.querySelector('[data-route-start]').disabled);
 const before=ticks;await wait(300);assert(ticks-before>=4,'UI heartbeat continues while GPS history is processed');assert(jobs===1&&mainCalculations===0,'Exactly one background job and no synchronous GPS matching');
 editor.select(M1Map.points().byCode.get('AFW')[0],true);await wait(0);editor.select(M1Map.points().byCode.get('AFR')[0]);await wait(40);const root=document.getElementById('manualRouteWorkspace');for(const select of root.querySelectorAll('[data-route-waypoint] select'))if(!select.value){select.value='1000';select.dispatchEvent(new Event('change'));}await until(()=>root.querySelector('[data-manual-route-line]'));assert(root.querySelector('[data-manual-route-line]'),'STK route can be drawn while matching runs');root.querySelector('[data-route-map-undo]').click();assert(editor.waypoints.join(',')==='AFW','Undo stays usable');assert(root.querySelector('[data-imported-knowledge=qualified]'),'Confirmed imported knowledge remains visible');
 await until(()=>lastResult&&document.querySelector('[data-gps-coverage-status]').textContent==='');assert(lastResult.counts.size>0,'Actual long GPS history produced matched route bins');assert(JSON.stringify(points)===original,'The complete GPS source is unchanged');assert(mainCalculations===0&&jobs===1,'No render-triggered second matching job');
 await wait(80);clearInterval(timer);const observedGap=maxGap;console.log('RENDER COSTS',JSON.stringify(costs));
 // A small fixture verifies exact parity with the existing conservative calculation.
 const a=M1Map.points().byCode.get('AFW')[0],b=M1Map.points().byCode.get('AFR')[0],small=new Map([['small',[[[a.lat,a.lon,1795165200000],[b.lat,b.lon,1795165210000]]]]]),expected=sync(RailNetworkSeed,small),actual=await create(RailNetworkSeed,small).promise;
 assert(JSON.stringify([...actual.counts])===JSON.stringify([...expected.counts]),'Worker passage counts equal the proven synchronous engine');assert(JSON.stringify([...actual.latest])===JSON.stringify([...expected.latest]),'Worker retains exact last passage dates');
 const cancelled=create(RailNetworkSeed,small);cancelled.cancel();let aborted=false;try{await cancelled.promise;}catch(error){aborted=error.name==='AbortError';}assert(aborted,'Leaving the module can terminate analysis without retaining a worker');
 assert(observedGap<1500,'No multi-second UI stall during opening, drawing or result display: '+Math.round(observedGap)+'ms '+JSON.stringify(costs));document.body.dataset.recovery=JSON.stringify({points:points.length,ticks,maxGapMs:Math.round(observedGap),bins:lastResult.counts.size,costs});parent.postMessage({layoutStatus:'pass',message:document.body.dataset.recovery},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    html='<button id="routeTab-view">View</button><button id="routeTab-create">Create</button><section id="routePanel-view"><div id="routeKnowledgeWorkspace"></div></section><section id="routePanel-create" hidden><div id="manualRouteWorkspace"></div></section>'
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+html+'<script>'+setup+'</script>'+''.join('<script src="/tf/'+name+'"></script>' for name in ASSETS)+'<script>'+checks+'</script></body></html>'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,widths=(800,),assets={'/tf/'+name:STATIC/name for name in ASSETS},label='Android STK responsiveness with real GPS history',cpu_rate=4,timeout=65)
