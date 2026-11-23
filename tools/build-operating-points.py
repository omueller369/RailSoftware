# Bereitet die gemeinsamen Anwendungsabläufe aus den eingecheckten Quellen reproduzierbar auf.
"""Import supplied M1 operating points; preserve route-specific points and source names.

Only unambiguous active stations get a shared GPS coordinate. Existing coordinates
and names are never replaced. All source rows remain available as reference data.
"""
import argparse,csv,gzip,hashlib,io,json,math,re,unicodedata
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACCOUNTS=ROOT/'backend/lokzeitleiste/accounts'
REF=ROOT/'backend/lokzeitleiste/reference/operating-points'
CANONICAL=REF/'m1-operating-points.json.gz'
FIELDS={'route':'Streckennummer','code':'Kürzel','name':'Bezeichnung','type':'Art','type_name':'Art lang','state':'Betriebszustand','km':'km_lage_l','route_name':'Streckenkurzname','region':'Bundesland'}
def norm(s):return re.sub(r'[^a-z0-9äöüß]','',unicodedata.normalize('NFC',s).casefold())
def distance(a,b):
 lat1,lon1,lat2,lon2=map(math.radians,[a['lat'],a['lon'],b['lat'],b['lon']]);return 12742000*math.asin(min(1,math.sqrt(math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2)))
def dump(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n'
def import_source(path):
 raw=path.read_bytes();rows=[]
 for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';',strict=True):
  item={key:row[col] for key,col in FIELDS.items()};item['code']=' '.join(item['code'].upper().split())
  item.update(lat=float(row['Geographische Breite (EPSG 4326)'].replace(',','.')),lon=float(row['Geographische Länge (EPSG 4326)'].replace(',','.')))
  if not item['route'].isdigit() or not item['code'] or not item['name'] or not all(math.isfinite(item[k]) for k in ['lat','lon']) or not -90<=item['lat']<=90 or not -180<=item['lon']<=180:raise ValueError('Invalid M1 row')
  rows.append(item)
 source={'name':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'crs':'EPSG:4326','source_rows':len(rows),'imported_at':'2026-11-17','coordinate_fields':'Geographische Länge/Breite (EPSG 4326)','note':'Uploaded M1 export; retain route-specific points, do not average or infer train passages.'}
 CANONICAL.write_bytes(gzip.compress(dump(dict(schema=1,source=source,points=rows)).encode(),mtime=0))
def build(check=False):
 data=json.loads(gzip.decompress(CANONICAL.read_bytes()));groups=defaultdict(list)
 for row in data['points']:groups[row['code']].append(row)
 stations=json.loads((ACCOUNTS/'stations.json').read_text());catalog={r['code']:r['name'] for r in stations};coords=json.loads((ACCOUNTS/'station_coordinates.json').read_text());positions={r['code']:r for r in coords['records']};additions=[];review=[];new_points=[]
 for code,rows in sorted(groups.items()):
  active=[r for r in rows if r['state']=='in Betrieb'];names={norm(r['name']) for r in active}
  if not active:continue
  if len(names)!=1 or code in catalog and norm(catalog[code]) not in names:
   review.append(dict(code=code,reason='name_conflict',names=sorted({r['name'] for r in rows})));continue
  if code not in catalog:
   catalog[code]=active[0]['name'];stations.append(dict(code=code,name=catalog[code]));additions.append(code)
  spread=max((distance(a,b) for a in active for b in active),default=0)
  if spread>25:
   review.append(dict(code=code,reason='multiple_reference_points',max_spread_m=round(spread,2)));continue
  if code in positions:continue
  r=active[0];point=dict(code=code,name=catalog[code],latitude=r['lat'],longitude=r['lon'],source_name=r['name'],max_spread_m=round(spread,2));coords['records'].append(point);new_points.append(code)
 # A stable import report is generated once, not rewritten on reproducibility checks.
 if not check:
  (ACCOUNTS/'stations.json').write_text(dump(sorted(stations,key=lambda r:r['code'])))
  coords['records'].sort(key=lambda r:r['code']);coords['supplement_csv_sha256']=data['source']['sha256'];(ACCOUNTS/'station_coordinates.json').write_text(dump(coords))
  (REF/'catalog-additions.json').write_text(dump([r for r in stations if r['code'] in additions]))
  (REF/'review.json').write_text(dump(review))
  (REF/'import-report.json').write_text(json.dumps(dict(source_rows=len(data['points']),distinct_codes=len(groups),stations_added=len(additions),coordinates_added=len(new_points),review_codes=len(review),policy='Keep existing names/coordinates; active exact-name matches, maximum spread 25m; no centroid.'),ensure_ascii=False,indent=2)+'\n')
 manifest=json.dumps(dict(schema=1,source=data['source'],canonical_sha256=hashlib.sha256(CANONICAL.read_bytes()).hexdigest(),point_count=len(data['points']),code_count=len(groups)),ensure_ascii=False,indent=2)+'\n'
 if check:
  assert (REF/'manifest.json').read_text()==manifest,'Operating point manifest is stale'
 else:(REF/'manifest.json').write_text(manifest)
 print(f"M1 operating points: {len(data['points'])} source rows, {len(groups)} codes; {len(additions)} new stations, {len(new_points)} new GPS coordinates.")
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 if args.source:
  if CANONICAL.exists():raise SystemExit('Canonical source already imported; review changes before replacing it')
  import_source(args.source)
  build(False)
 else:build(True)
