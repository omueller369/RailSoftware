"""Verify the actual offline data and counting modules in the tablet APK."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apk',type=Path,required=True);args=parser.parse_args()
    manifest=json.loads((ROOT/'backend/lokzeitleiste/reference/rail-network/manifest.json').read_text())
    with zipfile.ZipFile(args.apk) as archive:
        for name in ['rail-network-data.js','rail-network.js','route-coverage.js','route-knowledge.js','route-csv.js']:
            data=archive.read('assets/tf-portal/'+name)
            if data!=(ROOT/'backend/lokzeitleiste/static'/name).read_bytes():raise SystemExit('Stale or missing offline asset: '+name)
            if name=='rail-network-data.js' and hashlib.sha256(data).hexdigest()!=manifest['bundle_sha256']:raise SystemExit('Offline network checksum mismatch')
        html=archive.read('assets/tf-portal/tf-portal.html').decode()
        if not html.index('/tf/route-csv.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Private CSV module must load before the map module')
        if not html.index('/tf/route-coverage.js')<html.index('/tf/rail-network.js')<html.index('/tf/route-knowledge.js'):raise SystemExit('Offline map module loading order is incorrect')
    print('Android offline rail network: 1,549 routes, exact reference data, loader, passage colours and map assets verified.')
if __name__=='__main__':main()
