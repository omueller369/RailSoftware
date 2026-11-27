# Unvollständige lokale Berichte drucken, ohne Validierung, Versand oder Änderungen am Entwurf.
import argparse,re,time,base64
from pathlib import Path
from browser_realtime import check_pages
from check_field_error_navigation_ui import shell
from check_work_report_layout import STATIC

def fixture(native=False):
    source=(STATIC/'work-report.js').read_text().split('// Die Klappschalter')[0]
    export='''window.PreviewFixture={setup(){user={id:7,first_name:'Test',last_name:'Tf',username:'787000'};state={client_id:'preview-only',kind:'Sonstige Erfassung',ausbleibe:['8h'],legacy_pause:0};trips=[];trainEditor={draft:()=>[{id:'j1',train_number:'',rotation_name:'<script>evil()</script>',start_station:'AAA',end_station:'',start_at:'2026-11-27T10:00',end_at:'2026-11-27T09:00',events:[{cause:'DB-InfraGo',reason:'Historischer Wert',station:'BBB',start_at:'2026-11-27T10:00',end_at:''}]}],items:[{id:'j1'}],captureEditing:()=>[{id:'j1',eventFields:{cause:'CTL',reason:'Noch nicht eingetragen',station:'CC',start_at:'',end_at:''}}],pendingEvent:()=>true};el('dutyStart').value='2026-11-27T08:00';el('dutyEnd').value='';el('guestFrom').value='Angefangene Gastfahrt';el('guestTo').value='';el('guestTransport').value='train';reportFields(true);}};})();'''
    source=re.sub(r'\}\)\(\);\s*$',lambda _:export,source)
    setup=r'''
localStorage.clear();localStorage.setItem('unchanged-draft','original');let writes=0,printed=0,nativeJob=null;
window.I18n={t:s=>s,locale:'de-DE'};window.fetch=()=>{writes++;throw Error('Preview must not use the network');};window.print=()=>{printed++;};
'''
    if native:setup+="window.AndroidPortal={printReport:async value=>{nativeJob=value;}};"
    checks=r'''
(async()=>{const assert=(v,m)=>{if(!v)throw Error(m);},el=id=>document.getElementById(id);
el('workReport').hidden=false;PreviewFixture.setup();const before=JSON.stringify(localStorage);const raw=el('dutyEnd').value;
window.openWorkReportPreview();const dialog=el('reportPreviewDialog'),article=el('reportPreviewContent');assert(dialog.open,'Preview opens for incomplete report');
assert(article.textContent.includes('ENTWURF')&&article.textContent.includes('fehlt'),'Draft and missing information are explicit');assert(article.textContent.includes('27.11.2026 09:00'),'Inconsistent time is displayed unchanged');assert(article.textContent.includes('Historischer Wert'),'Stale choices do not block preview');assert(article.textContent.includes('Noch nicht eingetragen')&&article.textContent.includes('Angefangene Gastfahrt'),'Unentered event and guest editor values are included');assert(!article.querySelector('script')&&article.textContent.includes('<script>'),'Personal text cannot execute HTML');
assert(!writes&&JSON.stringify(localStorage)===before&&el('dutyEnd').value===raw,'Preview never writes, sends or repairs input');
const print=dialog.querySelectorAll('button')[1];print.click();await new Promise(r=>setTimeout(r,20));
if(window.AndroidPortal){assert(nativeJob&&nativeJob.text===article.textContent,'Native printer receives this report only');assert(!document.body.classList.contains('report-preview-printing'),'Android uses its own isolated print WebView');}
else{assert(printed===1&&document.body.classList.contains('report-preview-printing'),'Browser printing is isolated');window.dispatchEvent(new Event('afterprint'));assert(!document.body.classList.contains('report-preview-printing'),'Print state is cleaned after printing');}
dialog.querySelector('button').click();for(let i=0;el('reportPreviewDialog')&&i<100;i++)await new Promise(r=>setTimeout(r,20));assert(!el('reportPreviewDialog'),'Closing removes the report snapshot');assert(!writes&&JSON.stringify(localStorage)===before,'Printing and closing leave the draft unchanged');
// Eine lange Schichtvorschau darf beim PDF-Druck nicht auf eine Dialoghöhe abgeschnitten werden.
const report={start_at:'',end_at:'',trips:[],train_journeys:Array.from({length:25},(_,i)=>({id:'long-'+i,train_number:String(i),events:[{reason:i===24?'LAST_EVENT_TOKEN':'Normal',station:'BBB'}]}))};ReportPreview.open({owner:{first_name:'Test'},report,editors:[]});
if(!window.AndroidPortal)el('reportPreviewDialog').querySelectorAll('button')[1].click();
window.previewReady=true;document.documentElement.dataset.layoutStatus='pass';parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>{document.documentElement.dataset.layoutStatus='fail';document.documentElement.dataset.layoutMessage=error.stack;parent.postMessage({layoutStatus:'fail',message:error.stack},'*');});
'''
    return shell().replace('</body>','<script>'+setup+'\n'+ '\n'.join((STATIC/n).read_text() for n in ['messages.js','report-tabs.js','report-preview.js'])+'\n'+source.replace('</script','<\\/script')+'\n'+checks+'</script></body>')

def printer(output):
    def interact(client,width):
        # Direkt die Testseite aufrufen, damit der PDF-Druck keinen begrenzten iframe abbildet.
        deadline=time.monotonic()+10
        url=None
        while time.monotonic()<deadline:
            url=client.evaluate("document.querySelector('iframe')?.src")
            if url:break
            time.sleep(.05)
        client.call('Page.navigate',dict(url=url));client.call('Emulation.setDeviceMetricsOverride',dict(width=width,height=1200,deviceScaleFactor=1,mobile=False))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if client.evaluate('window.previewReady'):break
            if client.evaluate("document.documentElement.dataset.layoutStatus==='fail'"):return
            time.sleep(.05)
        assert client.evaluate('window.previewReady'),client.evaluate('document.documentElement.dataset.layoutMessage') or 'Preview did not finish'
        client.call('Emulation.setEmulatedMedia',dict(media='print'))
        assert client.evaluate("getComputedStyle(document.querySelector('main')).display==='none'"),'Form and portal must not be printed'
        data=client.call('Page.printToPDF',dict(printBackground=True,preferCSSPageSize=True));path=Path(output)/f'preview-{width}.pdf';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(data['data']))
        from pypdf import PdfReader
        reader=PdfReader(path);text='\n'.join(p.extract_text() for p in reader.pages)
        assert len(reader.pages)>1 and 'LAST_EVENT_TOKEN' in text,'Every page of the long draft must be present'
        assert 'unchanged-draft' not in text
    return interact

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()
    check_pages(fixture,a.output_dir+'/web',widths=(800,320),label='Incomplete report preview and PDF',interact=printer(a.output_dir))
    check_pages(lambda:fixture(True),a.output_dir+'/android',widths=(800,320),label='Android report preview')
