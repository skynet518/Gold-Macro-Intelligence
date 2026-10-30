import copy, json, unittest
from pathlib import Path
from gmi.core import report, drawdowns, survival, backtest, asof
P=Path(__file__).resolve().parents[1]/'examples'
def fixture(name): return json.loads((P/(name+'.json')).read_text())
class GMITests(unittest.TestCase):
 def test_example_decision_and_categories(self):
  r=report(fixture('analysis')); self.assertEqual(r['final_action'],'无模型建议'); self.assertFalse(r['issues']); self.assertEqual(r['cftc']['latest']['managed_money_net'],0)
 def test_missing_stale_and_risk_fail_closed(self):
  x=fixture('analysis'); x['observations']=[o for o in x['observations'] if o['module']!='options']; self.assertEqual(report(x)['data_quality_status'],'INSUFFICIENT_DATA')
  x=fixture('analysis'); x['max_age_days']['macro']=1; self.assertEqual(report(x)['data_quality_status'],'INSUFFICIENT_DATA')
  x=fixture('analysis'); del x['risk']; self.assertEqual(report(x)['risk_action'],'NOT_AVAILABLE')
 def test_cap_overrides_hypothesis(self):
  x=fixture('analysis'); x['research_hypothesis']='bullish'; x['risk']['portfolio_weight']=.3
  self.assertEqual(report(x)['risk_action'],'BLOCK_ADD')
 def test_future_revision_and_retrieval_excluded(self):
  x=fixture('analysis'); old=x['observations'][0]; rev=copy.deepcopy(old); rev.update(value=3,published_at='2024-01-04T00:00:00Z',vintage_available_at='2024-01-04T00:00:00Z',retrieved_at='2024-01-04T01:00:00Z',vintage='v2'); x['observations'].append(rev)
  self.assertEqual(next(o['value'] for o in asof(x['observations'],x['as_of']) if o['metric']=='real_yield_10y'),1.5)
  rev['published_at']='2024-01-02T00:30:00Z'; rev['vintage_available_at']='2024-01-02T00:30:00Z'; self.assertEqual(next(o['value'] for o in asof(x['observations'],x['as_of']) if o['metric']=='real_yield_10y'),1.5)
 def test_revisions_select_latest_available(self):
  x=fixture('analysis'); rev=copy.deepcopy(x['observations'][0]); rev.update(value=2,published_at='2024-01-02T02:00:00Z',vintage_available_at='2024-01-02T02:00:00Z',retrieved_at='2024-01-02T03:00:00Z',vintage='v2'); x['observations'].append(rev)
  self.assertEqual(next(o['value'] for o in asof(x['observations'],x['as_of']) if o['metric']=='real_yield_10y'),2)
 def test_drawdown_and_censoring(self):
  e=drawdowns(fixture('prices')['prices']); self.assertEqual(len(e),2); self.assertTrue(e[0]['recovered']); self.assertTrue(e[1]['right_censored']); self.assertIsNone(e[1]['recovery_days_from_trough']); self.assertAlmostEqual(e[0]['drawdown'],-.2)
  self.assertEqual(survival(e)[-1]['unrecovered_probability'],0.0)
 def test_backtest_next_close(self):
  b=fixture('backtest'); b['one_way_cost_bps']=0; r=backtest(b)
  self.assertAlmostEqual(r['final_equity'],100/90); self.assertEqual(r['records'][0]['position_after_close'],1)
 def test_lookahead_signal_rejected(self):
  b=fixture('backtest'); b['signals'][0]['available_at']='2024-01-02T00:00:00Z'
  with self.assertRaises(ValueError): backtest(b)
 def test_invalid_prices_rejected(self):
  b=fixture('prices')['prices']; b[1]['price']=0
  with self.assertRaises(ValueError): drawdowns(b)
 def test_cftc_pair_mismatch_blocked(self):
  x=fixture('analysis'); x['observations']=[o for o in x['observations'] if not(o.get('category')=='producer' and o['metric']=='short')]
  self.assertEqual(report(x)['data_quality_status'],'INSUFFICIENT_DATA')
if __name__=='__main__': unittest.main()
