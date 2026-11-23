# Browserprüfung für Berichte und die zugehörigen Prüf- und Versandabläufe.
"""Actual report finalization queues offline, then retries only the explicitly selected report."""
import re
from pathlib import Path
from browser_realtime import check_pages
from check_work_report_layout import STATIC
from check_android_report_navigation_ui import fixture as base_fixture

def fixture():
    page=base_fixture(False)
    page=page.replace("let attempts=0,uploads=0,stored=null,cloud={};","let attempts=0,uploads=0,stored=null,cloud={},connected=false;")
    page=page.replace("app_version:'test',account:","online:false,app_version:'0.28.0.2',account:")
    page=page.replace("window.fetch=async(url,options={})=>{url=String(url);", "window.fetch=async(url,options={})=>{if(!connected)throw TypeError('Network offline');url=String(url);")
    page=page.replace('/* Android-only adapters.',(STATIC/'android-offline.js').read_text()+'\n/* Android-only adapters.',1)
    source=(STATIC/'work-report.js').read_text();a=source.index('if(window.AndroidPortal?.offline)window.AndroidPortal.offline.registerReports(');z=source.index('\n',a);register=source[a:z]
    page=page.replace('window.NavFixture={loadReport,','window.NavFixture={enableAndroid(){'+register+'},loadReport,',1)
    start=page.index(" const a=report(");end=page.index("parent.postMessage({layoutStatus:'pass'}",start)
    checks=r'''
 const a=report(crypto.randomUUID(),'2026-11-18','111','CTL'),b=report(crypto.randomUUID(),'2026-11-17','222','CTL');
 const editor=new TrainJourneyEditor({userId:7,container:el('trainJourneyEditor'),button:el('newTrainJourney'),readonly:()=>NavFixture.readonly(),viewOnly:()=>NavFixture.readonly(),bounds:()=>({start:el('dutyStart').value,end:el('dutyEnd').value}),minute:value=>Date.parse(value)/60000,clock:String,uuid:()=>crypto.randomUUID(),stations(){},resolve:async input=>({code:input.value.split(' · ')[0],name:'Bahnhof'}),changed(){NavFixture.storeDraft();},editingChanged(){NavFixture.storeDraft();},message:value=>ReportFeedback.error(value),block(){}});
 await wait();NavFixture.setup(editor,[a,b]);await NavFixture.loadReport(a.client_id,true);NavFixture.enableAndroid();
 await NavFixture.synchronize([b.client_id]);assert(attempts===0&&uploads===0,'Offline synchronize does not attempt or pretend to send');assert(NavFixture.rows().some(row=>row.client_id===b.client_id),'Confirmed report remains on this device');assert([...Array(localStorage.length)].some((_,i)=>localStorage.key(i).startsWith('railsoftware.android.send-intents.')),'Explicit send intent survives document restart');
 connected=true;AndroidPortal.setOnline(true);await until(()=>uploads===1&&!NavFixture.rows().some(row=>row.client_id===b.client_id));assert(attempts===1,'Reconnect finalizes exactly once');assert(NavFixture.rows().some(row=>row.client_id===a.client_id),'Unconfirmed report stays a draft');assert(stored.client_id===b.client_id&&NavFixture.state().client_id===a.client_id,'Only selected report is sent without replacing open draft');
 '''
    return page[:start]+checks+page[end:]
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args();check_pages(fixture,args.output_dir,widths=(800,375),label='Android offline report queue',timeout=30)
