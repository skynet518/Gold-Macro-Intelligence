import copy,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from gmi.events import add_months
from gmi.factors import generic_factor,calendar_history
from gmi.walkforward import walk_forward,split_windows
from gmi.risk import decision
from gmi.snapshots import check_manifest
from gmi.audit import real_audit
P=Path(__file__).resolve().parents[1]
def observation(month,value,published):
 return {'metric':'central_bank_breadth','value':value,'observed_at':month+'-01T00:00:00Z','published_at':published,'retrieved_at':published,'source':'synthetic','vintage':'v1','unit':'fraction','series_id':'s'}
def rows(n):
 out=[];start=datetime(2020,1,1,tzinfo=timezone.utc)
 for i in range(n):
  d=start+timedelta(days=3*i);ds=d.isoformat();out.append({'decision_at':ds,'feature':{'value':(i%7)/10,'feature_type':'raw_observation','metric':'synthetic_indicator','unit':'index','series_id':'synthetic_series','source_id':'synthetic_provider','transformation':'identity','observed_at':ds,'published_at':ds,'vintage_available_at':ds,'retrieved_at':ds,'source_url':'https://example.org/data','vintage_evidence':'https://example.org/vintage','vintage_id':'synthetic-v1','evidence_status':'USER_ATTESTED'},'execution':{'entry_at':(d+timedelta(days=1)).isoformat(),'exit_at':(d+timedelta(days=2)).isoformat(),'entry_price':100,'exit_price':100+(i%3-1),'price_type':'daily_close','instrument':'SYNTHETIC','currency':'USD','source_url':'https://example.org/prices'}})
 return out
