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
        bundle=load_bundle();records=bundle['records'];self.assertEqual(len(records),6486)
        review=BUNDLE.with_name('station_coordinates_review.txt').read_text().splitlines()
        self.assertEqual(len(review),981);self.assertEqual(len(set(review)),981)
        self.assertFalse({row['code'] for row in records}&set(review))
        self.assertEqual(bundle['source_date'],'2026-05');self.assertEqual(bundle['license'],'CC-BY-4.0')
        with Session(self.engine) as db:
            seed_stations(db);self.assertEqual(seed_coordinates(db),6486);db.commit()
            self.assertEqual(db.scalar(select(func.count()).select_from(RailwayStation)),14928)
            self.assertEqual(seed_coordinates(db),0)
            row=db.get(RailwayStationCoordinates,'AABG');self.assertIsNotNone(row)
            self.assertTrue(47<=row.latitude<=56 and 5<=row.longitude<=16)
            self.assertEqual(row.source_date,'2026-05')
            self.assertIsNone(db.get(RailwayStationCoordinates,'AA'))

    def test_existing_catalog_upgrade_preserves_custom_names_and_deletions_once(self):
        records=json.loads(BUNDLE.with_name('stations.json').read_text())
        additions=set(BUNDLE.with_name('station_catalog_additions.txt').read_text().splitlines())
        self.assertEqual(len(additions),1166)
        with Session(self.engine) as db:
            legacy=[row for row in records if row['code'] not in additions and row['code']!='AABG']
            db.bulk_insert_mappings(RailwayStation,legacy)
            db.add(RailwayStation(code='AFS',name='Eigene Bezeichnung'));db.commit()
            self.assertEqual(seed_stations(db),1165);db.commit()
            self.assertEqual(db.get(RailwayStation,'AFS').name,'Eigene Bezeichnung')
            self.assertIsNone(db.get(RailwayStation,'AABG'),'Deleted legacy entries stay deleted')
            self.assertEqual(db.get(RailwayStation,'ALIN').name,'Lindaunis')
            self.assertEqual(seed_coordinates(db),6484);db.commit()
            self.assertIsNone(db.get(RailwayStationCoordinates,'AFS'))
            removed=db.get(RailwayStation,'ALIN');point=db.get(RailwayStationCoordinates,'ALIN')
            if point:db.delete(point);db.flush()
            db.delete(removed);db.commit()
            self.assertEqual(seed_stations(db),0,'Migration does not reinsert later user deletions')
            self.assertIsNone(db.get(RailwayStation,'ALIN'))

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

    def test_offline_snapshot_is_complete_private_and_hides_stale_coordinates(self):
        with Session(self.engine) as db:
            db.add_all([RailwayStation(code='X'+str(i),name='Zusatz '+str(i)) for i in range(50)])
            db.add(RailwayStationCoordinates(code='BBB',catalog_name='Berlin Beispiel',latitude=52.5,longitude=13.4,source_name='Berlin Beispiel',source_url='https://example.com/source',source_date='2026-05',max_spread_m=0));db.commit()
        response=self.driver.get('/api/v1/tf/stations/offline-catalog')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(response.json()['stations']),53)
        self.assertEqual(response.json()['coordinate_count'],1)
        self.assertEqual(response.json()['reference_revision'],json.loads(BUNDLE.with_name('station_catalog_manifest.json').read_text())['revision'])
        self.assertEqual(next(row for row in response.json()['stations'] if row[0]=='BBB'),['BBB','Berlin Beispiel',52.5,13.4])
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        with Session(self.engine) as db:db.get(RailwayStation,'BBB').name='Neuer Name';db.commit()
        response=self.driver.get('/api/v1/tf/stations/offline-catalog')
        self.assertEqual(response.json()['coordinate_count'],0)
        self.assertEqual(next(row for row in response.json()['stations'] if row[0]=='BBB'),['BBB','Neuer Name'])
        self.assertEqual(self.client.get('/api/v1/tf/stations/offline-catalog').status_code,403)
        self.driver.cookies.clear();self.assertEqual(self.driver.get('/api/v1/tf/stations/offline-catalog').status_code,401)
