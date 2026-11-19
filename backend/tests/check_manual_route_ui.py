"""Real offline M1 references: station selection, autozoom, green preview, confirmation."""
from pathlib import Path
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC

ASSETS=['messages.js','station-catalog-data.js','m1-basemap-data.js','rail-network-data.js','rail-network.js','m1-map.js','station-picker.js','route-imports.js','route-editor.js','route-knowledge.js']
def fixture():
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css'])
    setup="""window.I18n={t:s=>s};Object.defineProperty(navigator,'onLine',{get:()=>false});let requests=[],fail=true,saved=0;window.fetch=async(url,options)=>{requests.push([url,options]);if(fail)throw Error('offline');return {ok:true,json:async()=>({owner_id:1,items:[]})};};"""
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},wait=(ms=25)=>new Promise(r=>setTimeout(r,ms));
 const originalLoad=M1Map.load;let release;M1Map.load=()=>new Promise(resolve=>{release=()=>originalLoad().then(resolve);});const root=document.getElementById('root'),editor=ManualRouteEditor.mount({id:1},root,async()=>{saved++;});assert(root.querySelector('[data-route-start]').disabled,'Start selection waits for reference geometry');release();await wait();M1Map.load=originalLoad;
 assert(root.querySelector('[data-m1-country=DEU]'),'Local Germany background before any selection');
 const input=root.querySelector('[data-route-start]');input.focus();input.value='AFW';input.dispatchEvent(new Event('input',{bubbles:true}));await wait(250);
 const option=[...document.querySelectorAll('.station-picker button')].find(button=>button.textContent.startsWith('AFW ·'));assert(option,'DS100 start found');option.click();
 assert(editor.waypoints.join(',')==='AFW','Chosen station starts the route');
 const origin=root.querySelector('[data-m1-point=AFW]');assert(origin&&origin.getAttribute('transform').includes('300'),'Autozoom centres the chosen station');assert(root.querySelector('[data-m1-point=AFR]'),'Connected operating points visible after autozoom');
 root.querySelector('[data-m1-point=AFR]').dispatchEvent(new MouseEvent('click',{bubbles:true}));
 assert(editor.waypoints.join(',')==='AFW,AFR','Map click appends the next station');
 const choose=root.querySelector('ol select');if(!choose.value){choose.value='1000';choose.dispatchEvent(new Event('change'));}
 const line=root.querySelector('[data-manual-route-line]');assert(line&&line.getAttribute('stroke')==='#7cfc00'&&!line.hasAttribute('stroke-dasharray'),'Preview follows M1 as continuous light-green line');
 assert(requests.length===0&&saved===0,'Selection has not been uploaded or saved');
 const date=root.querySelector('[data-route-until]');assert(date.max&&date.value===date.max,'One calendar year upper bound');
 const form=root.querySelector('form');await form.onsubmit({preventDefault(){}});assert(editor.waypoints.length===2&&!root.querySelector('[data-route-save]').disabled,'Failed save keeps route and permits retry');
 fail=false;await form.onsubmit({preventDefault(){}});assert(saved===1&&editor.waypoints.length===0,'Explicit successful save clears only the selection');const payload=JSON.parse(requests.at(-1)[1].body);assert(payload.routes[0]==='1000'&&payload.waypoints.join(',')==='AFW,AFR','Confirmed M1 route sent without GPS points');assert(!('points' in payload),'No fabricated GPS');
 for(const control of root.querySelectorAll('input,button,select')){const box=control.getBoundingClientRect();assert(box.left>=0&&box.right<=innerWidth+1,'Controls fit viewport');}
 const tabs=document.createElement('div');tabs.innerHTML='<button id="routeTab-view">View</button><button id="routeTab-create">Create</button><section id="routePanel-view"><div id="routeKnowledgeWorkspace"></div></section><section id="routePanel-create" hidden><div id="manualRouteWorkspace"></div></section>';document.body.append(tabs);window.GpsRecorder={localRecords:async()=>[]};window.RouteCsv={mount:()=>Promise.resolve()};await startRouteKnowledge({id:1},{fetch:async()=>({ok:true,json:async()=>({owner_id:1,items:[],next_offset:null})})});assert(!document.getElementById('routePanel-view').hidden&&document.getElementById('routePanel-create').hidden,'Display is the default subtab');document.getElementById('routeTab-create').click();assert(document.getElementById('routePanel-view').hidden&&!document.getElementById('routePanel-create').hidden&&document.getElementById('manualRouteWorkspace').querySelector('[data-route-start]'),'Create subtab opens its own map editor');document.getElementById('routeTab-view').click();assert(!document.getElementById('routePanel-view').hidden,'Return to display subtab');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><main id="root"></main><script>'+setup+'</script>'+''.join('<script src="/tf/'+name+'"></script>' for name in ASSETS)+'<script>'+checks+'</script></body></html>'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,widths=(1280,800,375,320),assets={'/tf/'+name:STATIC/name for name in ASSETS},label='Manual M1 route',timeout=30)
