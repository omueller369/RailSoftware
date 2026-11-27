# Die Vorschau liest Rohwerte, ohne die Fachprüfung zu lockern oder Datensätze anzulegen.
import json,base64,math
from datetime import datetime
from types import SimpleNamespace
from fastapi import HTTPException
from ..localization import source

TEXT_FIELDS=('start_at','end_at','kind','hotel_name','hotel_location','overrun_reason','train_number','rotation_name','start_station','start_station_name','end_station','end_station_name','station','station_name','reason','cause','reason_detail','cause_detail','transport','transport_detail','id')
def parsed(value):
    try:
        result=datetime.fromisoformat(value)
        return result if result.tzinfo is None else None
    except (TypeError,ValueError):return None

def duration(start,end):
    a,b=parsed(start),parsed(end)
    return int((b-a).total_seconds()//60) if a and b and b>=a else None

def preview_metrics(db,user,data):
    from ..reports.absence import is_rest_day
    start,end=parsed(data['start_at']),parsed(data['end_at']);elapsed=duration(data['start_at'],data['end_at'])
    spans=[duration(t['start_at'],t['end_at']) for t in data['trips']]
    total=sum(spans) if all(v is not None for v in spans) else None
    inside=sum(max(0,int((min(end,parsed(t['end_at']))-max(start,parsed(t['start_at']))).total_seconds()//60)) for t in data['trips']) if elapsed is not None and total is not None else None
    credited=elapsed
    if elapsed is not None:
        if data['kind']=='Krank':credited=480
        elif data['kind']=='Urlaub':credited=0 if is_rest_day(db,user.id,start.date()) else 480
    pauses=[duration(e['start_at'],e['end_at']) for t in data['train_journeys'] for e in t['events'] if e.get('reason')=='Pause']
    pause=data['actual_pause']+sum(pauses) if data['actual_pause'] is not None and all(v is not None for v in pauses) else '—'
    return dict(duration_minutes=elapsed,credited_minutes=credited,guest_total_minutes=total,guest_minutes=inside,external_guest_minutes=total-inside if total is not None and inside is not None else None,documented_pause_minutes=pause)

def normalize(snapshot):
    if not isinstance(snapshot,dict) or not isinstance(snapshot.get('report'),dict):raise HTTPException(422)
    def row(value):
        if not isinstance(value,dict):raise HTTPException(422)
        result={key:str(value.get(key) or '')[:2000] for key in TEXT_FIELDS}
        result['self_payer']=value.get('self_payer') is True
        return result
    raw=snapshot['report'];data=row(raw)
    try:
        pause=float(raw.get('actual_pause',0));data['actual_pause']=(int(pause) if pause.is_integer() else pause) if math.isfinite(pause) else None
    except (TypeError,ValueError):data['actual_pause']=None
    data.update(in_hotel=raw.get('in_hotel') is True,ausbleibe=[str(v)[:30] for v in raw.get('ausbleibe',[])[:10]],trips=[],train_journeys=[])
    for key,limit in [('trips',100),('train_journeys',50)]:
        rows=raw.get(key,[])
        if not isinstance(rows,list) or len(rows)>limit:raise HTTPException(413)
        for value in rows:
            item=row(value)
            if key=='train_journeys':
                events=value.get('events',[])
                if not isinstance(events,list) or len(events)>500:raise HTTPException(413)
                item['events']=[row(e) for e in events]
            data[key].append(item)
    if sum(len(t['events']) for t in data['train_journeys'])+len(data['trips'])>2000:raise HTTPException(413)
    if snapshot.get('guest'):
        item=row(snapshot['guest']);item['transport_detail']=source('report_preview.text_ca34bce8b078')+' · '+item['transport_detail'];data['trips'].append(item)
    for editor in snapshot.get('editors',[])[:50]:
        if not isinstance(editor,dict) or not editor.get('pending'):continue
        target=next((t for t in data['train_journeys'] if t['id']==editor.get('id')),None)
        if target:
            item=row(editor.get('eventFields',{}));item['reason_detail']=source('report_preview.text_ca34bce8b078')+' · '+item['reason_detail'];target['events'].append(item)
    return data

def render(db,user,snapshot):
    from ..documents.archive import work_report_layout,pdf_document
    data=normalize(snapshot)
    report=SimpleNamespace(id='—',payload_json=json.dumps(data))
    layout=work_report_layout(db,user,report,preview=True)
    return dict(layout=layout,pdf=base64.b64encode(pdf_document(**layout)).decode('ascii'))
