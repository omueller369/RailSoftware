"""Real-browser GPS-DEMO playback checks with isolated, synthetic recording data."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html

def fixture():
    page=localize_html((runner.STATIC/'tf-portal.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css'])
    scripts='\n'.join((runner.STATIC/name).read_text() for name in ['messages.js','gps.js','gps-demo.js'])
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);},wait=()=>new Promise(resolve=>setTimeout(resolve,350));
 document.getElementById('gpsDemo').hidden=false;
 let now=0,requests=[],nativeCalls=0,fail=false;
 Object.defineProperty(performance,'now',{value:()=>now});
 Object.defineProperty(navigator,'onLine',{get:()=>false});
 Object.defineProperty(window,'indexedDB',{get(){throw Error('Demo must not access recording storage');}});
 window.AndroidPortal={gps:()=>{nativeCalls++;throw Error('Demo must not use native GPS');}};
 const base=1794358800000,record={train_number:'DEMO123',ended:true,points:Array.from({length:1801},(_,i)=>({t:base+i*10000,lat:52,lon:13+i*.0008,accuracy:5,speed:10})),manual_stops:[],stop_edits:{}};
 const original=JSON.stringify(record);
 window.fetch=async(url,options)=>{requests.push({url,options});if(fail)throw Error('Offline');return {ok:true,json:async()=>String(url).includes('gps-recordings')?{items:[{journey_id:'record',train_number:'DEMO123',start:base,end:base+18000000}],next_offset:null}:record};};
 await window.startGpsDemo({id:1});
 const workspace=document.getElementById('gpsDemoWorkspace'),buttons=workspace.querySelectorAll('.gps-demo-controls button');
 const [load,more,play,reset]=buttons,[selection,speed]=workspace.querySelectorAll('select'),seek=workspace.querySelector('input[type=range]'),output=workspace.querySelector('output');
 assert(selection.options.length===1&&!load.disabled,'Own recording offered');await load.onclick();
 assert(workspace.querySelector('.gps-map>svg'),'Original GPS renderer displays demo map');assert(workspace.querySelector('.gps-tools').hidden,'Recording controls hidden in demo');
 speed.value='300';speed.dispatchEvent(new Event('change'));play.click();now=1000;await wait();play.click();
 assert(output.textContent.startsWith('00:05:00'),'300x playback advances five minutes in one second');
 seek.value='9000000';seek.dispatchEvent(new Event('input'));assert(output.textContent.startsWith('02:30:00'),'Time slider seeks');
 const position=workspace.querySelector('[data-gps-position]');assert(position,'Playback shows current train position');
 reset.click();assert(output.textContent.startsWith('00:00:00'),'Reset returns to beginning');
 assert(!window.GpsRecorder.isActive()&&nativeCalls===0,'Demo never starts a recording');assert(JSON.stringify(record)===original,'Original recording unchanged');
 assert(requests.every(request=>!request.options.method||request.options.method==='GET'),'Only read requests');
 const width=innerWidth;for(const control of workspace.querySelectorAll('button,select,input')){if(control.hidden||!control.getClientRects().length)continue;const box=control.getBoundingClientRect();assert(box.left>=0&&box.right<=width+1,'Controls fit viewport');}
 fail=true;await load.onclick();assert(play.disabled,'Failed reload cannot play stale recording');
 fail=false;await load.onclick();seek.value='9000000';seek.dispatchEvent(new Event('input'));
 document.documentElement.dataset.layoutStatus='pass';window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    runner.fixture=fixture
    runner.main()
