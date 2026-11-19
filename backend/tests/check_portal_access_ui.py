"""Real DOM: six requested columns, safe employee text, failed refresh and recovery."""
import re
from localized_fixtures import localize_html
from check_work_report_layout import STATIC


def fixture():
    page=localize_html((STATIC/'portal-access.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    setup='''let fail=false;window.fetch=async()=>({ok:!fail,json:async()=>[{tf_number:'787117',last_name:'<img src=x onerror=alert(1)>',first_name:'Oliver',date:'19.11.2026',time:'12:34:56',android_version:'0.27.13.17'}]});'''
    checks='''(async()=>{const wait=()=>new Promise(r=>setTimeout(r,25)),assert=(v,m)=>{if(!v)throw Error(m);};await wait();const table=document.querySelector('table'),body=document.getElementById('accessRows');assert(table.querySelectorAll('th').length===6,'Six requested columns');assert(body.rows.length===1&&body.rows[0].cells.length===6,'Loaded employee row');assert(body.rows[0].cells[0].textContent==='787117','TF number shown');assert(!body.querySelector('img'),'Employee text cannot inject HTML');assert(body.rows[0].cells[3].textContent==='19.11.2026'&&body.rows[0].cells[5].textContent==='0.27.13.17','German date and Android version shown');fail=true;document.getElementById('refresh').click();await wait();assert(document.getElementById('status').textContent&&!document.getElementById('refresh').disabled,'Failure feedback and retry available');fail=false;document.getElementById('refresh').click();await wait();assert(!document.getElementById('status').textContent&&body.rows.length===1,'Successful retry replaces rows');window.parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));'''
    scripts=(STATIC/'messages.js').read_text()+setup+(STATIC/'portal-access.js').read_text()+checks
    return page.replace('</body>','<script>'+scripts+'</script></body>')


if __name__=='__main__':
    import argparse
    from browser_realtime import check_pages
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    check_pages(fixture,args.output_dir,widths=(1280,800,375),label='Portal access')
