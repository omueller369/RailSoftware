"""Real full M1 bundle offline; directional counts and layer visibility."""
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC


def fixture():
    scripts='\n'.join((STATIC/name).read_text() for name in ['messages.js','route-coverage.js','rail-network.js','route-knowledge.js'])
    checks=r'''
Object.defineProperty(navigator,'onLine',{value:false,configurable:true});
window.I18n={t:s=>s,locale:'de-DE'};
(async()=>{
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 const started=performance.now(),data=await window.RailNetwork.load();
 assert(data.source.source_rows===33425&&data.source.route_count===1549,'Actual supplied M1 dataset loaded');
 const reference=data.lines.find(row=>data.routes[row[0]][0]==='1000'&&row[5]&&Math.abs(row[5][1]-row[5][0])>1000);
 assert(reference,'Long real Flensburg reference line');
 const coords=reference[3],forward=[];for(let i=0;i<coords.length;i+=2)forward.push([Math.atan(Math.sinh(Math.PI*(1-2*coords[i+1]/data.scale)))*180/Math.PI,coords[i]/data.scale*360-180]);
 const make=(id,reverse)=>({journey_id:id,dirty:true,points:(reverse?[...forward].reverse():forward).map((p,i)=>({t:1794900000000+i*5000,lat:p[0],lon:p[1],accuracy:5}))});
 let rows=[make('forward-1'),make('forward-2'),make('backward-1',true),make('backward-2',true)];window.GpsRecorder={localRecords:async()=>rows};
 await window.startRouteKnowledge({id:7});
 assert(document.querySelectorAll('[data-rail-network]').length>0,'National reference geometry visible offline');
 assert(!document.querySelector('.route-knowledge-map image'),'Offline network does not request online map tiles');
 assert(document.querySelector('[data-route-track=qualified]'),'2 + 2 real-network journeys turn GPS green');
 assert(document.querySelector('[data-rail-coverage=qualified]'),'Matched reference bins also green');
 assert(document.querySelector('[data-route-track=qualified]').getAttribute('stroke')==='#16803a','Green stroke');
 assert(performance.now()-started<10000,'Full offline network remains responsive');
 const reload=document.querySelector('#routeKnowledgeWorkspace button');rows=rows.slice(0,3);await reload.onclick();
 assert(!document.querySelector('[data-route-track=qualified]'),'2 + 1 remains blue');
 assert(document.querySelector('[data-route-track=learning]'),'Blue GPS stroke retained');
 const toggle=document.querySelector('[data-network-toggle]');toggle.checked=false;toggle.dispatchEvent(new Event('change'));
 assert(!document.querySelector('[data-rail-network]'),'Reference checkbox hides network');assert(document.querySelector('[data-route-track=learning]'),'Own GPS remains when network hidden');
 toggle.checked=true;toggle.dispatchEvent(new Event('change'));assert(document.querySelector('[data-rail-network]'),'Toggle restores offline reference');assert(!document.querySelector('[data-route-track=qualified]'),'Toggling never creates a passage');
 rows=[];await reload.onclick();assert(!document.querySelector('[data-route-track]'),'Reference alone is never travelled');assert(document.querySelector('[data-rail-network]'),'Reference visible without any recording');
 rows=[make('forward-1'),make('forward-2'),make('backward-1',true),make('backward-2',true)];await reload.onclick();
 const map=document.querySelector('.route-knowledge-map');assert(map.getBoundingClientRect().width<=innerWidth,'Map fits narrow tablet/phone width');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','portal-theme.css','responsive.css'])
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main><h1>Streck-Kenntnisse</h1><div id="routeKnowledgeWorkspace"></div></main><script>'+scripts+checks+'</script></body></html>'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,assets={'/tf/rail-network-data.js':STATIC/'rail-network-data.js'},label='M1 offline rail network')
