# Gemeinsame Verarbeitung für die gemeinsamen Anwendungsabläufe.
"""One explicitly requested spelling for the train-event cause, including legacy keys."""
import json
from sqlalchemy import select
from .models import AppDefaultValue,AppDefaultSeed,AppDefaultOrder,AppDefaultAlias,DutyReport,DutyReportDraft,DutyReportCorrection,TrainGpsRecording,GpsDemoShare

CANONICAL='DB-InfraGo'
def named(value):
    return isinstance(value,str) and value.strip().casefold().replace(' ','').replace('-','') in {'dbinfrago','dbinfraogo'}
def canonical(value,aliases=None):return CANONICAL if isinstance(value,str) and (named(value) or value in (aliases or {})) else value

def normalize(value,aliases=None):
    if isinstance(value,list):return [normalize(item,aliases) for item in value]
    if not isinstance(value,dict):return value
    result={key:item if key=='points' else canonical(item,aliases) if key in ('cause','cause_label') and isinstance(item,str) else normalize(item,aliases) for key,item in value.items()}
    if result.get('cause')==CANONICAL and 'cause_label' in result:result['cause_label']=CANONICAL
    return result

def alias_map(db):return {row.alias:row.canonical for row in db.scalars(select(AppDefaultAlias).where(AppDefaultAlias.category=='cause'))}
def normalize_model(db,data,aliases=None):
    if aliases is None:aliases=alias_map(db)
    for train in data.train_journeys:
        for event in train.events:
            event.cause=canonical(event.cause,aliases)
            if named(event.cause_label) or event.cause==CANONICAL:event.cause_label=CANONICAL
    return data

def migrate(db):
    """Atomic and repeatable; report versions, revisions, GPS fixes and PDF bytes remain intact."""
    if db.get(AppDefaultSeed,3):return
    db.scalar(select(AppDefaultSeed).where(AppDefaultSeed.id==1).with_for_update())
    if db.scalar(select(AppDefaultSeed).where(AppDefaultSeed.id==3).with_for_update()):return
    rows=list(db.scalars(select(AppDefaultValue).where(AppDefaultValue.category=='cause').with_for_update()))
    matches=[row for row in rows if named(row.value) or named(row.label)]
    target=next((row for row in matches if row.value==CANONICAL),None)
    if target is None:
        target=next(iter(matches),None)
        if target is None:
            target=AppDefaultValue(category='cause',value=CANONICAL,label=CANONICAL,label_key=CANONICAL.casefold(),active=True,ever_used=False,revision=1);db.add(target);db.flush()
    aliases=alias_map(db)
    for alias in {'DB InfraGo','DB InfraoGo','DB-InfraoGo',*(row.value for row in matches)}:
        if alias==CANONICAL:continue
        aliases[alias]=CANONICAL
        if not db.get(AppDefaultAlias,('cause',alias)):db.add(AppDefaultAlias(category='cause',alias=alias,canonical=CANONICAL))
    duplicate_ids={row.id for row in matches if row is not target}
    used=any(row.ever_used for row in matches)
    # Doppelte eindeutige Bezeichnungen vor dem Ändern des verbleibenden Schlüssels entfernen.
    for row in matches:
        if row is not target:db.delete(row)
    db.flush()
    target.value=target.label=CANONICAL;target.label_key=CANONICAL.casefold();target.active=True;target.ever_used=used;target.revision+=1
    order=db.get(AppDefaultOrder,'cause')
    if order:
        ids=[target.id if item in duplicate_ids else item for item in json.loads(order.ids_json)];unique=list(dict.fromkeys(ids))
        if unique!=json.loads(order.ids_json):order.ids_json=json.dumps(unique);order.revision+=1
    db.flush()
    # Re-encode equal snapshots identically so correction guards and idempotency stay valid.
    for model,fields in [(DutyReport,['payload_json']),(DutyReportDraft,['payload_json']),(TrainGpsRecording,['payload_json']),(GpsDemoShare,['payload_json']),(DutyReportCorrection,['payload_json','submitted_json'])]:
        primary=model.recording_id if model is GpsDemoShare else model.id;last=-1
        while True:
            batch=list(db.scalars(select(model).where(primary>last).order_by(primary).limit(20).with_for_update()))
            if not batch:break
            for row in batch:
                last=getattr(row,primary.key)
                for field in fields:
                    raw=getattr(row,field)
                    if not raw:continue
                    before=json.loads(raw);after=normalize(before,aliases)
                    if after!=before:
                        setattr(row,field,json.dumps(after,ensure_ascii=False,separators=(',',':')))
                        target.ever_used=True
            db.flush()
    db.add(AppDefaultSeed(id=3));db.commit()
