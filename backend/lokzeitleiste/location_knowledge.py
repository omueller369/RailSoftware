# Gemeinsame Verarbeitung für Ortskenntnisse und ihre Gültigkeit.
"""Calendar-based location validity and monotonic renewal from actual GPS captures."""
import calendar,hashlib,json,unicodedata,math
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from .models import TfLocationKnowledge,RailwayStation
BERLIN=ZoneInfo('Europe/Berlin')
def today():return datetime.now(BERLIN).date()
def add_months(value,months):
    month=value.year*12+value.month-1+months;year,month=divmod(month,12);month+=1
    return date(year,month,min(value.day,calendar.monthrange(year,month)[1]))
def until_date(raw):
    try:return date.fromisoformat(raw)
    except (ValueError,TypeError):return None

def validity(raw,at=None):
    at=at or today();end=until_date(raw)
    return 'unknown' if end is None else 'expired' if end<at else 'expiring' if end<=add_months(at,3) else 'valid'
def normalize_code(code):return unicodedata.normalize('NFC',' '.join(code.upper().split()))
def owned_place(db,owner_id,code,lock=False):
    query=select(TfLocationKnowledge).where(TfLocationKnowledge.owner_id==owner_id)
    if lock:query=query.with_for_update()
    matches=[row for row in db.scalars(query) if normalize_code(row.ds100)==normalize_code(code)]
    return max(matches,key=lambda row:until_date(row.known_until) or date.min) if matches else None
def identity_key(code):return hashlib.sha256(unicodedata.normalize('NFC',code.strip()).upper().encode()).hexdigest()
def refresh_hash(row):
    values={key:getattr(row,key) for key in ['station_name','ds100','known_until']}
    row.content_sha256=hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def renew_from_gps(db,owner_id,payload):
    """Caller locks owner and owns transaction; replay/upload never advances capture date.

    Start needs a usable measured fix. End additionally needs a finished recording
    with later usable fixes. No credit for free text or manual-stand-only records.
    """
    at=today()
    def usable(point):
        if not isinstance(point,dict):return False
        for key,low,high in [('t',946684800000,4133980800000),('accuracy',0,50),('lat',-90,90),('lon',-180,180)]:
            value=point.get(key)
            if not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:return False
        return datetime.fromtimestamp(point['t']/1000,timezone.utc).astimezone(BERLIN).date()<=at
    fixes=[p for p in payload.get('points',[]) if usable(p)]
    if not fixes:return 0
    events=[('start',fixes[0])]
    # Eine Zielverlängerung braucht die ausdrückliche, an den Bahnhof gebundene Zustimmung.
    consent=payload.get('renew_end_location') is True and normalize_code(payload.get('renew_end_station') or '')==normalize_code(payload.get('end_station') or '')
    if consent and payload.get('ended') and len(fixes)>1 and fixes[-1]['t']>fixes[0]['t']:events.append(('end',fixes[-1]))
    changed=0
    for kind,point in events:
        code=(payload.get(kind+'_station') or '').strip().upper()
        if not code:continue
        station=db.get(RailwayStation,code)
        if not station:continue
        captured=datetime.fromtimestamp(point['t']/1000,timezone.utc).astimezone(BERLIN).date();target=add_months(captured,12)
        key=identity_key(code);row=owned_place(db,owner_id,code,lock=True)
        if row and until_date(row.known_until) and until_date(row.known_until)>=target:continue
        if row is None:
            row=TfLocationKnowledge(owner_id=owner_id,identity_key=key,station_name=station.name,ds100=station.code,known_until=target.isoformat());db.add(row)
        else:row.known_until=target.isoformat()
        refresh_hash(row);db.flush();changed+=1
    return changed
