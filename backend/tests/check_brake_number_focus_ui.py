# Zugnummern bleiben beim Tippen lokal; die Prüfung beginnt nach dem Fokuswechsel.
import argparse,re
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from localized_fixtures import localize_html

def fixture(overlay=False):
    html=localize_html((STATIC/'brake-sheet.html').read_text())
    html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S)
    html=re.sub(r'<link\b[^>]*>','',html)
    source=(STATIC/'brake-sheet.js').read_text()
    source=re.sub(r'\}\)\(\);\s*$',"window.BrakeFocusFixture={collect,restore,preview,imported:()=>wagonImport={rows:[]}};})();",source)
    setup=r'''
localStorage.clear();window.I18n={t:s=>s,locale:'de-DE'};window.confirm=()=>true;
const errors=[];window.ReportFeedback={error:message=>errors.push(message)};
let calculations=0,holdNext=false,release=null;
const result={a:{},total:{},preview_missing:[]};
window.fetch=async(url,options={})=>{let data=[],status=200;
if(String(url).endsWith('/account/me'))data={id:7,role:'tf'};
else if(String(url).endsWith('/calculate')){calculations++;const sheet=JSON.parse(options.body);if(holdNext){holdNext=false;return await new Promise(resolve=>release=()=>resolve(new Response(JSON.stringify({detail:'Zugnummer unvollständig'}),{status:422})));}if(sheet.train_numbers.some(n=>n&&!/^\d{5}$/.test(n))){data={detail:'Zugnummer unvollständig'};status=422;}else data=result;}
return new Response(JSON.stringify(data),{status});};
'''
    if overlay:setup="history.replaceState(null,'','/tf/bremszettel?overlay=journey-a&train=00123');"+setup
    checks=r'''
(async()=>{const assert=(v,m)=>{if(!v)throw Error(m);},wait=ms=>new Promise(r=>setTimeout(r,ms)),until=async test=>{const end=Date.now()+10000;while(!test()){if(Date.now()>end)throw Error('Timeout');await wait(20);}},el=id=>document.getElementById(id);
await until(()=>window.BrakeFocusFixture&&document.querySelectorAll('#trainNumbers input').length===2&&calculations===1);
const api=BrakeFocusFixture,initial=api.collect();assert(initial.countries[0].country==='DE'&&initial.countries[0].category==='G','First column defaults to DE/G');assert(initial.countries[1].country==='PL'&&initial.countries[1].category==='G','Second column receives the PL/G preset');assert(initial.countries[0].vmax===100&&initial.countries[1].vmax===100&&initial.class_de==='D4'&&initial.class_pl==='D'&&initial.required_percent===59,'Matching existing freight defaults are complete');
api.imported();const field=document.querySelector('#trainNumbers input');field.focus();const before=calculations;
for(const value of ['1','12','123']){field.value=value;field.dispatchEvent(new Event('input',{bubbles:true}));await wait(360);assert(calculations===before&&errors.length===0,'No calculation or popup interrupts an incomplete train number');}
const saved=JSON.parse(localStorage.getItem([...Object.keys(localStorage)].find(k=>k.startsWith('lokzeitleiste.brake-sheet.'))));assert(saved.sheet.train_numbers[0]==='123','Incomplete input is still retained in the local draft');
el('remarks').focus();await until(()=>errors.length===1);assert(calculations===before+1,'Leaving an incomplete number performs one debounced check');
field.focus();for(const value of ['1234','12345']){field.value=value;field.dispatchEvent(new Event('input',{bubbles:true}));await wait(360);assert(errors.length===1,'Completing the train number causes no further popup while typing');}
el('remarks').focus();const completed=calculations;await until(()=>calculations>completed);assert(errors.length===1,'Complete number passes after focus changes');
// Auch eine zuvor gestartete Serverantwort darf beim Tippen keine verspätete Fehlermeldung öffnen.
holdNext=true;api.preview();await until(()=>release);field.focus();field.value='2';field.dispatchEvent(new Event('input',{bubbles:true}));release();await wait(360);assert(errors.length===1,'Old asynchronous errors are ignored while editing a train number');field.value='23456';field.dispatchEvent(new Event('input',{bubbles:true}));el('remarks').focus();await wait(360);
const custom=api.collect();custom.countries[0]={country:'PL',category:'P',vmax:90};custom.countries[1]={country:'DE',category:'P',vmax:80};custom.class_de='D3';custom.class_pl='C';custom.required_percent=75;api.restore(custom);const restored=api.collect();assert(restored.countries[0].country==='PL'&&restored.countries[1].category==='P'&&restored.class_de==='D3'&&restored.required_percent===75,'Loading a saved sheet preserves manual values');
el('brakeNew').click();await until(()=>api.collect().countries[0].country==='DE');assert(api.collect().countries[1].country==='PL'&&api.collect().required_percent===59,'A newly created sheet restores the requested defaults');
parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    scripts=''.join('<script>'+value+'</script>' for value in [setup,(STATIC/'messages.js').read_text(),source,checks])
    return html.replace('</body>',scripts+'</body>')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    for overlay in (False,True):check_pages(lambda:fixture(overlay),args.output_dir+('/overlay' if overlay else '/module'),widths=(800,375),label='Brake number focus '+('overlay' if overlay else 'module'),timeout=35)
