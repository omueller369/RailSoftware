"""Browser checks for account-scoped tile visibility and saving failures."""
import json
import check_work_report_layout as runner

def fixture():
    messages=(runner.STATIC/'messages.js').read_text();script=(runner.STATIC/'gps-demo-visibility.js').read_text()
    before=r'''
 history.replaceState(null,'','/tf/me');let hidden=true,fail=false,viewer=1,requests=[];
 window.fetch=async(url,options={})=>{requests.push([String(url),options.method||'GET']);if(String(url).endsWith('/account/me'))return {ok:true,json:async()=>({id:viewer,role:'tf'})};if(options.method==='PUT'){if(fail)return {ok:false};hidden=JSON.parse(options.body).hidden;}return {ok:true,json:async()=>({owner_id:viewer,hidden})};};
'''
    after=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};for(let i=0;i<50&&!document.querySelector('#profileGpsDemoVisibility input:not(:disabled)');i++)await new Promise(resolve=>setTimeout(resolve,10));
 const check=document.querySelector('#profileGpsDemoVisibility input'),tile=document.querySelector('a.module');assert(check&&!check.checked,'Hidden tile can be restored under My account');check.checked=true;await check.onchange();assert(!hidden&&localStorage.getItem('railsoftware.gps-demo-hidden.1')==='false','Restoring tile saves own account preference');await GpsDemoVisibility.apply(1);assert(!tile.hidden,'Restored tile appears');await GpsDemoVisibility.set(1,true);assert(tile.hidden,'Hide takes effect');viewer=2;hidden=false;await GpsDemoVisibility.apply(2);assert(!tile.hidden,'Visibility does not leak between accounts');fail=true;let rejected=false;try{await GpsDemoVisibility.set(2,true);}catch(error){rejected=true;}assert(rejected&&!tile.hidden,'Failed save does not pretend tile was hidden');
 document.documentElement.dataset.layoutStatus='pass';parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    return '<!doctype html><html><head><meta charset="utf-8"><style>main{max-width:100%;overflow-wrap:anywhere}label{display:flex;gap:.5rem}</style></head><body><main><a class="module" href="/tf/gps-demo">GPS-DEMO</a></main><script>'+messages+before+script+after+'</script></body></html>'
if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,label='GPS demo visibility')
