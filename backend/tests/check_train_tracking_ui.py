"""Real complete national network, disclosed labels, stale/offline and revoked access."""
import argparse,re,json
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def fixture():
    page=localize_html((STATIC/'train-tracking.html').read_text());page=re.sub(r'<script\b[^>]*>.*?</script>|<link\b[^>]*>','',page,flags=re.S)
    css='\n'.join((STATIC/f).read_text() for f in ['tf-portal.css','portal-theme.css','responsive.css'])
    setup=r'''
window.I18n={t:s=>s,locale:'de-DE'};
const requests=[],clock=Date.now(),timers=new Map(),nativeNow=Date.now;let when=clock,mode='ok';Date.now=()=>when;
window.setInterval=(fn,ms)=>{timers.set(ms,fn);return ms;};window.clearInterval=()=>{};
indexedDB.open=()=>{throw Error('Must never read private TF caches');};
window.fetch=async(url,options)=>{requests.push([url,options]);if(mode==='offline')throw Error('offline');if(mode==='denied')return{status:403,ok:false,json:async()=>({})};return{ok:true,status:200,json:async()=>({positions:[{id:7,lat:51.15,lon:10.4,t:clock,train_number:'12345',first_name:'Anna'},{id:8,lat:51.5,lon:11,t:clock}],expires_after_seconds:600})};};
'''
    scripts='\n'.join((STATIC/f).read_text() for f in ['messages.js','rail-network.js','train-tracking.js'])
    checks=r'''
(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m);};await window.RailNetwork.load();await new Promise(resolve=>setTimeout(resolve,0));
 assert(document.querySelectorAll('[data-rail-network]').length>0,'Actual complete reference network');assert(document.querySelectorAll('[data-tracking-position]').length===2,'Shared GPS points on map');const marker=document.querySelector('[data-tracking-position="7"]'),number=marker.querySelector('[data-tracking-label=train_number]'),name=marker.querySelector('[data-tracking-label=first_name]'),icon=marker.querySelector('image');assert(number.textContent==='12345'&&name.textContent==='Anna','Disclosed train number and TF name');assert(+number.getAttribute('y')<+icon.getAttribute('y')&&+name.getAttribute('y')>+icon.getAttribute('y')+32,'Number above, name below small PNG');assert(!document.querySelector('[data-tracking-position="8"] text'),'Hidden attributes are never invented');assert(+icon.getAttribute('width')===32,'Small proportional icon');
 assert(requests.every(([url,opts])=>url==='/api/v1/admin/tracking/positions'&&opts.cache==='no-store'&&!opts.method),'Only protected read-only feed, never historical GPS');
 mode='offline';await window.TrainTracking.reload();assert(document.querySelector('[data-tracking-position]'),'Transient connection failure preserves only unexpired points');when=clock+601000;timers.get(1000)();assert(!document.querySelector('[data-tracking-position]'),'Expired positions disappear without successful refresh');
 when=clock;mode='ok';await window.TrainTracking.reload();assert(document.querySelector('[data-tracking-position]'),'Fresh feed restores positions');document.getElementById('trackingPlus').click();document.getElementById('trackingMinus').click();document.getElementById('trackingHome').click();assert(document.getElementById('trackingMap').getBoundingClientRect().width<=innerWidth,'Map fits viewport');
 mode='denied';await window.TrainTracking.reload();assert(!document.querySelector('[data-tracking-position]')&&document.getElementById('trackingRefresh').disabled,'Revoked access clears positions and stops polling');
 Date.now=nativeNow;window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+setup+scripts+checks+'</script></body>')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,assets={'/tf/rail-network-data.js':STATIC/'rail-network-data.js','/tf/gps-marker-electric.png':STATIC/'gps-marker-electric.png'},label='Train tracking')
