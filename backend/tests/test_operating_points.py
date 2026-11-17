import json,unittest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from lokzeitleiste.db import Base
from lokzeitleiste.models import RailwayStation,RailwayStationCoordinates,RailwayOperatingPoint
from lokzeitleiste.operating_points import load_points,seed_operating_points,route_references
from lokzeitleiste.accounts.station_coordinates import seed_coordinates

class OperatingPointsTest(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://');Base.metadata.create_all(self.engine);self.addCleanup(self.engine.dispose)
    def test_all_source_rows_preserved_and_idempotent_upgrade_keeps_custom_positions(self):
        data=load_points();self.assertEqual(len(data['points']),10632);self.assertEqual(len({r['code'] for r in data['points']}),7667)
        with Session(self.engine) as db:
            db.add(RailwayStation(code='WG G',name='Eigener Name'));db.add(RailwayStation(code='HD F',name='Delmenhorst Df'));db.flush()
            db.add(RailwayStationCoordinates(code='HD F',catalog_name='Delmenhorst Df',latitude=52,longitude=13,source_name='TF',source_url='https://example.org',source_date='2026-11',max_spread_m=0));db.commit()
            added=seed_operating_points(db);db.commit();self.assertGreater(added,10000)
            self.assertEqual(seed_operating_points(db),0);self.assertEqual(db.get(RailwayStation,'WG G').name,'Eigener Name')
            seed_coordinates(db);db.commit();self.assertIsNone(db.get(RailwayStationCoordinates,'WG G'))
            self.assertEqual(db.get(RailwayStationCoordinates,'HD F').latitude,52)
            refs=route_references(db,'1000',['AFW']);self.assertTrue(refs);self.assertTrue(all(r['route']=='1000' and r['code']=='AFW' for r in refs))
            self.assertTrue(any(r['code']=='WN G' for r in data['points']));self.assertTrue(any(r['code']=='WNG' for r in data['points']))
    def test_ambiguous_source_points_remain_distinct_without_centroids(self):
        points=[r for r in load_points()['points'] if r['code']=='AFW'];self.assertGreater(len(points),1)
        self.assertGreater(len({(r['lat'],r['lon']) for r in points}),1)
        with Session(self.engine) as db:
            seed_operating_points(db);db.commit()
            stored=[json.loads(r.payload_json) for r in db.scalars(select(RailwayOperatingPoint).where(RailwayOperatingPoint.code=='AFW'))]
            self.assertEqual({(r['route'],r['lat'],r['lon']) for r in stored},{(r['route'],r['lat'],r['lon']) for r in points})
            self.assertIsNone(db.get(RailwayStationCoordinates,'AFW'))
