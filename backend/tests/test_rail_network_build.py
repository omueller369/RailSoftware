import gzip,hashlib,importlib.util,json,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('rail_build',ROOT/'tools/build-rail-network.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class RailNetworkBuildTest(unittest.TestCase):
    def test_multiline_stays_disconnected_and_invalid_coordinates_fail(self):
        lines=build.parse_wkt('MULTILINESTRING ((13 52,13.001 52),(14 53,14.001 53))')
        self.assertEqual(len(lines),2);self.assertEqual(lines[0][-1],[13.001,52]);self.assertEqual(lines[1][0],[14,53])
        for text in ['LINESTRING (nan 52,13 52)','LINESTRING (181 52,13 52)','LINESTRING (13 52)','POINT (13 52)']:
            with self.assertRaises(ValueError):build.parse_wkt(text)

    def test_simplification_keeps_endpoints_and_bends(self):
        self.assertEqual(build.simplify([[0,0],[1,0],[2,0]],.1),[[0,0],[2,0]])
        self.assertEqual(build.simplify([[0,0],[1,2],[2,0]],.5),[[0,0],[1,2],[2,0]])
        self.assertEqual(build.project([0,0]),[50000000,50000000])

    def test_supplied_dataset_provenance_and_compressed_offline_bundle(self):
        reference=ROOT/'backend/lokzeitleiste/reference/rail-network'
        manifest=json.loads((reference/'manifest.json').read_text())
        raw=(reference/'m1-network.json.gz').read_bytes();data=json.loads(gzip.decompress(raw))
        self.assertEqual(hashlib.sha256(raw).hexdigest(),manifest['canonical_sha256'])
        self.assertEqual(data['source']['source_rows'],33425);self.assertEqual(data['source']['route_count'],1549)
        self.assertEqual(len(data['records']),manifest['source']['line_count'])
        script=build.OUTPUT.read_bytes()
        self.assertEqual(hashlib.sha256(script).hexdigest(),manifest['bundle_sha256'])
        self.assertEqual(gzip.decompress(build.COMPRESSED.read_bytes()),script)
        self.assertLess(build.COMPRESSED.stat().st_size,3*1024*1024)
        self.assertTrue(all(len(row[3])>=2 and row[2] in (0,1,2) for row in data['records']))
