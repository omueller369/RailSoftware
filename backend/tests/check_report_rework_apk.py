"""Ensure the tablet actually contains the changed editor and GPS defaults."""
import argparse,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--apk',type=Path,required=True);a=p.parse_args()
    with zipfile.ZipFile(a.apk) as z:
        for name in ['gps-settings.js','gps-demo.js','gps-demo-visibility.js','tf-profile.html','tf-portal.html','work-report.js','work-report.css','train-journeys.js','gps.js','tf-help-content.js','auth-session.js','updates.js']:
            assert z.read('assets/tf-portal/'+name)==(ROOT/'backend/lokzeitleiste/static'/name).read_bytes(),name
        assert 'assets/tf-portal/admin-work-reports.js' not in z.namelist()
        assert 'assets/tf-portal/admin-gps-demo.js' not in z.namelist()
    print('Android: correction editor, yellow rows, final duty validation, GPS defaults and current help verified.')
if __name__=='__main__':main()