CFG={'train_size':6,'validation_size':4,'test_size':3,'transaction_cost_bps':3,'slippage_bps':2,'cash_annual_rate':0.01,'funding_annual_rate':0.0,'custom_feature_contracts':[{'metric':'synthetic_indicator','unit':'index','series_id':'synthetic_series','source_id':'synthetic_provider','source_url':'https://example.org/data','description':'Fictional dimensionless indicator for offline tests only','min_value':-1000,'max_value':1000}]}
class V6Tests(unittest.TestCase):
 def test_delayed_central_bank_reporting(self):
  data=[]
  for i in range(24):
   m=add_months('2022-01',i);data.append(observation(m,i/100,m+'-02T00:00:00Z'))
  data.append(observation('2024-01',.4,'2024-02-10T10:00:00Z'))
  a=generic_factor('central_banks','2024-02',data,decision_at='2024-02-09T23:00:00Z')
  b=generic_factor('central_banks','2024-02',data,decision_at='2024-02-10T10:00:00Z')
  self.assertEqual(a['reporting_month'],'2023-12');self.assertEqual(b['reporting_month'],'2024-01');self.assertEqual(b['value'],.4);self.assertEqual(b['reporting_lag_months'],1)
 def test_delayed_etf_is_available_only_after_retrieval(self):
  data=[]
  for i in range(24):
   m=add_months('2022-01',i);o=observation(m,i/100,m+'-02T00:00:00Z');o['metric']='etf_physical_change';data.append(o)
  o=observation('2024-01',.4,'2024-02-10T10:00:00Z');o['metric']='etf_physical_change';data.append(o)
  self.assertEqual(generic_factor('etf_physical','2024-02',data,decision_at='2024-02-09T23:00:00Z')['reporting_month'],'2023-12')
  self.assertEqual(generic_factor('etf_physical','2024-02',data,decision_at='2024-02-10T10:00:00Z')['reporting_month'],'2024-01')
 def test_sparse_generic_history_is_not_36_months(self):
  data=[observation(add_months('2018-01',i*2),i/100,add_months('2018-01',i*2)+'-02T00:00:00Z') for i in range(36)]
  r=generic_factor('central_banks','2024-01',data);self.assertIsNone(r['normalized_score']);self.assertLess(r['window_quality']['available_months'],24)
 def test_trading_costs_reduce_equal_strategy(self):
  from gmi.walkforward import performance
  a=rows(5);free=dict(CFG,transaction_cost_bps=0,slippage_bps=0);cost=dict(CFG,transaction_cost_bps=10,slippage_bps=10)
  self.assertLess(performance(a,-1,cost)['total_return'],performance(a,-1,free)['total_return'])
  self.assertGreater(performance(a,-1,cost)['cost_paid_initial_equity_units'],0)
 def test_retrieval_after_publication_blocks_selection(self):
  o=observation('2024-01',.3,'2024-02-01T00:00:00Z');o['retrieved_at']='2024-02-10T00:00:00Z'
  self.assertIsNone(generic_factor('central_banks','2024-02',[o],decision_at='2024-02-09T00:00:00Z')['reporting_month'])
 def test_revisions_follow_decision_cutoff(self):
  a=observation('2024-01',.3,'2024-02-01T00:00:00Z');b=observation('2024-01',.4,'2024-02-15T00:00:00Z');b['vintage']='v2'
  self.assertEqual(generic_factor('central_banks','2024-02',[a,b],decision_at='2024-02-10T00:00:00Z')['value'],.3)
  self.assertEqual(generic_factor('central_banks','2024-02',[a,b],decision_at='2024-02-20T00:00:00Z')['value'],.4)
 def test_calendar_window_not_observation_count(self):
  hist=[(add_months('2018-01',i*2),i) for i in range(36)]
  vals,q=calendar_history('2024-01',hist,36,24)
  self.assertEqual(len(vals),18);self.assertEqual(q['coverage'],.5);self.assertEqual(len(q['missing_months']),18)
 def test_stale_factor_blocks_score(self):
  data=[observation(add_months('2020-01',i),i/100,add_months('2020-01',i)+'-02T00:00:00Z') for i in range(25)]
  self.assertIsNone(generic_factor('central_banks','2025-01',data)['normalized_score'])
 def test_walkforward_splits_and_no_test_leak(self):
  a=rows(16);r=walk_forward(a,CFG);self.assertEqual(r['status'],'RESEARCH_ONLY');w=r['walk_forward_windows'][0]
  self.assertEqual(w['train_indices'],[0,6]);self.assertEqual(w['validation_indices'],[6,10]);self.assertEqual(w['test_indices'],[10,13]);self.assertEqual(r['model_signal'],'NO_VALIDATED_SIGNAL')
  b=copy.deepcopy(a)
  for row in b[10:13]:row['feature']['value']+=100
  self.assertEqual(w['selected_threshold'],walk_forward(b,CFG)['walk_forward_windows'][0]['selected_threshold'])
 def test_future_feature_not_available(self):
  a=rows(13);a[5]['feature']['retrieved_at']=(datetime.fromisoformat(a[5]['decision_at'])+timedelta(days=1)).isoformat()
  with self.assertRaisesRegex(ValueError,'point-in-time'):walk_forward(a,CFG)
 def test_monthly_average_not_executable(self):
  a=rows(13);a[0]['execution']['price_type']='monthly_average'
  with self.assertRaisesRegex(ValueError,'non-executable'):walk_forward(a,CFG)
 def test_insufficient_split_and_explicit_cost(self):
  self.assertEqual(walk_forward(rows(3),CFG)['status'],'NO_GO')
  c=CFG.copy();del c['slippage_bps']
  with self.assertRaisesRegex(ValueError,'missing explicit'):walk_forward(rows(13),c)
 def test_risk_limits_and_signal_independence(self):
  risk={'portfolio_weight':.2,'max_position_weight':.2,'portfolio_drawdown':.02,'max_portfolio_drawdown':.1,'risk_budget':.06,'asset_stress_loss':.3}
  r=decision('bullish',risk);self.assertEqual(r['risk_action'],'BLOCK_ADD');self.assertEqual(r['final_action'],'RESEARCH_ONLY')
  risk['portfolio_weight']=.21;r=decision('bullish',risk);self.assertEqual(r['risk_action'],'REDUCE_CANDIDATE');self.assertEqual(r['market_signal']['model_signal'],'NO_VALIDATED_SIGNAL')
  risk['portfolio_weight']=.1;risk['portfolio_drawdown']=.1;self.assertIn('DRAWDOWN_LIMIT',decision('neutral',risk)['risk_breaches'])
  risk['portfolio_drawdown']=.01;risk['risk_budget']=.02;self.assertIn('RISK_BUDGET',decision('observe',risk)['risk_breaches'])
  self.assertEqual(decision('bearish',None)['risk_action'],'RISK_INPUTS_MISSING')
 def test_synthetic_example_regression(self):
  raw=json.loads((P/'examples/v060_walkforward_synthetic.json').read_text());expected=json.loads((P/'examples/v060_walkforward_synthetic.expected.json').read_text())
  self.assertEqual(walk_forward(raw['rows'],raw['config']),expected)
  data=json.loads((P/'examples/v060_risk_synthetic.json').read_text());self.assertEqual(decision(data['market_hypothesis'],data['risk']),json.loads((P/'examples/v060_risk_synthetic.expected.json').read_text()))
 @unittest.skipUnless((P/'sources/v6/fred_snapshot_manifest.json').is_file() and (P/'sources/v4/world_bank_gold_fixing_monthly.csv').is_file() and (P/'sources/v4/world_bank_gold_spot_monthly.csv').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_real_audit_never_reports_synthetic_performance(self):
  with tempfile.TemporaryDirectory() as d:
   report=real_audit(d,P/'sources/v6/fred_snapshot_manifest.json',P/'sources/v4/world_bank_gold_fixing_monthly.csv',P/'sources/v4/world_bank_gold_spot_monthly.csv')
   self.assertEqual(report['validation_status'],'NO_GO');self.assertIsNone(report['out_of_sample']['return']);self.assertEqual(report['model_signal'],'NO_VALIDATED_SIGNAL')
if __name__=='__main__':unittest.main()
