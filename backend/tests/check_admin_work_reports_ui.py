"""Exercise the read-only inbox with hostile employee text, filters and modal details."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html


def fixture():
    page=localize_html((runner.STATIC/'admin-work-reports.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','responsive.css'])
    mocks=r'''
const calls=[],person={id:4,name:'<img src=x onerror=alert(1)>',personnel_number:'004',employee_category:'wgm'};
window.fetch=async url=>{calls.push(url);let data;if(url.endsWith('/employees'))data=[person];else if(/\/12$/.test(url))data={employee:person,report:{id:12,start_at:'2026-11-12T08:00',end_at:'2026-11-12T16:00',kind:'Dienstschicht',duration_minutes:480,documented_pause_minutes:30,overrun_reason:'<script>unsafe<\/script>',trips:[],train_journeys:[]}};else data={total:1,items:[{id:12,employee:person,start_at:'2026-11-12T08:00',end_at:'2026-11-12T16:00',kind:'Dienstschicht',duration_minutes:480}]};return {ok:true,status:200,json:async()=>data};};
'''
    scripts=(runner.STATIC/'messages.js').read_text()+'\n'+mocks+(runner.STATIC/'admin-work-reports.js').read_text()
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 for(let i=0;i<100&&!document.querySelector('#reportRows tr');i++)await new Promise(resolve=>setTimeout(resolve,0));
 assert(document.querySelectorAll('#reportRows tr').length===1,'Inbox has incoming report');
 assert(!document.querySelector('#reportRows img'),'Employee name remains plain text');
 assert(!document.querySelector('main').textContent.includes('{{'),'All translated placeholders resolved');
 const category=document.getElementById('reportCategory');category.value='wgm';category.dispatchEvent(new Event('change'));await new Promise(resolve=>setTimeout(resolve,0));
 assert(calls.some(url=>url.includes('employee_category=wgm')),'Category filter sent');
 document.querySelector('#reportRows button').click();await new Promise(resolve=>setTimeout(resolve,0));
 const dialog=document.getElementById('reportDialog');assert(dialog.open,'Detail dialog opens');
 assert(document.getElementById('reportDetailBody').textContent.includes('WGM'),'Category shown in detail');
 assert(!document.querySelector('#reportDetailBody script'),'Duty note remains plain text');
 assert(!document.querySelector('#reportDetailBody input'),'Detail view read-only');
 assert(!document.getElementById('reportPdf').disabled,'PDF available after loading');
 document.getElementById('reportClose').click();assert(!dialog.open,'Detail closes');
 assert(document.documentElement.scrollWidth<=innerWidth+1,'Page fits viewport');
 for(const control of document.querySelectorAll('#reportFilters input,#reportFilters select')){const rect=control.getBoundingClientRect();assert(rect.left>=0&&rect.right<=innerWidth+1,'Filters fit viewport');}
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')


if __name__=='__main__':
    runner.fixture=fixture
    runner.main()
