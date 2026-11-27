from pathlib import Path
import argparse
import json
# Browserprüfung für Versionsprüfung und bestehende Installationen.
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
 assert(root.querySelectorAll('li').length===CtlReleaseHistory.length,'Complete version history');
 state.gps_running=true;await new Promise(resolve=>setTimeout(resolve,1100));assert(check.disabled&&install.disabled,'No update installation during GPS');
 state.gps_running=false;await new Promise(resolve=>setTimeout(resolve,1100));assert(!check.disabled&&!install.disabled,'Update usable after GPS ends');
 for(const control of root.querySelectorAll('button,a')){if(control.hidden)continue;const box=control.getBoundingClientRect();assert(box.left>=0&&box.right<=innerWidth+1,'Controls fit viewport');}
 assert(calls.every(method=>method.startsWith('updates.')),'No GPS or report writes');
 // Auch nachträglich hinzugefügte Kacheln müssen vor Updates landen.
 const updateTile=document.querySelector('a.module[href="/tf/updates"]');
 const code=__TILE_CODE__;
 const prepare=new Function('updateTile',code);prepare(updateTile);
 const list=updateTile.parentElement,extra=document.createElement('a');extra.className='module';list.append(extra);
 await new Promise(resolve=>setTimeout(resolve,50));assert(list.lastElementChild===updateTile,'Updates stays last after adding modules');
 assert(!updateTile.hidden,'Updates visible in Android');delete window.AndroidPortal;prepare(updateTile);assert(updateTile.hidden,'Updates hidden on web');
 const first=root.querySelector('li span'),original=first.textContent;
 window.I18n={t:source=>{const key=CtlReleaseHistory.find(row=>CtlText.source(row.key)===source)?.key;return key?CtlText.text(key,{},'pl'):source;}};
 window.dispatchEvent(new Event('languagechange'));assert(first.textContent!==original,'History changes language');
 window.fetch=async()=>{throw Error('offline');};await startUpdates();assert(root.querySelectorAll('li').length===CtlReleaseHistory.length,'History available offline');
 document.documentElement.dataset.layoutStatus='pass';window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    portal=(runner.STATIC/'tf-portal.js').read_text()
    tile_code=portal.split('if(updateTile){',1)[1].split('await window.GpsDemoVisibility',1)[0].rsplit('}',1)[0]
    checks=checks.replace('__TILE_CODE__',json.dumps(tile_code))
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')

if __name__=='__main__':
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,default=Path('/tmp/rail-updates-ui'))
    args=parser.parse_args()
    check_pages(fixture,args.output_dir,widths=(800,375,320),label='Updates')
