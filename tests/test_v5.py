import copy,json,tempfile,unittest
from datetime import date,datetime,timezone
from pathlib import Path
from gmi.events import last_before,macro_data,study,render_study
from gmi.factors import rank_prior,score_factors,generic_factor,associations,monthly_macro,SPECS
P=Path(__file__).resolve().parents[1]
class V5Tests(unittest.TestCase):
 def test_conflicting_same_day_is_rejected(self):
  rows=[(date(2020,1,30),1.2),(date(2020,1,30),2.3)]
  for r in (rows,list(reversed(rows))):
   with self.assertRaisesRegex(ValueError,'conflicting'):last_before(r,date(2020,1,31))
 def test_duplicate_equal_is_safe(self):
  self.assertEqual(last_before([(date(2020,1,30),1),(date(2020,1,30),1)],date(2020,1,31))['value'],1)
 def test_csv_conflict_rejected_before_ranking(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);b=b'observation_date,DFII10\n2020-01-30,1\n2020-01-30,2\n';(p/'DFII10.csv').write_bytes(b);(p/'DFII10.meta.json').write_text(json.dumps({'sha256':hashlib.sha256(b).hexdigest()}))
   with self.assertRaisesRegex(ValueError,'conflicting FRED'):macro_data(p)
 @unittest.skipUnless((P/'evidence/gmi_historical_events_2026-10.json').is_file() and (P/'sources/v5/v040_fred_anchors.json').is_file() and (P/'sources/cftc_disaggregated_futures_2025.zip').is_file() and (P/'sources/v3/cftc_disaggregated_futures_2026.zip').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_fixed_event_anchors_reproduce_v04(self):
  old=json.loads((P/'evidence/gmi_historical_events_2026-10.json').read_text())
  inputs=[(P/'sources/cftc_disaggregated_futures_2025.zip',P/'sources/v3/cftc_release_bounds_2025.json'),(P/'sources/v3/cftc_disaggregated_futures_2026.zip',P/'sources/v3/cftc_release_bounds_2026_subset.json')]
  new=study(P/'sources/v4/world_bank_gold_fixing_monthly.csv',P/'sources/v4/world_bank_gold_spot_monthly.csv',None,inputs,'2026-10-30T05:00:00Z',fred_anchors=P/'sources/v5/v040_fred_anchors.json')
  self.assertEqual(old['events'],new['events']);self.assertEqual(old['survival'],new['survival']);self.assertEqual(render_study(new),(P/'evidence/gmi_historical_events_2026-10.md').read_text())
 @unittest.skipUnless((P/'sources/v4/world_bank_gold_fixing_monthly.csv').is_file() and (P/'sources/v4/world_bank_gold_spot_monthly.csv').is_file() and (P/'sources/v5/v040_fred_anchors.json').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_fixed_anchors_reject_changed_threshold(self):
  with self.assertRaisesRegex(ValueError,'original price data and threshold'):
   study(P/'sources/v4/world_bank_gold_fixing_monthly.csv',P/'sources/v4/world_bank_gold_spot_monthly.csv',None,[],'2026-10-30T05:00:00Z',threshold=.2,fred_anchors=P/'sources/v5/v040_fred_anchors.json')
 def test_score_gates_and_never_treat_missing_as_zero(self):
  p={'macro':{'normalized_score':0.5,'status':'AVAILABLE_UNCALIBRATED','as_of_month':'2024-01'}}
  self.assertIsNone(score_factors(p)['score']);self.assertAlmostEqual(score_factors(p)['weighted_coverage'],1/6)
  p['cftc']={'normalized_score':-0.1,'status':'AVAILABLE_UNCALIBRATED','as_of_month':'2024-01'};self.assertAlmostEqual(score_factors(p)['score'],0.2)
  p['cftc']['as_of_month']='2023-12'
  with self.assertRaisesRegex(ValueError,'aligned'):score_factors(p)
 def test_prior_rank_has_no_future_input(self):
  from gmi.events import add_months,month_end
  months=[add_months('2020-01',i) for i in range(60)]
  macro={k:{'values':[(month_end(m),float(i*i+1)) for i,m in enumerate(months)],'source':{}} for k in ('DFII10','DTWEXBGS')}
  short=monthly_macro(months[:40],macro);full=monthly_macro(months,macro)
  self.assertIsNotNone(short[months[39]]['normalized_score']);self.assertEqual(short[months[39]],full[months[39]])
  self.assertIsNone(rank_prior(12,list(range(23)),24,36))
 def test_generic_modules_accept_timed_samples_and_reject_conflicts(self):
  from gmi.events import add_months
  for name in ('etf_physical','central_banks','liquidity','options'):
   metric=SPECS[name]['fields'][0];obs=[]
   for i in range(25):
    m=add_months('2022-01',i);at=m+'-01T00:00:00Z';obs.append({'metric':metric,'value':i/24 if name=='central_banks' else i,'observed_at':at,'published_at':at,'retrieved_at':at,'source':'SYNTHETIC','vintage':'v1','unit':'index','series_id':'test'})
   out=generic_factor(name,'2024-01',obs);self.assertEqual(out['status'],'AVAILABLE_UNCALIBRATED');self.assertFalse(out['pit_eligible'])
   bad=copy.deepcopy(obs[-1]);bad['value']=0.5 if name=='central_banks' else 999
   with self.assertRaisesRegex(ValueError,'conflicting'):generic_factor(name,'2024-01',obs+[bad])
 def test_association_small_sample_is_not_validation(self):
  prices=[{'month':f'2020-{i:02d}','price':100+i} for i in range(1,10)]
  packets={x['month']:{'normalized_score':0.5} for x in prices};r=associations(prices,packets,1)
  self.assertEqual(r['status'],'INSUFFICIENT_DATA');self.assertIsNone(r['correlation'])
 def test_import_fred_rejects_duplicate_conflict(self):
  from gmi.adapters import import_fred
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fred.csv';p.write_text('observation_date,DFII10\n2020-01-30,1\n2020-01-30,2\n')
   with self.assertRaisesRegex(ValueError,'conflicting'):import_fred(p,'DFII10',{},'2024-01-01T00:00:00Z')
 def test_descriptive_fred_rejects_duplicate_conflict(self):
  import hashlib
  from gmi.update import descriptive_fred
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);b=b'observation_date,DFII10\n2020-01-30,1\n2020-01-30,2\n';(p/'DFII10.csv').write_bytes(b);(p/'DFII10.meta.json').write_text(json.dumps({'sha256':hashlib.sha256(b).hexdigest(),'retrieved_at':'2021-01-01T00:00:00Z'}))
   with self.assertRaisesRegex(ValueError,'conflicting'):descriptive_fred(p,'2022-01-01T00:00:00Z')
if __name__=='__main__':unittest.main()
