"""Ensure the tablet actually contains the changed editor and GPS defaults."""
import argparse,zipfile,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--apk',type=Path,required=True);a=p.parse_args()
    with zipfile.ZipFile(a.apk) as z:
        for name in ['gps-settings.js','gps-demo.js','gps-demo-visibility.js','tf-profile.html','tf-portal.html','work-report.js','work-report.css','train-journeys.js','gps.js','tf-help-content.js','auth-session.js','updates.js']:
            actual=z.read('assets/tf-portal/'+name)
            expected=(ROOT/'backend/lokzeitleiste/static'/name).read_bytes()
            if name.endswith('.html'):
                messages=json.loads((ROOT/'backend/lokzeitleiste/locales/keys.json').read_text())['de']
                expected=re.sub(r'\{\{([a-z][a-z0-9_]*\.text_[a-f0-9]{12})\}\}',lambda match:messages[match[1]],expected.decode()).strip()
                assert actual.decode().strip()==expected,name
            else:assert actual==expected,name
        assert 'assets/tf-portal/admin-work-reports.js' not in z.namelist()
        assert 'assets/tf-portal/admin-gps-demo.js' not in z.namelist()
    print('Android: correction editor, yellow rows, final duty validation, GPS defaults and current help verified.')
if __name__=='__main__':main()
