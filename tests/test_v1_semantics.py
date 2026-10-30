import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_v6 import rows,CFG
from gmi.walkforward import walk_forward
from gmi.harness import run_fixture,verify
P=Path(__file__).resolve().parents[1]
class V1SemanticsTests(unittest.TestCase):
 def known_rows(self):
  a=rows(13)
  for row in a:row['feature'].update(metric='real_yield_10y',unit='percent',series_id='DFII10',source_id='FRED',source_url='https://fred.stlouisfed.org/series/DFII10')
  return a
 def test_all_identically_wrong_gold_tonnes_percent_rejected(self):
  a=rows(13)
  for row in a:row['feature'].update(metric='gold_tonnes',unit='percent',series_id='central_bank',source_id='FRED')
  with self.assertRaisesRegex(ValueError,'invalid unit'):walk_forward(a,CFG)
 def test_valid_dfii10_percent(self):
  self.assertEqual(walk_forward(self.known_rows(),CFG)['model_signal'],'NO_VALIDATED_SIGNAL')
 def test_wrong_known_series_or_source_rejected(self):
  for field,value in [('series_id','DGS10'),('source_id','UNKNOWN'),('source_url','https://other.example/series/DFII10')]:
   with self.subTest(field=field):
    a=self.known_rows()
    for row in a:row['feature'][field]=value
    with self.assertRaisesRegex(ValueError,'incompatible series/source'):walk_forward(a,CFG)
 def test_explicit_custom_contract_and_unknown_rejected(self):
  a=rows(13);self.assertEqual(walk_forward(a,CFG)['model_signal'],'NO_VALIDATED_SIGNAL')
  cfg=copy.deepcopy(CFG);del cfg['custom_feature_contracts']
  with self.assertRaisesRegex(ValueError,'explicit custom'):walk_forward(a,cfg)
  cfg=copy.deepcopy(CFG);cfg['custom_feature_contracts'][0]['description']=''
  with self.assertRaisesRegex(ValueError,'incomplete'):walk_forward(a,cfg)
 def test_known_metric_cannot_be_overridden_by_custom_contract(self):
  a=self.known_rows();cfg=copy.deepcopy(CFG);cfg['custom_feature_contracts'][0].update(metric='real_yield_10y',unit='tonnes')
  for row in a:row['feature']['unit']='tonnes'
  with self.assertRaisesRegex(ValueError,'invalid unit'):walk_forward(a,cfg)
 def test_future_information_rejected(self):
  a=self.known_rows();a[0]['feature']['retrieved_at']='2030-01-01T00:00:00Z'
  with self.assertRaisesRegex(ValueError,'point-in-time'):walk_forward(a,CFG)
 def test_json_layout_independent_and_content_sensitive(self):
  original=json.loads((P/'fixtures/gmi_portability_input.json').read_text())
  with tempfile.TemporaryDirectory() as d:
   paths=[]
   for i,text in enumerate([json.dumps(original,ensure_ascii=False,indent=2)+'\n',json.dumps(original,ensure_ascii=False,indent=4,sort_keys=True).replace('\n','\r\n')+'\r\n',json.dumps(original,ensure_ascii=True,separators=(',',':'))]):
    p=Path(d)/f'{i}.json';p.write_bytes(text.encode());paths.append(p)
   results=[run_fixture(x) for x in paths];self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
   obj=copy.deepcopy(original);obj['risk']['risk']['portfolio_weight']+=0.01;p=Path(d)/'changed.json';p.write_text(json.dumps(obj));self.assertNotEqual(run_fixture(p)['fixture_content_sha256'],results[0]['fixture_content_sha256'])
   out=Path(d)/'result.json';out.write_text(json.dumps(results[1]));self.assertEqual(verify(out,P/'fixtures/gmi_portability_expected.json')['comparison_status'],'MATCH')
   with patch('gmi.harness.__version__','999.0.0'):out.write_text(json.dumps(run_fixture(paths[0])))
   self.assertEqual(verify(out,P/'fixtures/gmi_portability_expected.json')['comparison_status'],'MISMATCH')
if __name__=='__main__':unittest.main()
