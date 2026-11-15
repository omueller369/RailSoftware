import copy,json,tempfile,unittest
from pathlib import Path
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from lokzeitleiste.db import Base
from lokzeitleiste.models import RailwayStation,RailwayStationCoordinates
from lokzeitleiste.accounts.tf_profiles import seed_stations
from lokzeitleiste.accounts.station_coordinates import BUNDLE,load_bundle,seed_coordinates,with_coordinates,normalized_name
import test_stations


class StationCoordinatesTest(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

    def test_complete_catalog_is_filled_once_and_review_codes_are_not_included(self):
        bundle=load_bundle();records=bundle['records'];self.assertEqual(len(records),5408)
        review=BUNDLE.with_name('station_coordinates_review.txt').read_text().splitlines()
        self.assertEqual(len(review),857);self.assertEqual(len(set(review)),857)
        self.assertFalse({row['code'] for row in records}&set(review))
        self.assertEqual(bundle['source_date'],'2026-05');self.assertEqual(bundle['license'],'CC-BY-4.0')
        with Session(self.engine) as db:
            seed_stations(db);self.assertEqual(seed_coordinates(db),5408);db.commit()
            self.assertEqual(db.scalar(select(func.count()).select_from(RailwayStation)),13720)
            self.assertEqual(seed_coordinates(db),0)
            row=db.get(RailwayStationCoordinates,'AABG');self.assertIsNotNone(row)
            self.assertTrue(47<=row.latitude<=56 and 5<=row.longitude<=16)
            self.assertEqual(row.source_date,'2026-05')
            self.assertIsNone(db.get(RailwayStationCoordinates,'AA'))

    def test_fill_only_preserves_existing_positions_and_live_names_and_transaction(self):
        records=load_bundle()['records'];one=next(r for r in records if r['code']=='AABG');two=next(r for r in records if r['code']=='AACW')
        with Session(self.engine) as db:
            db.add_all([RailwayStation(code=one['code'],name=one['name']),RailwayStation(code=two['code'],name='Eigene geänderte Bezeichnung')]);db.flush()
            stored=RailwayStationCoordinates(code=one['code'],catalog_name=one['name'],latitude=51.25,longitude=13.5,source_name='Manuell',source_url='https://example.com/manual',source_date='2025-01',max_spread_m=0);db.add(stored);db.commit()
            self.assertEqual(seed_coordinates(db),0);self.assertEqual(db.get(RailwayStationCoordinates,'AABG').latitude,51.25)
            self.assertIsNone(db.get(RailwayStationCoordinates,'AACW'));self.assertEqual(db.get(RailwayStation,'AACW').name,'Eigene geänderte Bezeichnung')
            db.delete(stored);db.commit();self.assertEqual(seed_coordinates(db),1);db.rollback()
            self.assertIsNone(db.get(RailwayStationCoordinates,'AABG'),'Importer leaves commit/rollback to caller')

    def test_invalid_bundle_is_rejected_before_any_write(self):
        original=load_bundle()
        for field,value in [('latitude',float('nan')),('longitude',181),('max_spread_m',26),('name','Another station')]:
            broken=copy.deepcopy(original);broken['records'][-1][field]=value
            with tempfile.TemporaryDirectory() as directory,Session(self.engine) as db:
                if not db.get(RailwayStation,'AABG'):
                    db.add(RailwayStation(code='AABG',name='Agathenburg'));db.commit()
                path=Path(directory)/'invalid.json';path.write_text(json.dumps(broken))
                with self.assertRaises(ValueError):seed_coordinates(db,path)
                self.assertEqual(db.scalar(select(func.count()).select_from(RailwayStationCoordinates)),0)

    def test_catalog_views_hide_positions_after_identity_change(self):
        with Session(self.engine) as db:
            db.add(RailwayStation(code='TEST',name='Original'));db.flush()
            db.add(RailwayStationCoordinates(code='TEST',catalog_name='Original',latitude=51,longitude=13,source_name='Original',source_url='https://example.com/source',source_date='2026-05',max_spread_m=0));db.commit()
            result=with_coordinates(db,[dict(code='TEST',name='Original')])[0]
            self.assertEqual(result['coordinates']['latitude'],51)
            self.assertIsNone(with_coordinates(db,[dict(code='TEST',name='Other')])[0]['coordinates'])


class StationCoordinateApiTest(unittest.TestCase):
    setUp=test_stations.StationDirectoryTest.setUp
    tearDown=test_stations.StationDirectoryTest.tearDown

    def test_catalog_exposes_reference_coordinates_without_changing_station_identity(self):
        with Session(self.engine) as db:
            db.add(RailwayStationCoordinates(code='BBB',catalog_name='Berlin Beispiel',latitude=52.5,longitude=13.4,source_name='Berlin Beispiel',source_url='https://example.com/source',source_date='2026-05',max_spread_m=0));db.commit()
        row=self.driver.get('/api/v1/tf/stations/catalog',params={'q':'BBB'}).json()[0]
        self.assertEqual(row['code'],'BBB');self.assertEqual(row['name'],'Berlin Beispiel');self.assertEqual(row['coordinates']['latitude'],52.5)
        row=self.driver.get('/api/v1/tf/stations/catalog',params={'q':'CCC'}).json()[0];self.assertIsNone(row['coordinates'])
        self.assertEqual(self.client.get('/api/v1/tf/stations/catalog',params={'q':'BBB'},headers={'X-CTL-Area':'backend'}).status_code,403)
