import copy,json,unittest,subprocess,sys
from pathlib import Path
from gmi.research import validate_observation,asof,report,cftc
from gmi.adapters import import_cftc,import_fred
from gmi.core import conditional_drawdowns,drawdowns,survival,backtest
P=Path(__file__).resolve().parents[1]/'examples'
def load(n):return json.loads((P/n).read_text())
def first(x,metric):return next(o for o in x['observations'] if o['metric']==metric)
class V2Tests(unittest.TestCase):
 def test_wrong_yield_unit(self):
  o=first(load('analysis.json'),'real_yield_10y');o['unit']='tonnes'
  with self.assertRaises(ValueError):validate_observation(o)
  o['unit']='basis_points'
  with self.assertRaises(ValueError):validate_observation(o)
  o['conversion_rule']='basis_points_to_percent';validate_observation(o)
 def test_contract_must_be_integer(self):
  o=first(load('analysis.json'),'long');o['value']=1.5
  with self.assertRaises(ValueError):validate_observation(o)
 def test_utc_normalization(self):
  x=load('analysis.json');o=next(o for o in x['observations'] if o['metric']=='short' and o.get('category')=='managed_money');o['observed_at']='2023-12-31T19:00:00-05:00';o['report_date']=o['observed_at']
  self.assertTrue(report(x)['cftc']['latest']['validation_passed'])
 def test_same_vintage_conflicts_even_if_reordered(self):
  x=load('analysis.json');o=copy.deepcopy(first(x,'long'));o['value']+=1;x['observations'].append(o)
  for rows in (x['observations'],list(reversed(x['observations']))):
   with self.assertRaisesRegex(ValueError,'conflicting'):asof(rows,x['as_of'])
 def test_country_stale_isolated(self):
  x=load('analysis.json'); o=copy.deepcopy(first(x,'gold_tonnes'));o.update(country='Oldland',observed_at='2023-01-01T00:00:00Z');x['observations'].append(o);x['central_bank_coverage']['extended']=['Oldland'];r=report(x)
  self.assertEqual(r['central_banks']['countries']['Oldland']['coverage_status'],'STALE');self.assertEqual(r['central_banks']['countries']['Exampleland']['coverage_status'],'CURRENT')
 def test_missing_month_not_one_month_change(self):
  x=load('analysis.json');o=copy.deepcopy(first(x,'gold_tonnes'));o['observed_at']='2023-10-01T00:00:00Z';o['value']=400;x['observations'].append(o);r=report(x)['central_banks']['countries']['Exampleland']
  self.assertIsNone(r['previous_period_change']['value'])
 def test_cftc_different_report_date_not_combined(self):
  x=load('analysis.json');o=next(o for o in x['observations'] if o['metric']=='short' and o.get('category')=='managed_money');o['observed_at']=o['report_date']='2023-12-31T00:00:00Z'
  self.assertFalse(report(x)['cftc']['latest']['validation_passed'])
 def test_cftc_wrong_report_type_rejected(self):
  x=load('analysis.json');first(x,'long')['report_type']='combined'
  with self.assertRaises(ValueError):report(x)
 def test_hypothesis_never_becomes_model(self):
  x=load('analysis.json');x['research_hypothesis']='bullish';r=report(x)
  self.assertEqual(r['market_signal']['type'],'MANUAL_HYPOTHESIS');self.assertFalse(r['model_signal_eligible']);self.assertNotEqual(r['final_action'],'加仓候选')
 def test_cap_not_bearish_or_automatic_reduction(self):
  x=load('analysis.json');x['risk']['portfolio_weight']=x['risk']['max_gold_weight'];x['research_hypothesis']='bearish';r=report(x)
  self.assertEqual(r['risk_action'],'BLOCK_ADD');self.assertEqual(r['market_signal']['hypothesis'],'bearish');self.assertEqual(r['final_action'],'无模型建议')
 def test_archived_vs_reconstructed(self):
  x=load('analysis.json');o=copy.deepcopy(first(x,'real_yield_10y'));o['retrieved_at']='2024-02-01T00:00:00Z';o['vintage_available_at']=o['published_at']
  self.assertEqual(asof([o],x['as_of'],'strict_archive'),[]);self.assertEqual(len(asof([o],x['as_of'],'historical_reconstruction')),1)
  o['vintage_available_at']='2024-01-04T00:00:00Z';self.assertEqual(asof([o],x['as_of'],'historical_reconstruction'),[])
  del o['publication_evidence'];self.assertEqual(asof([o],x['as_of'],'historical_reconstruction'),[])
 def test_later_revision_never_enters_earlier(self):
  x=load('analysis.json');o=copy.deepcopy(first(x,'real_yield_10y'));o.update(value=3,published_at='2024-01-04T00:00:00Z',vintage_available_at='2024-01-04T00:00:00Z',retrieved_at='2024-02-01T00:00:00Z',vintage='revision');x['observations'].append(o)
  r=asof(x['observations'],x['as_of'],'historical_reconstruction');self.assertEqual(next(o['value'] for o in r if o['metric']=='real_yield_10y'),1.5)
 @unittest.skipUnless((P/'cftc_official_2025_12_23.csv').is_file() and (P/'cftc_releases.json').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_official_source_and_missing_release(self):
  x=import_cftc(P/'cftc_official_2025_12_23.csv',load('cftc_releases.json'),'2026-10-30T03:20:56Z');r=cftc(x['observations'])['latest'];self.assertEqual(r['open_interest'],492103);self.assertEqual(r['managed_money_net'],136270);self.assertTrue(r['validation_passed']);self.assertIsNone(r['net_percentile'])
  x=import_cftc(P/'cftc_official_2025_12_23.csv',{},'2026-10-30T03:20:56Z');self.assertEqual(x['observations'],[]);self.assertTrue(x['excluded_rows'])
 def test_fred_missing_release_and_missing_value(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fred.csv';p.write_text('observation_date,DFII10\n2024-01-01,.\n2024-01-02,1.5\n')
   r=import_fred(p,'DFII10',{},'2024-02-01T00:00:00Z');self.assertEqual(len(r['excluded_rows']),2);self.assertEqual(r['observations'],[])
   r=import_fred(p,'DFII10',{'2024-01-02':{'published_at':'2024-01-03T00:00:00Z','publication_evidence':'https://example.org','vintage_available_at':'2024-01-03T00:00:00Z'}},'2024-02-01T00:00:00Z');self.assertEqual(r['observations'][0]['value'],1.5)
 def test_expected_outputs_match(self):
  x=load('analysis.json');self.assertEqual(report(x),load('analysis.expected.json'))
  e=drawdowns(load('prices.json')['prices']);out=load('drawdowns.expected.json');self.assertEqual(e,out['episodes']);self.assertEqual(survival(e),out['survival']);self.assertEqual(conditional_drawdowns(load('prices.json')['prices']),out['conditional_from_first_crossing'])
  self.assertEqual(backtest(load('backtest.json')),load('backtest.expected.json'))
 def test_missing_risk_allows_report(self):
  x=load('analysis.json');del x['risk'];r=report(x);self.assertEqual(r['risk_action'],'NOT_AVAILABLE');self.assertTrue(r['cftc']['latest']['validation_passed'])
 def test_twenty_observation_change(self):
  from datetime import datetime,timedelta,timezone
  x=load('analysis.json'); x['observations']=[o for o in x['observations'] if o['metric']!='real_yield_10y']; base=first(load('analysis.json'),'real_yield_10y')
  days=[datetime(2023,12,1,tzinfo=timezone.utc)+timedelta(days=i) for i in range(40) if (datetime(2023,12,1,tzinfo=timezone.utc)+timedelta(days=i)).weekday()<5][:21]
  for i,dt in enumerate(days):
   o=copy.deepcopy(base);o['observed_at']=dt.isoformat();o['value']=i/10;x['observations'].append(o)
  v=report(x)['factors']['real_yield_10y_20_observation_change'];self.assertTrue(v['valid']);self.assertEqual(v['value'],2);self.assertEqual(v['sample_count'],21)
 def test_price_contract_rejects_mixed_series(self):
  from gmi.research import validate_price_contract
  x=load('prices.json');validate_price_contract(x);x['prices'][0]['instrument']='GC'
  with self.assertRaises(ValueError):validate_price_contract(x)
 @unittest.skipUnless((P/'cftc_real_research.json').is_file() and (P/'cftc_real_research.expected.json').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_real_report_expected_json(self):
  r=report(load('cftc_real_research.json'));self.assertEqual(r,load('cftc_real_research.expected.json'));self.assertEqual(r['data_quality_status'],'INSUFFICIENT_DATA')
if __name__=='__main__':unittest.main()
