# Regressionstests für Streckenkenntnisse und Referenzgeometrie.
import unittest
from unittest.mock import patch
from lokzeitleiste.route_knowledge_mapping import mileage,match
class RouteMappingTest(unittest.TestCase):
    def row(self,route='1000',a='AAA',b='BBB'):return dict(route_number=route,from_code=a,to_code=b)
    def test_mileage_and_exact_matching_and_no_gap_bridging(self):
        self.assertEqual(mileage('170,9 + 58'),170958);self.assertEqual(mileage('-0,1 + 50'),-50);self.assertIsNone(mileage(''))
        points={('1000','AAA'):[dict(km='0,0 + 0')],('1000','BBB'):[dict(km='1,0 + 0')]}
        with patch('lokzeitleiste.route_knowledge_mapping.reference',return_value=(points,{'1000':[[0,400],[600,1000]]},'hash')):
            result=match(self.row());self.assertEqual(result['status'],'partial');self.assertEqual((result['from_m'],result['to_m']),(0,1000))
            self.assertEqual(match(self.row('0'))['status'],'missing_route');self.assertEqual(match(self.row(a='AA A'))['status'],'missing_endpoint')
            points[('1000','AAA')].append(dict(km='0,1 + 0'));self.assertEqual(match(self.row())['status'],'ambiguous_endpoint')
    def test_missing_mileage_not_fabricated_and_complete_mapping(self):
        points={('1000','AAA'):[dict(km='')],('1000','BBB'):[dict(km='1,0 + 0')]}
        with patch('lokzeitleiste.route_knowledge_mapping.reference',return_value=(points,{'1000':[[0,1000]]},'hash')):
            self.assertEqual(match(self.row())['status'],'missing_mileage');points[('1000','AAA')][0]['km']='0,0 + 0'
            self.assertEqual(match(self.row())['status'],'mapped');self.assertEqual(match(self.row(a='BBB',b='AAA'))['from_m'],1000)
            self.assertEqual(match(self.row('9999'))['status'],'missing_geometry')
