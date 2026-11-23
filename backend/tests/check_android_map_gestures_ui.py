# Browserprüfung für Kartenbedienung und Bildausschnitte.
"""Chrome-generated two-finger events on the real Android map renderers at 4x CPU slowdown."""
import argparse,json,time
from browser_realtime import check_pages
from check_work_report_layout import STATIC
ASSETS=['messages.js','map-gestures.js','station-catalog-data.js','m1-basemap-data.js','rail-network-data.js','rail-network.js','m1-map.js','station-picker.js','route-imports.js','route-coverage.js','route-table.js','route-editor.js','route-knowledge.js','gps.js','train-workspace.js']
def fixture():
    css='\n'.join((STATIC/name).read_text() for name in ['tf-portal.css','work-report.css','responsive.css','portal-theme.css'])
    setup=r'''
Object.defineProperty(navigator,'onLine',{get:()=>false});window.I18n={t:s=>s};let nativeCalls=0;window.AndroidPortal={gps:async()=>{nativeCalls++;return {running:false,points:[],paused:false};},request:async()=>({})};window.confirm=()=>true;
window.fetch=async url=>new Response(JSON.stringify({owner_id:1,items:[],next_offset:null}),{status:String(url).includes('/gps/')?404:200,headers:{'Content-Type':'application/json'}});
'''
    checks=r'''
(async()=>{
 const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const manualHost=document.getElementById('manual'),manual=ManualRouteEditor.mount({id:1},manualHost,async()=>{});await M1Map.load();await wait(100);manual.select(M1Map.points().byCode.get('AFW')[0],true);manual.select(M1Map.points().byCode.get('AFR')[0]);
 await startRouteKnowledge({id:1},{administration:true,fetch:window.fetch,errorLabel:()=>''});
 const points=Array.from({length:10800},(_,i)=>({t:1795165200000+i*1000,lat:52,lon:13+i*.00001,accuracy:5,speed:10})),raw=JSON.stringify(points),recorders={};
 for(const demo of [false,true]){const name=demo?'demo':'gps',recorder=GpsRecorder.mount({userId:1,journeyId:name,container:document.getElementById(name),demo,trainNumber:()=>name,readonly:()=>true,now:()=>points.at(-1).t});await recorder.readyPromise;recorder.record={train_number:name,ended:true,points:structuredClone(points),manual_stops:[],stop_edits:{}};recorder.m1Data=RailNetworkSeed;recorder.mapState={mode:'free',zoom:12,center:M1Map.project({lat:52,lon:13.04})};recorder.setExpanded(true);recorders[name]=recorder;}
 const maps={manual:manualHost.querySelector('.manual-route-map'),knowledge:document.querySelector('#routeKnowledgeWorkspace .route-knowledge-map'),gps:recorders.gps.map,demo:recorders.demo.map};let selected=null,draws=0,full=false,row=null;
 const originals=new Map(Object.values(maps).map(map=>[map,map.replaceChildren.bind(map)]));for(const map of Object.values(maps))map.replaceChildren=(...children)=>{if(map===selected)draws++;return originals.get(map)(...children);};
 window.GestureHarness={ready:true,prepare(name){if(full){TrainWorkspace.fullscreen(recorders.gps);full=false;}for(const section of document.querySelectorAll('body>section'))section.hidden=true;const target=name==='full'?'gps':name;document.getElementById(target==='knowledge'?'knowledge':target).hidden=false;selected=maps[target];if(name==='full'){TrainWorkspace.fullscreen(recorders.gps);full=true;}draws=0;row=manualHost.querySelector('[data-route-waypoint]');window.scrollTo(0,0);const svg=selected.querySelector('svg'),r=svg.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,view:MapGestures.mount(selected,{}).view};},state(){return {draws,active:MapGestures.mount(selected,{}).active,view:MapGestures.mount(selected,{}).view,transform:selected.querySelector('svg').style.transform,waypoints:manual.waypoints.join(','),rowRetained:row===manualHost.querySelector('[data-route-waypoint]'),rawUnchanged:Object.values(recorders).every(r=>JSON.stringify(r.record.points)===raw),pageScale:visualViewport.scale};},backgroundUpdate(){for(const recorder of Object.values(recorders))if(recorder.map===selected)for(let i=0;i<3;i++)recorder.drawMap();},tapPoint(){const p=manualHost.querySelector('[data-m1-point=AFW]').getScreenCTM();return {x:p.e,y:p.f};},undo(){manualHost.querySelector('[data-route-map-undo]').click();},finish(){if(full)TrainWorkspace.fullscreen(recorders.gps);parent.postMessage({layoutStatus:'pass'},'*');}};
})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'body{margin:0}body>section{padding:8px;box-sizing:border-box}</style></head><body><section id="manual"></section><section id="knowledge"><div id="routeKnowledgeWorkspace"></div></section><section id="gps"></section><section id="demo"></section><script>'+setup+'</script>'+''.join('<script src="/tf/'+name+'"></script>' for name in ASSETS)+'<script>'+checks+'</script></body></html>'

def interact(client,width):
    prefix="document.querySelector('iframe').contentWindow"
    deadline=time.monotonic()+40
    while not client.evaluate(prefix+'.GestureHarness?.ready'):
        if time.monotonic()>deadline:raise AssertionError('Gesture fixture did not initialize')
        time.sleep(.05)
    client.call('Emulation.setTouchEmulationEnabled',dict(enabled=True,maxTouchPoints=2))
    def state():return client.evaluate(prefix+'.GestureHarness.state()')
    for name in ['manual','knowledge','gps','demo','full']:
        view=client.evaluate(prefix+'.GestureHarness.prepare('+json.dumps(name)+')');x,y=view['x'],view['y'];zoom=view['view']['zoom']
        def touch(kind,distance):
            points=[] if kind in ('touchEnd','touchCancel') else [dict(id=i+1,x=x+sign*distance/2,y=y,radiusX=4,radiusY=4,force=1) for i,sign in enumerate([-1,1])]
            client.call('Input.dispatchTouchEvent',dict(type=kind,touchPoints=points))
        # Echte, zeitversetzte Berührungen lösen die implizite SVG-Erfassung aus.
        # Gleichzeitiges Aufsetzen allein deckt deren Übergabe nicht zuverlässig ab.
        def fingers(kind,positions):
            client.call('Input.dispatchTouchEvent',dict(type=kind,touchPoints=[dict(id=i,x=px,y=py,radiusX=4,radiusY=4,force=1) for i,px,py in positions]))
        time.sleep(.15)
        before=state()['view']
        fingers('touchStart',[(1,x,y)]);time.sleep(.06)
        fingers('touchMove',[(1,x+40,y+30)]);time.sleep(.06)
        fingers('touchMove',[(1,x+70,y+50)]);time.sleep(.06)
        fingers('touchEnd',[]);time.sleep(.1)
        single=state()['view']
        assert single['center']['x']<before['center']['x'] and single['center']['y']<before['center']['y'],(name,'One real finger commits pan after capture transfer',before,single)
        assert single['zoom']==before['zoom'],(name,'One finger never changes zoom')
        fingers('touchStart',[(1,x-70,y)]);time.sleep(.06)
        fingers('touchStart',[(1,x-70,y),(2,x+70,y)]);time.sleep(.06)
        fingers('touchMove',[(1,x-30,y+35),(2,x+110,y+35)]);time.sleep(.06)
        fingers('touchEnd',[(2,x+110,y+35)]);time.sleep(.06)
        fingers('touchMove',[(2,x+145,y+65)]);time.sleep(.06)
        fingers('touchEnd',[]);time.sleep(.1)
        paired=state()['view']
        assert paired['center']['x']<single['center']['x'] and paired['center']['y']<single['center']['y'],(name,'Staggered two-finger pan commits and continues with remaining finger',single,paired)
        assert abs(paired['zoom']-single['zoom'])<.01,(name,'Parallel two-finger pan retains zoom')
        client.evaluate(prefix+'.GestureHarness.prepare('+json.dumps(name)+')')
        touch('touchStart',140)
        for distance in range(150,261,10):touch('touchMove',distance)
        client.evaluate(prefix+'.GestureHarness.backgroundUpdate()')
        during=state();assert during['active'] and during['draws']==0,(name,'No full redraw during finger movement',during)
        touch('touchEnd',0);deadline=time.monotonic()+3
        while state()['draws']==0 and time.monotonic()<deadline:time.sleep(.02)
        after=state();assert after['view']['zoom']>zoom+.5,(name,'Pinch out zooms in',after)
        assert after['draws']==1 and after['pageScale']==1,(name,'One map commit, no page zoom',after)
        touch('touchStart',260);touch('touchMove',130);touch('touchEnd',0);time.sleep(.04);back=state();assert back['view']['zoom']<after['view']['zoom']-.5,(name,'Pinch inward zooms out')
        assert back['waypoints']=='AFW,AFR' and back['rawUnchanged'],(name,'Neither route selection nor 10,800 original GPS fixes changes')
        if name=='manual':assert back['rowRetained'],'Zoom does not rebuild the route table'
        before=back['view'];touch('touchStart',200);touch('touchMove',240);touch('touchCancel',0);assert state()['view']==before,(name,'Cancellation keeps last committed view')
        if name=='manual':
            time.sleep(.7)
            point=client.evaluate(prefix+'.GestureHarness.tapPoint()')
            client.call('Input.dispatchTouchEvent',dict(type='touchStart',touchPoints=[dict(id=1,**point,radiusX=4,radiusY=4,force=1)]));client.call('Input.dispatchTouchEvent',dict(type='touchEnd',touchPoints=[]))
            assert state()['waypoints']=='AFW,AFR,AFW','A real finger tap still selects an operating point'
            client.evaluate(prefix+'.GestureHarness.undo()');assert state()['waypoints']=='AFW,AFR'
        print(f'{name}: one-/two-finger pan with capture transfer; two-finger zoom both ways; zero full redraws during movement; one commit; unchanged data',flush=True)
    client.evaluate(prefix+'.GestureHarness.finish()')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,widths=(800,375),assets={'/tf/'+name:STATIC/name for name in ASSETS},label='Android map gestures',cpu_rate=4,timeout=40,interact=interact)
