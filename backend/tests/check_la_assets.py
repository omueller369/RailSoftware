"""Pinned local PDF renderer, licences, native routes and packaged assets."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--apk',type=Path);a=p.parse_args();static=ROOT/'backend/lokzeitleiste/static';vendor=static/'la-vendor';m=json.loads((vendor/'manifest.json').read_text())
    assert m['version']=='6.5.438' and m['license']=='Apache-2.0'
    assert all(name in m['files'] for name in ['LICENSE','cmaps/LICENSE','standard_fonts/LICENSE_FOXIT','standard_fonts/LICENSE_LIBERATION','wasm/LICENSE_OPENJPEG'])
    for name,digest in m['files'].items():assert hashlib.sha256((vendor/name).read_bytes()).hexdigest()==digest,name
    if a.apk:
        with zipfile.ZipFile(a.apk) as z:
            for file in ['la-instructions.js','la-instructions.css','auth-session.js','android-portal.js','tf-help-content.js','tf-portal.js']:
                assert z.read('assets/tf-portal/'+file)==(static/file).read_bytes(),file
            for name,digest in m['files'].items():assert hashlib.sha256(z.read('assets/tf-portal/la-vendor/'+name)).hexdigest()==digest,name
            page=z.read('assets/tf-portal/tf-portal.html').decode();assert '/tf/la-anweisungen' in page and '/tf/la-instructions.js' in page
            assert 'assets/tf-portal/la-admin.html' not in z.namelist()
    print('La PDF renderer: pinned source checksums, licences and '+('APK assets' if a.apk else 'local assets')+' verified.')
if __name__=='__main__':main()
