# Gemeinsame Verarbeitung für die gemeinsamen Anwendungsabläufe.
"""Public route-specific operating point references; never create journey credits."""
import gzip,hashlib,json,math
from functools import lru_cache
from pathlib import Path
from sqlalchemy import select
from .models import RailwayOperatingPoint,RailwayStation,StationCatalogMigration
ROOT=Path(__file__).parent/'reference'/'operating-points'

@lru_cache(maxsize=1)
def load_points():
    raw=(ROOT/'m1-operating-points.json.gz').read_bytes()
    manifest=json.loads((ROOT/'manifest.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=manifest['canonical_sha256']:raise ValueError('Operating point checksum mismatch')
    data=json.loads(gzip.decompress(raw))
    for row in data['points']:
        if not row['code'] or len(row['code'])>10 or not row['route'].isdigit() or not all(math.isfinite(row[k]) for k in ['lat','lon']) or not -90<=row['lat']<=90 or not -180<=row['lon']<=180:raise ValueError('Invalid operating point')
    return data

def seed_operating_points(db):
    data=load_points();migration='m1-points-'+data['source']['sha256'][:16]
    if db.get(StationCatalogMigration,migration):return 0
    existing=set(db.scalars(select(RailwayOperatingPoint.key)));records=[]
    for row in data['points']:
        payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'));key=hashlib.sha256(payload.encode()).hexdigest()
        if key in existing:continue
        existing.add(key);records.append(dict(key=key,code=row['code'],route_number=row['route'],payload_json=payload))
    additions=json.loads((ROOT/'catalog-additions.json').read_text());codes=set(db.scalars(select(RailwayStation.code)))
    for row in additions:
        if row['code'] not in codes:db.add(RailwayStation(**row));codes.add(row['code'])
    if records:db.bulk_insert_mappings(RailwayOperatingPoint,records)
    db.add(StationCatalogMigration(key=migration))
    return len(records)

def route_references(db,route_number,codes):
    return [json.loads(row.payload_json) for row in db.scalars(select(RailwayOperatingPoint).where(RailwayOperatingPoint.route_number==str(int(route_number)),RailwayOperatingPoint.code.in_(codes)))]
