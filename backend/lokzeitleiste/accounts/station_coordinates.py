"""Conservative, offline and fill-only reference coordinate import."""
import json
import math
import re
import unicodedata
from pathlib import Path
from sqlalchemy import select
from ..models import RailwayStation,RailwayStationCoordinates
from ..localization import source

INVALID_KEY='station_coordinates.text_fed00b2cee7c'
BUNDLE=Path(__file__).with_name('station_coordinates.json')


def normalized_name(value):
    return re.sub(r'[^a-z0-9äöüß]','',unicodedata.normalize('NFC',value).casefold())


def load_bundle(path=BUNDLE):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    def invalid():raise ValueError(source(INVALID_KEY))
    if not isinstance(data,dict) or data.get('crs')!='EPSG:4326' or not isinstance(data.get('records'),list):invalid()
    if not isinstance(data.get('source_url'),str) or not data['source_url'].startswith('https://') or len(data['source_url'])>500 or not re.fullmatch(r'\d{4}-\d{2}',data.get('source_date','')):invalid()
    seen=set()
    for row in data['records']:
        if not isinstance(row,dict):invalid()
        for field,limit in [('code',10),('name',200),('source_name',200)]:
            if not isinstance(row.get(field),str) or not row[field].strip() or len(row[field])>limit:invalid()
        if row['code'] in seen or row['code']!=row['code'].strip().upper():invalid()
        seen.add(row['code'])
        for field,minimum,maximum in [('latitude',-90,90),('longitude',-180,180),('max_spread_m',0,25)]:
            if type(row.get(field)) not in (int,float) or not math.isfinite(row[field]) or not minimum<=row[field]<=maximum:invalid()
        if row['latitude']==0 and row['longitude']==0 or normalized_name(row['name'])!=normalized_name(row['source_name']):invalid()
    return data


def seed_coordinates(db,path=BUNDLE):
    """Caller owns transaction. Validate everything before writing any coordinate.

    Never create a station, rename it or overwrite a previously stored position.
    Modified live names and codes absent from the live catalogue are skipped.
    """
    bundle=load_bundle(path)
    stations=dict(db.execute(select(RailwayStation.code,RailwayStation.name)).all())
    existing=set(db.scalars(select(RailwayStationCoordinates.code)))
    records=[]
    for row in bundle['records']:
        if row['code'] in existing or row['code'] not in stations:continue
        if normalized_name(stations[row['code']])!=normalized_name(row['name']):continue
        records.append(dict(code=row['code'],catalog_name=stations[row['code']],latitude=row['latitude'],longitude=row['longitude'],source_name=row['source_name'],source_url=bundle['source_url'],source_date=bundle['source_date'],max_spread_m=row['max_spread_m']))
    if records:db.bulk_insert_mappings(RailwayStationCoordinates,records)
    return len(records)


def with_coordinates(db,rows):
    if not rows:return rows
    coords={r.code:r for r in db.scalars(select(RailwayStationCoordinates).where(RailwayStationCoordinates.code.in_([r['code'] for r in rows])))}
    for row in rows:
        point=coords.get(row['code'])
        # Do not attach a stale position after a live catalogue rename.
        row['coordinates']=dict(latitude=point.latitude,longitude=point.longitude,crs='EPSG:4326',source_url=point.source_url,source_date=point.source_date) if point and normalized_name(point.catalog_name)==normalized_name(row['name']) else None
    return rows
