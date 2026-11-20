"""Real M1 map: parallel multi-selection, persistent edits, node filter and pin suggestions."""
import argparse
from check_manual_route_ui import fixture as base_fixture,ASSETS
from check_work_report_layout import STATIC
from browser_realtime import check_pages

def fixture():
    page=base_fixture().replace('</head>','<style>'+(STATIC/'portal-theme.css').read_text()+'</style></head>')
    checks=r'''
 {
 const navRoot=document.createElement('div');document.body.append(navRoot);const nav=ManualRouteEditor.mount({id:1},navRoot,async()=>{});await wait();
 nav.select(M1Map.points().byCode.get('AFW')[0],true);
 assert(navRoot.querySelector('[data-route-suggestion-line]'),'Connected next sections are light-blue previews');assert(navRoot.querySelector('[data-route-marker=suggested]'),'Possible next point uses a light-blue location pin');assert(navRoot.querySelector('[data-route-marker=selected]'),'Selected start uses a light-green pin');
 nav.select(M1Map.points().byCode.get('AFR')[0]);const before=nav.waypoints.join(','),lineBefore=navRoot.querySelector('[data-manual-route-line]').getAttribute('d'),filter=navRoot.querySelector('[data-route-nodes-only]');filter.checked=true;filter.dispatchEvent(new Event('change'));
 assert(nav.waypoints.join(',')===before&&navRoot.querySelector('[data-manual-route-line]').getAttribute('d')===lineBefore,'Node filter preserves selected points and drawn sections');for(const point of navRoot.querySelectorAll('[data-m1-point]')){const code=point.getAttribute('data-m1-point');assert(nav.waypoints.includes(code)||M1Map.isJunction(code,RailNetworkSeed),'Filter hides ordinary intermediate points');}
 const undo=navRoot.querySelector('[data-route-map-undo]'),mapBox=navRoot.querySelector('.manual-route-map svg').getBoundingClientRect(),undoBox=undo.getBoundingClientRect();assert(undoBox.left>=mapBox.left&&undoBox.left<mapBox.left+16&&undoBox.top>=mapBox.top&&undoBox.top<mapBox.top+16,'Undo sits inside actual map top-left at every width');assert(getComputedStyle(undo).backgroundColor==='rgba(0, 0, 0, 0)','Undo background is transparent');assert(!navRoot.querySelector('.route-editor-controls [data-route-map-undo]'),'Undo is not beside the map');
 filter.checked=false;filter.dispatchEvent(new Event('change'));nav.select(M1Map.points().byCode.get('ALD')[0],true);nav.select(M1Map.points().byCode.get('ALD A')[0]);let choice=navRoot.querySelector('[data-route-waypoint] select'),all=[...choice.options].find(o=>o.textContent==='Alle Strecken zugleich');assert(all,'Real parallel lines offer All lines at once');choice.value=all.value;choice.dispatchEvent(new Event('change'));assert(!navRoot.querySelector('[data-route-save]').disabled,'Parallel multiple selection enables save');await navRoot.querySelector('form').onsubmit({preventDefault(){}});let payload=JSON.parse(requests.at(-1)[1].body);assert(Array.isArray(payload.routes[0])&&payload.routes[0].includes('1113')&&payload.routes[0].includes('1115'),'Explicit save includes both parallel VzG lines');navRoot.querySelector('[data-saved-route]').click();choice=navRoot.querySelector('[data-route-waypoint] select');assert(choice.value.startsWith('@'),'Editing restores parallel selection');
 nav.select(M1Map.points().byCode.get('ABLZ')[0],true);nav.select(M1Map.points().byCode.get('AHAR')[0]);choice=navRoot.querySelector('[data-route-waypoint] select');assert(choice.options.length>=3&&![...choice.options].some(o=>o.textContent==='Alle Strecken zugleich'),'Divergent lines sharing end points never offer parallel selection');
 }
 '''
    return page.replace(" window.parent.postMessage({layoutStatus:'pass'},'*');",checks+" window.parent.postMessage({layoutStatus:'pass'},'*');")
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args();check_pages(fixture,args.output_dir,widths=(1280,800,375,320),assets={'/tf/'+name:STATIC/name for name in ASSETS},label='Manual M1 navigation',timeout=40)
