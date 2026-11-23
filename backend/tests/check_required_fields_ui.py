# Browserprüfung für Pflichtsterne, dynamische Formulare und die zeitliche Fehleranzeige.
import argparse
from pathlib import Path
from browser_realtime import check_pages
from check_work_report_layout import STATIC

def fixture():
    script=(STATIC/'auth-session.js').read_text()
    css=(STATIC/'portal-theme.css').read_text()
    tests=r'''
(async()=>{
 const wait=()=>new Promise(r=>setTimeout(r,40)),assert=(value,msg)=>{if(!value)throw Error(msg);},field=id=>document.getElementById(id),star=id=>field(id).closest('label').querySelectorAll('.ctl-required-mark');
 await wait();
 for(const id of ['name','email','conditional'])assert(star(id).length===1,'Exactly one star for '+id);
 assert(star('optional').length===0,'Optional input remains unmarked');
 assert(star('email')[0].parentElement.tagName==='SPAN','Star stays inside the caption span');
 assert(document.querySelector('#externalLabel .ctl-required-mark'),'Separate for-label marked');
 assert(document.querySelectorAll('form>.ctl-required-hint').length===1,'One explanation per form');
 const red=f=>getComputedStyle(f).borderTopColor==='rgb(196, 0, 0)';
 assert(!red(field('email'))&&!red(field('name')),'Untouched required inputs have neutral borders');
 field('email').value='wrong';field('email').dispatchEvent(new Event('input',{bubbles:true}));assert(red(field('email')),'Malformed typed email becomes red');
 assert(!red(field('name')),'Unrelated empty field remains neutral');
 field('email').value='test@example.org';field('email').dispatchEvent(new Event('input',{bubbles:true}));assert(!red(field('email')),'Correction removes error frame');
 field('form').reportValidity();assert(red(field('name')),'Missing value becomes red after attempted entry');
 field('name').value='Anna';field('name').dispatchEvent(new Event('input',{bubbles:true}));assert(!red(field('name')),'Missing value correction removes frame');
 field('conditional').required=false;await wait();assert(star('conditional').length===0,'Conditional requirement removed');
 field('conditional').required=true;await wait();assert(star('conditional').length===1,'Conditional requirement restored without duplication');
 const dynamic=document.createElement('label');dynamic.innerHTML='Dynamic<input required id="dynamic">';field('form').append(dynamic);await wait();assert(star('dynamic').length===1&&!red(field('dynamic')),'Late form row gets star without an error');
 dynamic.firstChild.textContent='Changed caption';await wait();assert(star('dynamic').length===1,'Caption changes preserve one star');
 field('form').reset();assert(!red(field('name')),'Reset clears validation feedback');
 window.I18n={t:value=>value==='* Pflichtfeld'?'* Required field':value};window.dispatchEvent(new Event('languagechange'));assert(document.querySelector('.ctl-required-hint').textContent==='* Required field','Explanation follows language');
 assert(document.querySelectorAll('#split .ctl-required-mark').length===1,'Split vehicle number uses one group caption');
 assert(!document.querySelector('#split .ctl-required-caption'),'Split number layout has no extra labels');
 parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return '<!doctype html><html><head><meta charset="utf-8"><style>input{border:1px solid #999}'+css+'</style></head><body><main><form id="form"><label>Name<input id="name" required></label><label><span>Email</span><input id="email" required type="email"></label><label>Conditional<input id="conditional" required></label><label>Optional<input id="optional"></label><label for="external" id="externalLabel">External</label><input id="external" required><div id="split"><label>Vehicle</label><div class="brake-number"><input required aria-label="Part 1"><input required aria-label="Part 2"></div></div><button>Save</button></form></main><script src="/tf/messages.js"></script><script>window.AndroidPortal={};window.fetch=async()=>new Response("{}");</script><script>'+script+'</script><script>'+tests+'</script></body></html>'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args();check_pages(fixture,args.output_dir,widths=(800,375),assets={'/tf/messages.js':STATIC/'messages.js'},label='Required field indicators',timeout=20)
