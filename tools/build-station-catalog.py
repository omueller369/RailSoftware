# Bereitet Betriebsstellen und Ortszuordnungen aus den eingecheckten Quellen reproduzierbar auf.
"""Build a reproducible public DS100 bundle for offline web and Android use."""
import argparse
import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'backend/lokzeitleiste/accounts'
MANIFEST=SOURCE/'station_catalog_manifest.json'
OUTPUT=ROOT/'backend/lokzeitleiste/static/station-catalog-data.js'
def normalized(value):return re.sub(r'[^a-z0-9äöüß]','',unicodedata.normalize('NFC',value).casefold())
def build():
    stations=json.loads((SOURCE/'stations.json').read_text())
    positions=json.loads((SOURCE/'station_coordinates.json').read_text())
    coords={row['code']:row for row in positions['records']};rows=[];seen=set()
    for station in sorted(stations,key=lambda s:s['code']):
        code,name=station['code'],station['name']
        if not code or not name or code in seen:raise ValueError('Invalid station catalogue')
        seen.add(code);row=[code,name];point=coords.get(code)
        if point and normalized(name)==normalized(point['name']):row.extend([point['latitude'],point['longitude']])
        rows.append(row)
    operating=json.loads(gzip.decompress((ROOT/'backend/lokzeitleiste/reference/operating-points/m1-operating-points.json.gz').read_bytes()))
    packed=json.dumps(rows,ensure_ascii=False,separators=(',',':'))
    data=dict(schema=1,revision=hashlib.sha256(packed.encode()).hexdigest(),stations=rows,coordinate_count=sum(len(row)==4 for row in rows),operating_points=operating['points'],operating_points_source=operating['source'],source={key:positions[key] for key in ['source','source_url','source_date','license','license_url','crs']})
    return '// Erzeugt aus öffentlichen Ortsdaten durch tools/build-station-catalog.py.\nwindow.StationCatalogSeed='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();text=build()
    seed=json.loads(text.split('window.StationCatalogSeed=',1)[1].strip().rstrip(';'))
    manifest=json.dumps(dict(schema=1,revision=seed['revision'],entry_count=len(seed['stations']),coordinate_count=seed['coordinate_count']),indent=2)+'\n'
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text()!=text or not MANIFEST.exists() or MANIFEST.read_text()!=manifest:raise SystemExit('Offline DS100 bundle is stale. Run python tools/build-station-catalog.py')
    else:OUTPUT.write_text(text);MANIFEST.write_text(manifest)
    print(f'Offline DS100 catalogue: {len(seed["stations"])} entries / {seed["coordinate_count"]} reference coordinates verified.')
if __name__=='__main__':main()
