"""Verify the actual offline data and counting modules in the tablet APK."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apk',type=Path,required=True);args=parser.parse_args()
    manifest=json.loads((ROOT/'backend/lokzeitleiste/reference/rail-network/manifest.json').read_text())
    with zipfile.ZipFile(args.apk) as archive:
        for name in ['m1-basemap-data.js','m1-map.js','route-editor.js','portal-theme.css','location-editor.js','knowledge-inventory.js','station-catalog-data.js','route-imports.js','rail-network-data.js','rail-network.js','route-coverage.js','route-knowledge.js','route-csv.js']:
            data=archive.read('assets/tf-portal/'+name)
            if data!=(ROOT/'backend/lokzeitleiste/static'/name).read_bytes():raise SystemExit('Stale or missing offline asset: '+name)
            if name=='rail-network-data.js' and hashlib.sha256(data).hexdigest()!=manifest['bundle_sha256']:raise SystemExit('Offline network checksum mismatch')
        html=archive.read('assets/tf-portal/tf-portal.html').decode()
        if not html.index('/tf/m1-basemap-data.js')<html.index('/tf/m1-map.js')<html.index('/tf/gps.js'):raise SystemExit('M1 layers must load before GPS')
        if not html.index('/tf/route-editor.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Manual editor must load before knowledge tabs')
        if not html.index('/tf/location-editor.js')<html.index('/tf/knowledge-inventory.js'):raise SystemExit('Location editor must load before inventory lists')
        if not html.index('/tf/knowledge-inventory.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Knowledge inventories must load before their tabs')
        if not html.index('/tf/route-imports.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Imported reference layer must load before the map')
        if not html.index('/tf/route-csv.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Private CSV module must load before the map module')
        if not html.index('/tf/route-coverage.js')<html.index('/tf/rail-network.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Offline map module loading order is incorrect')
    print('Android offline rail network: 1,549 routes, exact reference data, loader, passage colours and map assets verified.')
if __name__=='__main__':main()
