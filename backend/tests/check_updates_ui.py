"""Browser checks for the update module, including native availability and GPS guards."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html

def fixture():
    page=localize_html((runner.STATIC/'tf-portal.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css'])
    scripts='\n'.join((runner.STATIC/name).read_text() for name in ['messages.js','updates.js'])
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 document.getElementById('updatesModule').hidden=false;
 const state={version:'0.26.45-test.13',available:false,checking:false,gps_running:false};
 window.fetch=async()=>({ok:true,json:async()=>({version:'0.26.46'})});
 const calls=[];window.AndroidPortal={request:async method=>{calls.push(method);if(method==='updates.check')state.available=true;return {...state};}};
 await window.startUpdates();const root=document.getElementById('updatesWorkspace'),[check,install]=root.querySelectorAll('button');
 assert(install.hidden,'Install hidden until update is ready');await check.onclick();assert(!install.hidden,'Verified update can be installed');
 assert(root.textContent.includes('0.26.45-test.13')&&root.textContent.includes('0.26.46'),'Separate native and web versions');
 assert(root.querySelectorAll('li').length===6,'Recent version history');
 state.gps_running=true;await new Promise(resolve=>setTimeout(resolve,1100));assert(check.disabled&&install.disabled,'No update installation during GPS');
 state.gps_running=false;await new Promise(resolve=>setTimeout(resolve,1100));assert(!check.disabled&&!install.disabled,'Update usable after GPS ends');
 for(const control of root.querySelectorAll('button,a')){if(control.hidden)continue;const box=control.getBoundingClientRect();assert(box.left>=0&&box.right<=innerWidth+1,'Controls fit viewport');}
 assert(calls.every(method=>method.startsWith('updates.')),'No GPS or report writes');
 document.documentElement.dataset.layoutStatus='pass';window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    runner.fixture=fixture
    runner.main()
