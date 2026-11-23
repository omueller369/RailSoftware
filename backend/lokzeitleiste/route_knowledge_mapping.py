# Gemeinsame Verarbeitung für Streckenkenntnisse und Referenzgeometrie.
"""Map imported knowledge onto public reference geometry, without inventing GPS rides."""
import gzip,json,re
from collections import defaultdict,Counter
from functools import lru_cache
from pathlib import Path
from .operating_points import load_points
REF=Path(__file__).parent/'reference'/'rail-network'

def mileage(value):
    match=re.fullmatch(r'(-?\d+(?:,\d+)?)\s*\+\s*(-?\d+(?:,\d+)?)',value.strip())
    return round(float(match[1].replace(',','.'))*1000+float(match[2].replace(',','.')),3) if match else None

@lru_cache(maxsize=1)
def reference():
    points=defaultdict(list);routes=defaultdict(list)
    for row in load_points()['points']:points[(str(int(row['route'])),row['code'])].append(row)
    network=json.loads(gzip.decompress((REF/'m1-network.json.gz').read_bytes()))
    for row in network['records']:
        if row[4]:routes[str(int(row[0]))].append(sorted(row[4]))
    manifest=json.loads((REF/'manifest.json').read_text());revision=manifest.get('reference_revision',manifest['bundle_sha256'])
    return points,routes,revision

def match(row):
    points,routes,revision=reference();route=str(int(row['route_number']))
    def result(status,**values):return dict(status=status,route=route,reference_revision=revision,**values)
    if route=='0':return result('missing_route')
    if route not in routes:return result('missing_geometry')
    endpoints=[]
    for field in ['from_code','to_code']:
        code=' '.join(row[field].strip().upper().split());candidates=points.get((route,code),[])
        if not candidates:return result('missing_endpoint')
        values={mileage(p['km']) for p in candidates}
        if None in values:return result('missing_mileage')
        if len(values)!=1:return result('ambiguous_endpoint')
        endpoints.append(next(iter(values)))
    lo,hi=sorted(endpoints)
    if hi-lo<.01:return result('same_position')
    ranges=sorted((max(lo,a),min(hi,b)) for a,b in routes[route] if min(hi,b)>max(lo,a))
    if not ranges:return result('outside_geometry')
    covered=0;end=lo
    for a,b in ranges:covered+=max(0,b-max(a,end));end=max(end,b)
    return result('mapped' if covered>=hi-lo-.5 else 'partial',from_m=endpoints[0],to_m=endpoints[1])

def match_counts(records):return dict(Counter(match(json.loads(row['source_json']))['status'] for row in records))
