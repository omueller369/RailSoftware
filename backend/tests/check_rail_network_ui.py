"""Real full M1 bundle offline; directional counts and layer visibility."""
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html


def fixture():
    scripts='\n'.join((STATIC/name).read_text() for name in ['messages.js','knowledge-inventory.js','route-imports.js','route-coverage.js','rail-network.js','route-knowledge.js'])
    checks=r'''
Object.defineProperty(navigator,'onLine',{value:false,configurable:true});
window.I18n={t:s=>s,locale:'de-DE'};const ageTimers=[];window.setInterval=(fn,ms)=>{if(ms===60000)ageTimers.push(fn);return 1;};
(async()=>{
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 const started=performance.now(),data=await window.RailNetwork.load();
 assert(data.source.source_rows===33425&&data.source.route_count===1549,'Actual supplied M1 dataset loaded');
 const reference=data.lines.find(row=>data.routes[row[0]][0]==='1000'&&row[5]&&Math.abs(row[5][1]-row[5][0])>1000);
 assert(reference,'Long real Flensburg reference line');
 const coords=reference[3],forward=[];for(let i=0;i<coords.length;i+=2)forward.push([Math.atan(Math.sinh(Math.PI*(1-2*coords[i+1]/data.scale)))*180/Math.PI,coords[i]/data.scale*360-180]);
 const make=(id,reverse,days=0)=>({journey_id:id,dirty:true,points:(reverse?[...forward].reverse():forward).map((p,i)=>({t:Date.now()-days*86400000-3600000+i*5000,lat:p[0],lon:p[1],accuracy:5}))});
 let emitImports;window.RouteCsv={mount:async(user,root,receive)=>{emitImports=receive;}};
 let rows=[make('forward-1'),make('forward-2'),make('backward-1',true),make('backward-2',true)];let localLoads=0;window.GpsRecorder={localRecords:async()=>{localLoads++;return rows;}};
 await window.startRouteKnowledge({id:7});
 assert(document.querySelectorAll('[data-rail-network]').length>0,'National reference geometry visible offline');
 assert(!document.querySelector('.route-knowledge-map image'),'Offline network does not request online map tiles');
 assert(document.querySelector('[data-route-track=qualified]'),'2 + 2 real-network journeys turn GPS green');
 assert(document.querySelector('[data-rail-coverage=qualified]'),'Matched reference bins also green');
 assert(document.querySelector('[data-route-track=qualified]').getAttribute('stroke')==='#16803a','Green stroke');
 assert(document.querySelector('[data-route-track=qualified]').getAttribute('stroke-width')==='6','GPS lines doubled from 3 to 6');assert(document.querySelector('[data-rail-coverage=qualified]').getAttribute('stroke-width')==='5','Coverage doubled from 2.5 to 5');assert(document.querySelector('[data-rail-network="0"]').getAttribute('stroke-width')==='2.7','Reference doubled from 1.35 to 2.7');assert(getComputedStyle(document.querySelector('.route-network-swatch.qualified')).borderTopWidth==='6px','Legend lines doubled too');
 assert(performance.now()-started<10000,'Full offline network remains responsive');
 const routesTab=document.getElementById('knowledgeTab-routes'),placesTab=document.getElementById('knowledgeTab-places'),classesTab=document.getElementById('knowledgeTab-classes'),panel=name=>document.getElementById('knowledgePanel-'+name),originalSvg=document.querySelector('.route-knowledge-map svg'),loadsBefore=localLoads;
 assert(document.querySelector('#routeKnowledge h1').textContent==='Stecken-, BR- und Ortskenntnisse','Requested module name');
 assert(routesTab.getAttribute('aria-selected')==='true'&&!panel('routes').hidden,'Route tab is initial selection');
 placesTab.click();assert(!panel('places').hidden&&panel('routes').hidden&&panel('classes').hidden,'Location placeholder only');assert(panel('places').querySelector('[data-knowledge-file]'),'Location CSV inventory available');
 classesTab.click();assert(!panel('classes').hidden&&panel('places').hidden,'Vehicle class placeholder only');assert(panel('classes').querySelector('[data-knowledge-file]'),'Rolling-stock CSV inventory available');
 classesTab.dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true}));assert(document.activeElement===routesTab&&!panel('routes').hidden,'Home activates first tab and restores focus');
 routesTab.dispatchEvent(new KeyboardEvent('keydown',{key:'End',bubbles:true}));assert(document.activeElement===classesTab,'End activates last tab');classesTab.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));assert(document.activeElement===routesTab,'Arrow wraps to first tab');
 assert(document.querySelector('.route-knowledge-map svg')===originalSvg&&localLoads===loadsBefore,'Tabs preserve the actual map and do not reload GPS or count again');

 const reload=document.querySelector('#routeKnowledgeWorkspace button');rows=rows.slice(0,3);await reload.onclick();
 assert(!document.querySelector('[data-route-track=qualified]'),'2 + 1 remains blue');
 assert(document.querySelector('[data-route-track=learning]'),'Blue GPS stroke retained');
 const toggle=document.querySelector('[data-network-toggle]');toggle.checked=false;toggle.dispatchEvent(new Event('change'));
 assert(!document.querySelector('[data-rail-network]'),'Reference checkbox hides network');assert(document.querySelector('[data-route-track=learning]'),'Own GPS remains when network hidden');
 toggle.checked=true;toggle.dispatchEvent(new Event('change'));assert(document.querySelector('[data-rail-network]'),'Toggle restores offline reference');assert(!document.querySelector('[data-route-track=qualified]'),'Toggling never creates a passage');
 rows=[];await reload.onclick();assert(!document.querySelector('[data-route-track]'),'Reference alone is never travelled');assert(document.querySelector('[data-rail-network]'),'Reference visible without any recording');
 rows=[make('forward-1'),make('forward-2'),make('backward-1',true),make('backward-2',true)];await reload.onclick();
 const realNow=Date.now,baseNow=realNow();Date.now=()=>baseNow+200*86400000;ageTimers[0]();assert(document.querySelector('[data-route-track=aging]'),'Open map updates age at calendar-day change without reloading');Date.now=realNow;ageTimers[0]();assert(document.querySelector('[data-route-track=qualified]'),'Restoring current calendar date restores recent green');
 // Age overrides passage counts; a recent journey in either direction refreshes matched bins.
 rows=[make('old-f1',false,200),make('old-f2',false,200),make('old-b1',true,200),make('old-b2',true,200)];await reload.onclick();
 assert(document.querySelector('[data-route-track=aging]')&&document.querySelector('[data-rail-coverage=aging]'),'Over 180 days orange on GPS and reference');assert(!document.querySelector('[data-route-track=qualified]'),'Orange overrides old green');
 rows=rows.map((row,i)=>make('expired-'+i,i>=2,400));await reload.onclick();assert(document.querySelector('[data-route-track=expired]')&&document.querySelector('[data-rail-coverage=expired]'),'Over 365 days red on GPS and reference');assert(!document.querySelector('[data-route-track=qualified]'),'Red overrides old green');
 await reload.onclick();assert(document.querySelector('[data-route-track=expired]'),'Reload never refreshes trip date');
 rows.push(make('recent-forward'));await reload.onclick();assert(document.querySelector('[data-route-track=qualified]'),'Recent ride in either direction refreshes known section');
 rows=[];await reload.onclick();assert([...document.querySelectorAll('[data-rail-network]')].every(path=>path.getAttribute('stroke')==='#000000'),'ALL untravelled network statuses are black');
 // Server timestamps take precedence over the compatible geometry-only response.
 const serverRows=[make('server-old-f1',false,400),make('server-old-f2',false,400),make('server-old-b1',true,400),make('server-old-b2',true,400)];let legacy=false,requests=[];
 window.RouteKnowledgeTileUrl='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1ioAAAAASUVORK5CYII=';
 Object.defineProperty(navigator,'onLine',{value:true,configurable:true});window.fetch=async url=>{requests.push(url);return {ok:true,json:async()=>({owner_id:7,items:serverRows.map(row=>({journey_id:row.journey_id,segments:[row.points.map(p=>[p.lat,p.lon])],...(legacy?{}:{timed_segments:[row.points.map(p=>[p.lat,p.lon,p.t])]})})),next_offset:null})};};
 await reload.onclick();assert(document.querySelector('[data-route-track=expired]'),'Server-saved GPS dates produce red');assert(requests.every(url=>url.includes('dates=1')),'Timed API has a distinct offline-cache URL');
 legacy=true;await reload.onclick();assert(!document.querySelector('[data-route-track=qualified]')&&document.querySelector('[data-route-track=learning]'),'Undated legacy API never invents fresh green');
 Object.defineProperty(navigator,'onLine',{value:false,configurable:true});rows=[make('forward-1'),make('forward-2'),make('backward-1',true),make('backward-2',true)];await reload.onclick();
 rows=rows.map((row,i)=>make('priority-old-'+i,i>=2,400));await reload.onclick();assert(document.querySelector('[data-route-track=expired]'),'GPS genuinely stale before imported qualification');const before=localLoads;const mile=reference[5],imported={status:'streckenkundig',valid_until:'2099-01-01',map_match:{status:'mapped',route:'1000',from_m:Math.min(...mile),to_m:Math.max(...mile),reference_revision:window.RailNetwork.revision}};emitImports({items:[imported]});assert(document.querySelector('[data-confirmed-priority]')&&document.querySelector('[data-route-track=qualified]'),'Imported qualification cannot be downgraded by GPS');assert(document.querySelector('[data-imported-knowledge=qualified]'),'Manual CSV knowledge colours real M1 route without adding GPS journeys');assert(document.querySelector('[data-imported-knowledge=qualified]').getAttribute('stroke-dasharray'),'Imported knowledge visually separate');assert(localLoads===before,'Import rendering never manufactures/reloads GPS');const importedToggle=document.querySelector('[data-import-knowledge-toggle]');importedToggle.checked=false;importedToggle.dispatchEvent(new Event('change'));assert(!document.querySelector('[data-imported-knowledge]')&&document.querySelector('[data-route-track=expired]'),'Imported layer toggles independently and underlying GPS age is retained');importedToggle.checked=true;importedToggle.dispatchEvent(new Event('change'));assert(document.querySelector('[data-imported-knowledge=qualified]'),'Imported layer restored');emitImports({items:[]});assert(!document.querySelector('[data-imported-knowledge]'),'Another owner or cleared import removes all imported marks');
 window.StationCatalogSeed={operating_points:[{code:'TEST',name:'Testpunkt',route:'1000',km:'0,0 + 0',lat:51.15,lon:10.4,type_name:'Bahnhof',state:'in Betrieb'}]};const plus=[...document.querySelectorAll('.gps-map-tools button')].find(b=>b.textContent==='+');for(let i=0;i<7;i++)plus.click();const dot=document.querySelector('[data-operating-point=TEST]');assert(dot&&dot.getAttribute('role')==='button','Operating point shown at detailed zoom');dot.dispatchEvent(new MouseEvent('click',{bubbles:true}));assert(document.querySelector('[role=status]').textContent.includes('Testpunkt'),'Touch-accessible point details');assert([...document.querySelectorAll('.route-knowledge-map text')].some(t=>t.textContent==='TEST'),'DS100 code label at detailed zoom');
 const map=document.querySelector('.route-knowledge-map');assert(map.getBoundingClientRect().width<=innerWidth,'Map fits narrow tablet/phone width');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','portal-theme.css','responsive.css'])
    source=localize_html((STATIC/'tf-portal.html').read_text());markup='<section id="routeKnowledge"'+source.split('<section id="routeKnowledge"',1)[1].split('<section id="updatesModule"',1)[0];markup=markup.replace('id="routeKnowledge" hidden','id="routeKnowledge"')
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main>'+markup+'</main><script>'+scripts+checks+'</script></body></html>'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,assets={'/tf/rail-network-data.js':STATIC/'rail-network-data.js'},label='M1 offline rail network')
