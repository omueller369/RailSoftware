# Die sichtbare PDF-Vorschau und der Download verwenden die Bytes des offiziellen Renderers.
import argparse,json,re,io,base64
from pathlib import Path
from browser_realtime import check_pages
from check_field_error_navigation_ui import shell
from check_work_report_layout import STATIC


def sample():
    import test_work_report_preview
    case=test_work_report_preview.WorkReportPreviewTest('test_bounds_and_invalid_shape');case.setUp()
    try:
        report=case.payload();report['train_journeys']=[{'id':'train-1','train_number':'12345','start_station':'BHF','end_station':'LL','start_at':report['start_at'],'end_at':report['end_at'],'events':[]}]
        report['train_journeys'].append({**report['train_journeys'][0],'id':'train-2','train_number':'67890'})
        response=case.preview(report);assert response.status_code==200,response.text
        return response.json(),report
    finally:case.tearDown();case.doCleanups()


def fixture(result,report,native=False):
    from pypdf import PdfReader
    expected_pages=len(PdfReader(io.BytesIO(base64.b64decode(result['pdf']))).pages)
    setup="const expectedPages="+str(expected_pages)+";window.I18n={t:s=>s,locale:'de-DE'};const expected="+json.dumps(result,ensure_ascii=False)+",report="+json.dumps(report,ensure_ascii=False)+";"
    setup+=r'''
let requests=0,printed=0,job=null,saved=null,download=null;const original=window.fetch.bind(window);
window.fetch=async(path,options={})=>{if(String(path).endsWith('/api/v1/tf/work-reports/preview')){requests++;return new Response(JSON.stringify(expected));}return original(path,options);};
window.print=()=>printed++;
const create=URL.createObjectURL.bind(URL);URL.createObjectURL=blob=>{download=blob;return create(blob);};document.addEventListener('click',event=>{if(event.target.matches('a[download]'))event.preventDefault();},true);
'''
    if native:setup+="window.AndroidPortal={printReportPdf:async value=>job=value,saveBlob:async(name,blob)=>{saved={blob,name};},printReport:async()=>{throw Error('Raw text printer must not handle a finished PDF');}};"
    checks=r'''
(async()=>{const assert=(v,m)=>{if(!v)throw Error(m);},until=async check=>{const end=Date.now()+20000;while(!check()){if(Date.now()>end)throw Error('PDF timeout: '+document.querySelector('#reportPreviewDialog [role=status]')?.textContent);await new Promise(r=>setTimeout(r,30));}};
ReportPreview.open({owner:{first_name:'Test',last_name:'Tf'},report,editors:[]});await until(()=>document.querySelectorAll('.report-pdf-page').length===expectedPages&&!document.querySelector('#reportPreviewDialog button:nth-last-child(1)').disabled);
const dialog=document.getElementById('reportPreviewDialog'),buttons=dialog.querySelectorAll('button');assert(requests===1,'Only the ephemeral rendering endpoint is used');assert(document.querySelectorAll('canvas').length===expectedPages&&expectedPages===2&&expected.layout.train_pages.length===2,'Two complete trains share the second PDF page');
buttons[2].click();await until(()=>saved||download);const blob=saved?.blob||download;const bytes=new Uint8Array(await blob.arrayBuffer());const encoded=btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));assert(encoded===expected.pdf,'Save PDF downloads the exact bytes from the final renderer');assert(blob.type==='application/pdf','Correct PDF media type');if(saved)assert(saved.name.endsWith('.pdf'),'Android uses a PDF filename');
buttons[1].click();await until(()=>job||printed);if(window.AndroidPortal)assert(job.pdf===expected.pdf&&job.pages===expectedPages,'Android prints the original PDF rather than rebuilding text');else assert(printed===1&&document.body.classList.contains('report-preview-printing'),'Browser prints the visible A4 PDF pages');
buttons[0].click();parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    source=(STATIC/'messages.js').read_text()+'\n'+(STATIC/'report-preview.js').read_text()
    return shell().replace('</body>','<script>'+setup+source+checks+'</script></body>')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();result,report=sample()
    assets={'/tf/la-vendor/'+str(path.relative_to(STATIC/'la-vendor')):path for path in (STATIC/'la-vendor').rglob('*') if path.is_file()}
    for native in [False,True]:check_pages(lambda:fixture(result,report,native),a.output_dir+('/android' if native else '/web'),widths=(800,320),assets=assets,label='Official PDF preview '+('Android' if native else 'web'),timeout=35)
