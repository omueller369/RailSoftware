"""Actual browser multipart -> authenticated FastAPI -> database import round trip."""
import argparse,base64,http.server,json,threading
from pathlib import Path
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from test_route_knowledge_import import RouteKnowledgeImportTest,csv_bytes,ROWS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);parser.add_argument('--source',type=Path);args=parser.parse_args()
    # An optional private source is read locally only, never included in repository assets.
    raw=args.source.read_bytes() if args.source else csv_bytes([[f'Strecke {i}',str(i+1),'streckenkundig','2027-12-31','-','-','AAA','BBB'] for i in range(2013)])
    case=RouteKnowledgeImportTest();case.setUp()
    class Proxy(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_OPTIONS(self):
            self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Content-Type');self.end_headers()
        def forward(self):
            if not self.path.startswith('/api/v1/tf/route-knowledge/imports'):self.send_error(404);return
            body=self.rfile.read(int(self.headers.get('Content-Length',0)))
            response=case.driver.request(self.command,self.path,content=body,headers={'Content-Type':self.headers.get('Content-Type','application/octet-stream')})
            self.send_response(response.status_code);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(response.content)
        do_POST=do_GET=forward
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Proxy);threading.Thread(target=server.serve_forever,daemon=True).start()
    def fixture():
        config='const origin='+json.dumps('http://127.0.0.1:'+str(server.server_address[1]))+',encoded='+json.dumps(base64.b64encode(raw).decode())+',owner='+str(case.tf)+';'
        scripts='\n'.join((STATIC/name).read_text() for name in ['messages.js','route-csv.js'])
        checks=r'''
(async()=>{const assert=(ok,msg)=>{if(!ok)throw Error(msg);};const original=window.fetch.bind(window);window.fetch=(url,options)=>original(origin+url,options);const root=document.getElementById('csv');await RouteCsv.mount({id:owner},root);const file=root.querySelector('input[type=file]'),transfer=new DataTransfer();transfer.items.add(new File([Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))],'Kenntnisse.csv',{type:'text/csv'}));file.files=transfer.files;await file.onchange();const preview=root.querySelector('[data-route-csv-preview]');assert(!preview.hidden,'Actual multipart preview succeeded');assert(preview.textContent.includes('787100'),'Authenticated TF identity in preview');const apply=root.querySelector('[data-route-csv-apply]');assert(!apply.disabled,'Confirmed import enabled');await apply.onclick();assert(root.querySelectorAll('tbody tr').length===100,'First 100 private entries returned from actual DB');assert((await RouteCsv.cache(owner)).items.length===2013,'All 2013 rows cached privately');parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
        return '<!doctype html><meta charset="utf-8"><section id="csv"></section><script>'+config+scripts+checks+'</script>'
    try:
        check_pages(fixture,args.output_dir,widths=(800,),label='CSV actual server round trip')
        assert case.counts()==(2013,1,0),case.counts()
        print('2013 entries stored once, no GPS records created: PASS')
    finally:server.shutdown();server.server_close();case.tearDown()
if __name__=='__main__':main()
