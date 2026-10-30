import copy,unittest
from test_v6 import rows,CFG
from gmi.walkforward import walk_forward
class IdentityTests(unittest.TestCase):
 def test_reject_each_incompatible_dimension(self):
  for field,value in [('metric','central_bank_gold'),('unit','tonnes'),('series_id','other'),('source_id','other-provider'),('source_url','https://other.example/data')]:
   with self.subTest(field=field):
    a=rows(13);a[5]['feature'][field]=value
    with self.assertRaisesRegex(ValueError,'incompatible feature identity'):walk_forward(a,CFG)
 def test_real_yield_percent_cannot_mix_with_gold_tonnes(self):
  a=rows(13)
  for row in a:row['feature'].update(metric='real_yield_10y',unit='percent',series_id='DFII10',source_id='FRED',source_url='https://fred.stlouisfed.org/series/DFII10')
  a[5]['feature'].update(metric='gold_tonnes',unit='tonnes',series_id='RESERVES',source_id='CENTRAL_BANK')
  with self.assertRaisesRegex(ValueError,'incompatible feature identity'):walk_forward(a,CFG)
 def test_missing_identity_fails_closed(self):
  for field in ('metric','unit','series_id','source_id','transformation'):
   with self.subTest(field=field):
    a=rows(13);del a[0]['feature'][field]
    with self.assertRaisesRegex(ValueError,'missing feature identity'):walk_forward(a,CFG)
 def test_derived_and_conversion_are_not_silently_allowed(self):
  for field,value in [('feature_type','derived'),('transformation','basis_points_to_percent')]:
   a=rows(13);a[0]['feature'][field]=value
   with self.assertRaises(ValueError):walk_forward(a,CFG)
 def test_homogeneous_feature_works(self):
  self.assertEqual(walk_forward(rows(13),CFG)['model_signal'],'NO_VALIDATED_SIGNAL')
if __name__=='__main__':unittest.main()
