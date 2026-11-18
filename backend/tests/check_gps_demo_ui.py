"""Real-browser GPS-DEMO playback checks with isolated, synthetic recording data."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html

def fixture():
    page=localize_html((runner.STATIC/'tf-portal.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css'])
    scripts='\n'.join((runner.STATIC/name).read_text() for name in ['messages.js','gps-settings.js','gps.js','gps-demo.js'])
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);},wait=()=>new Promise(resolve=>setTimeout(resolve,350));
 document.getElementById('gpsDemo').hidden=false;
 let now=0,requests=[],nativeCalls=0,fail=false;
 Object.defineProperty(performance,'now',{value:()=>now});
 Object.defineProperty(navigator,'onLine',{get:()=>false});
 Object.defineProperty(window,'indexedDB',{get(){throw Error('Demo must not access recording storage');}});
 window.AndroidPortal={gps:()=>{nativeCalls++;throw Error('Demo must not use native GPS');}};
 const preferences={owner_id:1,revision:1,first_name:'DemoName',stop_minutes:15,marker:'circle',share_enabled:true,show_elapsed:true,show_stopped:false,show_speed:false,show_train:false,show_first_name:true};
 const base=1794358800000,record={train_number:'DEMO123',stop_minutes:1,ended:true,points:Array.from({length:1801},(_,i)=>({t:base+i*10000,lat:52,lon:13+Math.max(0,i-30)*.0008,accuracy:5,speed:i<=30?0:10})),manual_stops:[],stop_edits:{}};
 const original=JSON.stringify(record);
 window.fetch=async(url,options)=>{requests.push({url,options});if(fail)throw Error('Offline');return {ok:true,json:async()=>String(url).includes('/gps-demo/shared')?{items:[],next_offset:null}:String(url).includes('/gps-demo/stations')?{items:JSON.parse(options.body).points.map(()=>({station:null}))}:String(url).endsWith('gps-settings')?preferences:String(url).includes('gps-recordings')?{items:[{journey_id:'record',train_number:'DEMO123',start:base,end:base+18000000}],next_offset:null}:String(url).includes('gps-shared-positions')?{positions:[{id:2,lat:53,lon:14,t:Date.now(),marker:'steam',first_name:'LivePeer'}]}:record};};
 await window.startGpsDemo({id:1});
 const workspace=document.getElementById('gpsDemoWorkspace'),buttons=workspace.querySelectorAll('.gps-demo-controls button');
 const [load,more,play,reset]=buttons,[selection,speed]=workspace.querySelectorAll('select'),seek=workspace.querySelector('input[type=range]'),output=workspace.querySelector('output');
 assert(selection.options.length===1&&!load.disabled,'Own recording offered');await load.onclick();
 assert(workspace.querySelector('.gps-map>svg'),'Original GPS renderer displays demo map');assert(workspace.querySelector('.gps-tools').hidden,'Recording controls hidden in demo');
 speed.value='300';speed.dispatchEvent(new Event('change'));play.click();now=1000;await wait();play.click();
 assert(output.textContent.startsWith('00:05:00'),'300x playback advances five minutes in one second');
 seek.value='9000000';seek.dispatchEvent(new Event('input'));assert(output.textContent.startsWith('02:30:00'),'Time slider seeks');
 const position=workspace.querySelector('[data-gps-position]');assert(position,'Playback shows current train position');
 assert(!position.querySelector('path')&&position.querySelector('circle'),'Saved circle icon applied in demo');
 assert(position.textContent.includes('DemoName')&&!position.textContent.includes('DEMO123')&&!position.textContent.includes('km/h'),'Saved visible fields applied in demo');
 assert(/^\d{2}:\d{2}$/.test(position.querySelector('text').textContent),'Demo time without labels or dangling slash');
 assert(!workspace.querySelector('[data-gps-stop]'),'Saved 15-minute threshold suppresses recorded five-minute stand');
 assert(!workspace.querySelector('[data-gps-peer]'),'Demo excludes real live positions');
 reset.click();assert(output.textContent.startsWith('00:00:00'),'Reset returns to beginning');
 assert(!window.GpsRecorder.isActive()&&nativeCalls===0,'Demo never starts a recording');assert(JSON.stringify(record)===original,'Original recording unchanged');
 assert(requests.every(request=>!request.options.method||request.options.method==='GET'||(request.options.method==='POST'&&request.url.endsWith('/gps-demo/stations'))),'Only read requests and read-only station lookups');
 const width=innerWidth;for(const control of workspace.querySelectorAll('button,select,input')){if(control.hidden||!control.getClientRects().length)continue;const box=control.getBoundingClientRect();assert(box.left>=0&&box.right<=width+1,'Controls fit viewport');}
 fail=true;await load.onclick();assert(play.disabled,'Failed reload cannot play stale recording');
 fail=false;preferences.marker='steam';await load.onclick();seek.value='9000000';seek.dispatchEvent(new Event('input'));assert(workspace.querySelector('[data-gps-position] image')?.getAttribute('href')==='/tf/gps-marker-steam.png','Demo applies selected original PNG');const decoded=new Image();decoded.src=workspace.querySelector('[data-gps-position] image').getAttribute('href');await decoded.decode();assert(decoded.naturalWidth===128,'Demo original PNG loaded');
 document.documentElement.dataset.layoutStatus='pass';window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    assets={'/tf/gps-marker-'+name+'.png':runner.STATIC/('gps-marker-'+name+'.png') for name in ['electric','steam','diesel','tank']}
    check_pages(fixture,args.output_dir,assets=assets,label="GPS demo")
