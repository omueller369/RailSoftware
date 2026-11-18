"""Synthetic browser checks for consent, read-only stops, DS100 refresh and revocation."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html

def fixture():
    page=localize_html((runner.STATIC/'admin-gps-demo.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css'])
    scripts='\n'.join((runner.STATIC/name).read_text() for name in ['messages.js','gps-settings.js','gps.js','gps-demo.js'])
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);},wait=()=>new Promise(resolve=>setTimeout(resolve,20));
 Object.defineProperty(window,'indexedDB',{get(){throw Error('No recording storage in demo');}});
 navigator.geolocation.getCurrentPosition=()=>{throw Error('No GPS in demo');};
 let shared=false,available=true,failPublish=false,requests=[],privateCalls=0,stationName='Current DS100',stationCalls=0;
 const base=1794358800000,record={detection_version:5,train_number:'DEMO',stop_minutes:1,ended:true,points:Array.from({length:60},(_,i)=>({t:base+i*5000,lat:52,lon:13,accuracy:5,speed:0})),manual_stops:[{key:'manual-test',start:base+20000,end:base+100000}],stop_edits:{['live-'+base]:{station_input:'Old place',reason:'Zugfolge',cause:'DB-InfraGo'}}};
 const original=JSON.stringify(record),meta={journey_id:'own',train_number:'DEMO',revision:1,shared:false,start:base,end:base+295000};
 window.fetch=async(url,options={})=>{url=String(url);requests.push([url,options.method||'GET']);let data={};
  if(url.endsWith('gps-settings'))data={owner_id:1,revision:1,first_name:'VIEWER_NAME',stop_minutes:1,marker:'circle',show_elapsed:true,show_stopped:true,show_speed:true,show_train:true,show_first_name:true,share_enabled:true};
  else if(url.includes('gps-recordings')){privateCalls++;data={items:[{...meta,shared}],next_offset:null};}
  else if(url.endsWith('/shares')){if(failPublish)return {ok:false,status:503};shared=JSON.parse(options.body).changes[0].shared;data={items:[]};}
  else if(url.includes('/shared?'))data={items:shared?[{id:7,train_number:'SHARED',start:base,end:base+295000}]:[],next_offset:null};
  else if(url.endsWith('/access'))return {ok:available&&shared,json:async()=>({available:available&&shared})};
  else if(url.endsWith('/stations')){stationCalls++;data={items:JSON.parse(options.body).points.map(()=>({station:{code:'NEW',name:stationName}}))};}
  else if(url.endsWith('/gps/own')){privateCalls++;data=record;}
  else if(url.endsWith('/shared/7'))data=record;
  else throw Error('Unexpected request '+url);
  return {ok:true,json:async()=>structuredClone(data)};
 };
 const realInterval=window.setInterval;let accessCheck;window.setInterval=(fn,ms)=>ms===30000?(accessCheck=fn,0):realInterval(fn,ms);
 await startGpsDemo({id:1});let root=document.getElementById('gpsDemoWorkspace');
 let check=root.querySelector('input[type=checkbox]');assert(check&&!check.checked,'Sharing is explicit and off by default');check.scrollIntoView({block:'center'});const hit=check.getBoundingClientRect();assert(document.elementFromPoint(hit.left+hit.width/2,hit.top+hit.height/2)===check,'Checkbox is an unobstructed touch target');check.click();const publish=root.querySelector('[data-gps-demo-publish]');assert(check.checked&&!shared&&!publish.disabled,'Native checkbox is clickable and only stages the selection');assert(!requests.some(([,method])=>method==='PUT'||method==='POST'),'No sharing request before confirmation');failPublish=true;await publish.onclick();assert(!shared&&root.querySelector('input[type=checkbox]').checked&&!publish.disabled,'Failed publish retains staged selection');failPublish=false;await publish.onclick();assert(shared,'Only confirmation publishes the selection');assert(root.querySelector('option[value="shared:7"]'),'Shared demo is offered');
 let selection=root.querySelector('select'),load=root.querySelector('.gps-demo-controls button');selection.value='shared:7';await load.onclick();
 let seek=root.querySelector('input[type=range]');seek.value='295000';seek.oninput();
 assert(root.querySelector('.gps-demo-stops').textContent.includes('NEW · Current DS100'),'Current DS100 enriches an old recording');assert(root.querySelector('.gps-demo-stops tbody').children.length===2,'Automatic and manual stops shown');const cells=root.querySelector('.gps-demo-stops tbody tr').children;assert(/^\d{2}:\d{2}$/.test(cells[1].textContent)&&/^\d{2}:\d{2}$/.test(cells[2].textContent),'Stop list contains times without dates');const stopBox=root.querySelector('.gps-demo-stops'),table=stopBox.querySelector('table');assert(Math.abs(table.getBoundingClientRect().width-stopBox.clientWidth)<4,'Stop table uses full flexible width');assert(!root.querySelector('.gps-demo-stops input,.gps-demo-stops button,.gps-demo-stops select'),'Stops have no editing controls');assert(root.querySelector('[data-gps-stop]'),'Stop circles shown on map');assert(!root.querySelector('[data-gps-position]').textContent.includes('VIEWER_NAME'),'Shared replay never labels the owner with the viewer name');assert(JSON.stringify(record)===original,'Source recording unchanged');
 stationName='Updated DS100';await load.onclick();seek.value='295000';seek.oninput();assert(root.querySelector('.gps-demo-stops').textContent.includes('Updated DS100'),'Reload picks up later DS100 entries');
 available=false;await accessCheck();assert(!root.querySelector('.gps-map>svg'),'Revocation clears map');assert(!root.querySelector('.gps-demo-stops table'),'Revocation clears stop data');assert(root.querySelectorAll('.gps-demo-controls')[1].querySelector('button').disabled,'Revocation disables playback');
 available=true;const oldPrivate=privateCalls;await startGpsDemo({id:99},{administration:true});root=document.getElementById('gpsDemoWorkspace');assert(!root.querySelector('input[type=checkbox]'),'Administration cannot publish another TF recording');selection=root.querySelector('select');assert(selection.options.length===1&&selection.value==='shared:7','Administration receives shared recordings only');load=root.querySelector('.gps-demo-controls button');await load.onclick();seek=root.querySelector('input[type=range]');seek.value='295000';seek.oninput();assert(root.querySelector('.gps-demo-stops tbody').children.length===2,'Administrative replay displays same read-only stops');assert(privateCalls===oldPrivate,'No private TF API requested by administration');
 assert(requests.every(([url,method])=>method==='GET'||url.endsWith('/stations')||url.endsWith('/shares')),'No recording/report/live-sharing writes');assert(stationCalls>=3,'DS100 refreshed per playback load');
 const width=innerWidth;for(const control of root.querySelectorAll('button,select,input')){if(control.hidden||!control.getClientRects().length)continue;const box=control.getBoundingClientRect();assert(box.left>=0&&box.right<=width+1,'Controls fit viewport');}
 document.documentElement.dataset.layoutStatus='pass';window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,label='GPS demo sharing')
