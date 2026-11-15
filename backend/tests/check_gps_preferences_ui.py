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
 assert(form.elements.marker.options.length===5,'Original marker and four new icons');assert(form.elements.share_enabled.value==='false','Consent defaults to No');
 assert(form.querySelectorAll('input[type=checkbox]').length===5,'Five display/privacy choices');
 const container=document.createElement('section'),tools=document.createElement('div');container.append(tools);document.body.append(container);let active=true;
 const recorder={o:{userId:1,journeyId:'00000000-0000-4000-8000-000000000002',trainNumber:()=> '123'},key:'1.test',box:container,record:{train_number:'123',stop_minutes:1,points:[{t:Date.now(),lat:52,lon:13,accuracy:5,speed:12}]},drawMap(){},liveMetrics:()=>({elapsed:60000,stopped:30000}),liveManualStops:()=>[],fail(message){throw Error(message);}};
 const control=window.GpsPreferences.attach(recorder,tools,()=>active);await window.GpsPreferences.load(1);await new Promise(resolve=>setTimeout(resolve,0));const share=tools.querySelector('button');assert(share.hidden,'Share hidden without consent');
 form.elements.share_enabled.value='true';form.elements.marker.value='steam';form.elements.stop_minutes.value='1';await form.onsubmit({preventDefault(){}});
 assert(!share.hidden,'Share visible after consent');assert(!writes.some(url=>url.includes('gps-sharing')),'Consent does not start sharing');
 await share.onclick();assert(writes.filter(url=>url.endsWith('/start')).length===1,'Explicit share start only');assert(share.getAttribute('aria-pressed')==='true','Active share shown');
 const count=writes.length;await control.changed();assert(writes.length===count,'No second position inside five minutes');
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),make=tag=>document.createElementNS(svg.namespaceURI,tag);window.GpsPreferences.marker(svg,make,20,20,{marker:'steam',first_name:'<img src=x>'},true);assert(svg.querySelector('[data-gps-position]'),'Selected marker drawn');assert(!svg.querySelector('img'),'First name rendered safely');
 await share.onclick();assert(share.getAttribute('aria-pressed')==='false','Explicit share stop');assert(writes.some(url=>url.includes('gps-sharing/')&&!url.endsWith('/start')),'Position endpoint used');
 for(const field of form.querySelectorAll('input,select')){const r=field.getBoundingClientRect();assert(r.left>=0&&r.right<=innerWidth+1,'Settings controls fit viewport');}
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')


if __name__=='__main__':
    runner.fixture=fixture
    runner.main()
