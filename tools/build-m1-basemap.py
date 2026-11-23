# Bereitet Kartenbedienung und Bildausschnitte aus den eingecheckten Quellen reproduzierbar auf.
"""Build the public-domain offline background from the checked-in reference."""
import argparse,gzip,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'backend/lokzeitleiste';reference=root/'reference/basemap'
parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
raw=(reference/'central-europe.geojson.gz').read_bytes();manifest=json.loads((reference/'manifest.json').read_text())
assert hashlib.sha256(raw).hexdigest()==manifest['canonical_sha256']
data=json.loads(gzip.decompress(raw));content='/* Ländergrenzen: Natural Earth 1:50m, gemeinfrei. Quelle: reference/basemap/manifest.json. */\nwindow.M1BasemapSeed='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n'
places_raw=(reference/'places.json.gz').read_bytes()
assert hashlib.sha256(places_raw).hexdigest()==manifest['places']['canonical_sha256']
places=json.loads(gzip.decompress(places_raw))
assert len(places)==manifest['places']['count']
content+='/* Ortsnamen: GeoNames, CC BY 4.0. */\nwindow.M1BasemapPlaces='+json.dumps(places,ensure_ascii=False,separators=(',',':'))+';\n'
p=root/'static/m1-basemap-data.js'
if args.check:assert p.read_text()==content
else:p.write_text(content)
print('Offline background:',len(data['features']),'countries verified')
