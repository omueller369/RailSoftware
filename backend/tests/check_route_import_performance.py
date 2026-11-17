"""Actual SVG render with full reference and 2013 synthetic imports at 4x CPU slowdown."""
import argparse,re,html,json
from pathlib import Path
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from check_rail_network_ui import fixture as base_fixture

def fixture():
    page=base_fixture()
    # Keep only setup through loading the actual full public network, then stress the renderer.
    marker=" const reference=data.lines.find"
    start=page.index(marker)
    end=page.index("})().catch(error=>",start)
    checks=r'''
 const lines=data.lines.filter(row=>row[5]),items=[];for(let i=0;i<2013;i++){const row=lines[Math.floor(i*lines.length/2013)];items.push({status:['streckenkundig','abgelaufen','wird erworben'][i%3],valid_until:'2027-12-31',map_match:{status:'mapped',route:data.routes[row[0]][0],from_m:row[5][0],to_m:row[5][1],reference_revision:window.RailNetwork.revision}});}
 const original=JSON.stringify(items);let emit;window.GpsRecorder={localRecords:async()=>[]};window.RouteCsv={mount:async(user,root,callback)=>{emit=callback;}};
 await window.startRouteKnowledge({id:7});const begin=performance.now();emit({items});const cold=performance.now()-begin;await new Promise(requestAnimationFrame);const first=document.querySelector('[data-imported-knowledge]');assert(first,'Large imported inventory is actually drawn');const commands=[...document.querySelectorAll('[data-imported-knowledge]')].reduce((n,path)=>n+(path.getAttribute('d').match(/[ML]/g)||[]).length,0);assert(commands>100&&commands<20000,'Overview geometry stays compact');assert(cold<10000,'Cold render under 4x CPU slowdown remains bounded');
 let heartbeat=false;setTimeout(()=>heartbeat=true,0);const repeat=performance.now();emit({items});const warm=performance.now()-repeat;await new Promise(resolve=>setTimeout(resolve,0));assert(heartbeat&&warm<3000,'Repeated drawing yields to UI and reuses imported geometry');
 const buttons=[...document.querySelectorAll('.gps-map-tools button')],plus=buttons.find(b=>b.textContent==='+'),minus=buttons.find(b=>b.textContent==='−');plus.click();await new Promise(requestAnimationFrame);minus.click();await new Promise(requestAnimationFrame);assert(document.querySelector('[data-imported-knowledge]'),'Zoom preserves all imported layers');assert(JSON.stringify(items)===original,'Knowledge snapshot is unchanged');emit({items:[]});assert(!document.querySelector('[data-imported-knowledge]'),'Changing owner/removing snapshot clears old layer');
 emit({items});await new Promise(requestAnimationFrame);document.body.dataset.performance=JSON.stringify({entries:2013,cpuSlowdown:4,coldMs:Math.round(cold),repeatMs:Math.round(warm),commands});window.parent.postMessage({layoutStatus:'pass',message:document.body.dataset.performance},'*');
'''
    return page[:start]+checks+page[end:]
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args();check_pages(fixture,args.output_dir,widths=(800,),assets={'/tf/rail-network-data.js':STATIC/'rail-network-data.js'},label='Large imported inventory performance',cpu_rate=4,timeout=60)

    capture=(Path(args.output_dir)/'800.html').read_text();match=re.search(r'data-layout-message="([^"]*)"',capture)
    if match:
        metrics=json.loads(html.unescape(match[1]));(Path(args.output_dir)/'timings.json').write_text(json.dumps(metrics,indent=2)+'\n');print(json.dumps(metrics))
