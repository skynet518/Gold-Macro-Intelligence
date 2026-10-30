import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from gmi.research import central,changes,report
from gmi.adapters import import_cftc
from gmi.update import descriptive_fred
P=Path(__file__).resolve().parents[1]; ex=P/'examples'
def load(n):return json.loads((ex/n).read_text())
class V3Tests(unittest.TestCase):
 def country(self,name,month,value,vintage):
  o=copy.deepcopy(next(x for x in load('analysis.json')['observations'] if x['metric']=='gold_tonnes'))
  o.update(country=name,observed_at=month+'-01T00:00:00Z',value=value,vintage=vintage,series_id='gold-reserve',methodology_id='physical-tonnes-v1')
  return o
 def test_breadth_month_and_independent_vintage(self):
  r=[self.country('A','2023-12',100,'dec'),self.country('A','2024-01',110,'jan'),self.country('A','2024-02',120,'feb'),self.country('B','2023-12',200,'dec'),self.country('B','2024-01',190,'jan')]
  out=central(r,datetime(2024,2,3,tzinfo=timezone.utc),{'core':['A','B'],'report_month':'2024-02'},200)
  breadth=out['buying_breadth'];self.assertEqual(breadth['positive_holding_change_countries'],1);self.assertEqual(breadth['comparable_countries'],1);self.assertEqual(breadth['country_status']['UNREPORTED'],['B']);self.assertEqual(out['countries']['B']['latest_holdings_tonnes'],190)
  self.assertEqual(out['countries']['A']['positive_holding_change_streak_months'],2)
 def test_breadth_incomparable_and_stale(self):
  r=[self.country('A','2023-12',100,'v1'),self.country('A','2024-01',110,'v2')];r[1]['methodology_id']='changed'
  out=central(r,datetime(2024,1,3,tzinfo=timezone.utc),{'core':['A'],'report_month':'2024-01'},30);self.assertEqual(out['buying_breadth']['country_status']['NONCOMPARABLE'],['A'])
  out=central(r,datetime(2024,3,3,tzinfo=timezone.utc),{'core':['A'],'report_month':'2024-01'},30);self.assertEqual(out['buying_breadth']['country_status']['STALE'],['A'])
 def test_monthly_gaps_fail_twenty_observation(self):
  rows=[{'metric':'usd_index','unit':'index','value':100+i,'observed_at':f'{2020+i//12:04d}-{i%12+1:02d}-01T00:00:00Z'} for i in range(21)]
  out=changes(rows,'usd_index');self.assertFalse(out['valid']);self.assertIsNone(out['value']);self.assertLess(out['weekday_coverage'],0.8);self.assertGreater(out['max_gap_calendar_days'],7)
 def test_position_not_model_hold(self):
  x=load('analysis.json');self.assertEqual(report(x)['final_action'],'无模型建议')
  x['risk']['portfolio_weight']=0.4;self.assertEqual(report(x)['risk_action'],'REDUCE_CANDIDATE')
 @unittest.skipUnless((P/'sources/v3/cftc_release_bounds_2025.json').is_file() and (P/'sources/cftc_disaggregated_futures_2025.zip').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_cftc_all_2025_official_bounds(self):
  meta=json.loads((P/'sources/v3/cftc_release_bounds_2025.json').read_text());self.assertEqual(meta['matched_reports'],52);self.assertEqual(meta['bounded_reports'],52)
  x=import_cftc(P/'sources/cftc_disaggregated_futures_2025.zip',meta['mapping'],'2026-10-30T04:00:00Z')
  from gmi.research import cftc
  self.assertEqual(x['matched_rows'],52);self.assertFalse(x['excluded_rows']);self.assertEqual(cftc(x['observations'])['valid_report_count'],52)
  self.assertIn('not necessarily first release',x['observations'][0]['publication_time_semantics'])
 def test_fred_cache_hash_detects_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'DGS2.csv').write_text('observation_date,DGS2\n2025-01-01,2.0\n');(p/'DGS2.meta.json').write_text(json.dumps({'sha256':'bad','retrieved_at':'2025-01-02T00:00:00Z'}))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):descriptive_fred(p,'2025-01-03T00:00:00Z')
if __name__=='__main__':unittest.main()
