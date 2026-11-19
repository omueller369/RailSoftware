"""Real DOM: settings, explicit start/stop gate and customizable map marker."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html


def fixture():
    page=localize_html((runner.STATIC/'tf-profile.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','responsive.css'])
    mocks=r'''
const writes=[],prefs={owner_id:1,first_name:'Anna',revision:0,stop_minutes:2,marker:'electric',show_elapsed:true,show_stopped:true,show_speed:true,show_train:true,show_first_name:false,share_enabled:false};
window.fetch=async(url,options={})=>{let data;if(url.endsWith('gps-settings')){if(options.method==='PUT'){Object.assign(prefs,JSON.parse(options.body));prefs.revision++;writes.push(url);}data={...prefs};}else if(url.endsWith('/start')){writes.push(url);data={session_id:'00000000-0000-4000-8000-000000000001'};}else if(options.method==='PUT'){writes.push(url);data={accepted:true};}else if(options.method==='DELETE'){writes.push(url);data={ok:true};}else data={positions:[]};return {ok:true,status:200,json:async()=>data};};
'''
    scripts=(runner.STATIC/'messages.js').read_text()+'\n'+mocks+(runner.STATIC/'gps-settings.js').read_text()
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 for(let i=0;i<100&&!document.querySelector('#profileGpsSettings button:not(:disabled)');i++)await new Promise(resolve=>setTimeout(resolve,0));
 const form=document.querySelector('#profileGpsSettings form');assert(form,'GPS settings form');
 assert([...form.elements.stop_minutes.options].map(o=>o.value).join(',')==='1,2,4,5,10,15','All six thresholds');
 assert(form.querySelectorAll('input[type=radio][name=marker]').length===5,'Five illustrated radio options');assert(form.querySelectorAll('[data-gps-icon-preview]').length===5,'Every option has a map icon preview');assert(form.elements.share_enabled.value==='false','Consent defaults to No');
 assert(form.querySelectorAll('input[type=checkbox]').length===5,'Five display/privacy choices');
 const container=document.createElement('section'),tools=document.createElement('div');container.append(tools);document.body.append(container);let active=true;
 const recorder={o:{userId:1,journeyId:'00000000-0000-4000-8000-000000000002',trainNumber:()=> '123'},key:'1.test',box:container,record:{train_number:'123',stop_minutes:1,points:[{t:Date.now(),lat:52,lon:13,accuracy:5,speed:12}]},drawMap(){},liveMetrics:()=>({elapsed:60000,stopped:30000}),liveManualStops:()=>[],fail(message){throw Error(message);}};
 const control=window.GpsPreferences.attach(recorder,tools,()=>active);await window.GpsPreferences.load(1);await new Promise(resolve=>setTimeout(resolve,0));const share=tools.querySelector('button');assert(share.hidden,'Share hidden without consent');
 form.elements.share_enabled.value='true';form.querySelector('input[name=marker][value=steam]').click();assert(form.elements.marker.value==='steam','Click selects one icon');form.elements.stop_minutes.value='1';await form.onsubmit({preventDefault(){}});
 assert(!share.hidden,'Share visible after consent');assert(!writes.some(url=>url.includes('gps-sharing')),'Consent does not start sharing');
 await share.onclick();assert(writes.filter(url=>url.endsWith('/start')).length===1,'Explicit share start only');assert(share.getAttribute('aria-pressed')==='true','Active share shown');
 assert(form.querySelectorAll('input[name=marker]:checked').length===1,'Exactly one icon selected');
 const selected=form.querySelector('input[name=marker]:checked');const label=selected.closest('label'),preview=label.querySelector('svg');assert(selected.getBoundingClientRect().top>=preview.getBoundingClientRect().bottom,'Radio button below icon');
 const sample=document.createElementNS('http://www.w3.org/2000/svg','svg');window.GpsPreferences.marker(sample,tag=>document.createElementNS(sample.namespaceURI,tag),0,0,{marker:'steam'},true);assert(sample.firstElementChild.innerHTML===preview.firstElementChild.innerHTML,'Preview uses exact original map icon');
 window.dispatchEvent(new Event('languagechange'));assert(form.elements.marker.value==='steam','Language change preserves radio selection');assert(new Set([...form.querySelectorAll('[name=marker]')].map(r=>r.value)).size===5,'Language change retains all distinct icon values');
 const count=writes.length;await control.changed();assert(writes.length===count,'No second position inside five minutes');
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),make=tag=>document.createElementNS(svg.namespaceURI,tag);window.GpsPreferences.marker(svg,make,20,20,{marker:'steam',first_name:'<img src=x>'},true);assert(svg.querySelector('[data-gps-position]'),'Selected marker drawn');assert(!svg.querySelector('img'),'First name rendered safely');
 const timing=document.createElementNS(svg.namespaceURI,'svg');window.GpsPreferences.marker(timing,make,0,0,{marker:'circle',elapsed_ms:8100000,stopped_ms:1800000},true);assert(timing.querySelector('text').textContent==='02:15 / 00:30','Elapsed / stopped shown without labels');
 const single=document.createElementNS(svg.namespaceURI,'svg');window.GpsPreferences.marker(single,make,0,0,{marker:'circle',stopped_ms:1800000},true);assert(single.querySelector('text').textContent==='00:30','Single selected time without separator');
 await share.onclick();assert(share.getAttribute('aria-pressed')==='false','Explicit share stop');assert(writes.some(url=>url.includes('gps-sharing/')&&!url.endsWith('/start')),'Position endpoint used');
 for(const field of form.querySelectorAll('input,select')){const r=field.getBoundingClientRect();assert(r.left>=0&&r.right<=innerWidth+1,'Settings controls fit viewport');}
 for(const type of ['electric','steam','diesel','tank']){
  const preview=form.querySelector('[data-gps-icon-preview="'+type+'"]'),image=preview.querySelector('image');
  assert(!preview.querySelector('rect'),'Marker has no frame');
  assert(image?.getAttribute('href')==='/tf/gps-marker-'+type+'.png','Original PNG mapped to '+type);
  const decoded=new Image();decoded.src=image.getAttribute('href');await decoded.decode();assert(decoded.naturalWidth===128&&decoded.naturalHeight===128,'Original 128px PNG loaded: '+type);
  assert(image.getBoundingClientRect().width>=20&&image.getBoundingClientRect().width<=28,'Marker uses readable proportional size');
 }
 assert(!form.querySelector('[data-gps-icon-preview="circle"] image'),'Circle remains a vector option');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')


if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    assets={'/tf/gps-marker-'+name+'.png':runner.STATIC/('gps-marker-'+name+'.png') for name in ['electric','steam','diesel','tank']}
    check_pages(fixture,args.output_dir,assets=assets,label="GPS icons")
