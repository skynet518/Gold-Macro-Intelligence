"""Bounded, long/flat walk-forward research; no broker and no automatic signal promotion."""
from datetime import datetime,timezone
from math import isfinite
from statistics import median
from .research import DICTIONARY

# Only provider/series pairs whose identity is explicitly defined by this project.
KNOWN_SERIES={
 "real_yield_10y":("DFII10","FRED"),
 "nominal_yield_2y":("DGS2","FRED"),
 "nominal_yield_10y":("DGS10","FRED"),
 "breakeven_10y":("T10YIE","FRED"),
 "usd_index":("DTWEXBGS","FRED"),
}

def validate_feature_semantics(feature,contracts):
 metric=feature["metric"];unit=feature["unit"];series=feature["series_id"];source=feature["source_id"];url=feature.get("source_url")
 if metric in DICTIONARY:
  expected_unit=DICTIONARY[metric][1]; low,high=DICTIONARY[metric][5:7]
  if not low<=num(feature['value'])<=high:raise ValueError('value outside known metric range')
  if unit!=expected_unit:raise ValueError("invalid unit for known metric "+metric)
  if metric not in KNOWN_SERIES:raise ValueError("known metric lacks registered walk-forward series/source mapping: "+metric)
  known_series,known_source=KNOWN_SERIES[metric]
  if (series,source)!=(known_series,known_source) or url!="https://fred.stlouisfed.org/series/"+known_series:raise ValueError("incompatible series/source for known metric "+metric)
  return
 if not isinstance(contracts,list):raise ValueError("custom feature contracts must be a list")
 matches=[c for c in contracts if isinstance(c,dict) and c.get("metric")==metric]
 if len(matches)!=1:raise ValueError("unknown metric requires exactly one explicit custom feature contract")
 contract=matches[0];required=("metric","unit","series_id","source_id","source_url","description","min_value","max_value")
 if any(k not in contract for k in required) or not isinstance(contract["description"],str) or not contract["description"].strip():raise ValueError("custom feature definition is incomplete")
 if any(not isinstance(contract[k],str) or not contract[k].strip() for k in ("metric","unit","series_id","source_id","source_url")):raise ValueError("invalid custom feature identity")
 if any(feature.get(k)!=contract[k] for k in ("metric","unit","series_id","source_id","source_url")):raise ValueError("custom feature identity does not match contract")
 low=num(contract["min_value"]);high=num(contract["max_value"])
 if low>high or not low<=num(feature["value"])<=high:raise ValueError("custom feature value outside defined range")

def dt(x):
 d=datetime.fromisoformat(x.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('timezone required')
 return d.astimezone(timezone.utc)
def num(x):
 if isinstance(x,bool) or not isinstance(x,(int,float)) or not isfinite(x):raise ValueError('finite numeric value required')
 return float(x)

def validate_rows(rows,custom_contracts=None):
 previous_exit=None; identity=None; feature_identity=None
 for row in rows:
  f=row['feature']; p=row['execution'];decision=dt(row['decision_at']);obs=dt(f['observed_at']);pub=dt(f['published_at']);ret=dt(f['retrieved_at']);vintage=dt(f['vintage_available_at'])
  num(f['value'])
  if f.get('feature_type')!='raw_observation':raise ValueError('only raw observations allowed; derived factor lineage is not verified')
  required=('metric','unit','series_id','source_id','transformation')
  if any(not isinstance(f.get(k),str) or not f[k].strip() for k in required):raise ValueError('missing feature identity: metric, unit, series_id, source_id and transformation required')
  if f['transformation']!='identity':raise ValueError('derived or transformed features require verified lineage and are not supported')
  feature_key=tuple(f[k] for k in required)+(f.get('source_url'),)
  if feature_identity is None:feature_identity=feature_key
  elif feature_key!=feature_identity:raise ValueError('incompatible feature identity or source')
  validate_feature_semantics(f,custom_contracts or [])
  if not obs<=pub<=vintage<=ret<=decision:raise ValueError('feature not point-in-time available at decision')
  if not f.get('source_url','').startswith('https://') or not f.get('vintage_evidence','').startswith('https://') or not f.get('vintage_id'):raise ValueError('missing feature vintage evidence')
  if f.get('evidence_status') not in ('USER_ATTESTED','INDEPENDENTLY_VERIFIED'):raise ValueError('feature evidence status required')
  entry,exit=dt(p['entry_at']),dt(p['exit_at'])
  if entry<=decision or exit<=entry or (previous_exit and decision<previous_exit):raise ValueError('overlapping or future-looking execution times')
  if p.get('price_type') not in ('daily_close','futures_settlement'):raise ValueError('monthly average or non-executable price rejected')
  if not p.get('source_url','').startswith('https://') or not p.get('instrument') or p.get('currency')!='USD':raise ValueError('price contract and source required')
  if num(p['entry_price'])<=0 or num(p['exit_price'])<=0:raise ValueError('invalid price')
  key=(p['instrument'],p['price_type'],p['currency'])
  if identity is None:identity=key
  elif key!=identity:raise ValueError('mixed price contract')
  previous_exit=exit
 return identity

def split_windows(length,train_size,validation_size,test_size):
 if any(isinstance(x,bool) or not isinstance(x,int) or x<1 for x in (train_size,validation_size,test_size)):raise ValueError('positive integer split sizes required')
 out=[];start=0
 while start+train_size+validation_size+test_size<=length:
  t=start+train_size;v=t+validation_size;e=v+test_size
  out.append({'train':(start,t),'validation':(t,v),'test':(v,e)})
  start+=test_size
 return out

def performance(rows,threshold,config,benchmark=False):
 cost=(num(config['transaction_cost_bps'])+num(config['slippage_bps']))/10000
 cash=num(config['cash_annual_rate']); funding=num(config['funding_annual_rate'])
 if not 0<=cost<1 or not -0.99<cash<=1 or not 0<=funding<=1:raise ValueError('invalid cost or rate')
 equity=peak=1.; maxdd=0.;previous=0; turnover=0.;cost_paid=0.
 for row in rows:
  p=row['execution']; position=1 if benchmark or num(row['feature']['value'])>=threshold else 0
  turn=abs(position-previous);before=equity;cost_paid+=before*turn*cost;equity*=1-turn*cost;turnover+=turn
  duration=(dt(p['exit_at'])-dt(p['entry_at'])).total_seconds()/(365*86400)
  asset=num(p['exit_price'])/num(p['entry_price'])-1
  period=asset-funding*duration if position else cash*duration
  if period<=-1:raise ValueError('period loss exceeds equity')
  equity*=1+period;peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1);previous=position
 # Terminal liquidation at last exit, included in benchmark and strategy.
 if previous:
  cost_paid+=equity*cost;equity*=1-cost;turnover+=1;maxdd=min(maxdd,equity/peak-1)
 return {'sample_count':len(rows),'total_return':equity-1,'max_drawdown':maxdd,'turnover':turnover,'cost_paid_initial_equity_units':cost_paid,'cash_annual_rate':cash,'funding_annual_rate':funding,'transaction_cost_bps':config['transaction_cost_bps'],'slippage_bps':config['slippage_bps']}

def walk_forward(rows,config):
 for k in ('train_size','validation_size','test_size','transaction_cost_bps','slippage_bps','cash_annual_rate','funding_annual_rate'):
  if k not in config:raise ValueError('missing explicit configuration '+k)
 contract=validate_rows(rows,config.get('custom_feature_contracts',[]));windows=split_windows(len(rows),config['train_size'],config['validation_size'],config['test_size'])
 if not windows:return {'status':'NO_GO','reason':'insufficient rows for train, validation and test','windows':[],'model_signal':'NO_VALIDATED_SIGNAL'}
 out=[]
 for w in windows:
  train=rows[slice(*w['train'])];val=rows[slice(*w['validation'])];test=rows[slice(*w['test'])]
  center=median(num(r['feature']['value']) for r in train)
  # Candidate offsets are fixed before looking at validation; no test data used in selection.
  candidates=[center-0.1,center,center+0.1];evaluations=[performance(val,t,config) for t in candidates]
  best=max(range(len(candidates)),key=lambda i:(evaluations[i]['total_return'],-i)); threshold=candidates[best]
  out.append({'train_indices':list(w['train']),'validation_indices':list(w['validation']),'test_indices':list(w['test']),'training_median':center,'candidate_thresholds':candidates,'validation_results':evaluations,'selected_threshold':threshold,'out_of_sample':performance(test,threshold,config),'benchmark':performance(test,threshold,config,True)})
 return {'status':'RESEARCH_ONLY','model_signal':'NO_VALIDATED_SIGNAL','reason':'mechanical checks do not establish independent evidence or sufficient statistical validation','price_contract':list(contract),'walk_forward_windows':out,'limitations':['Input evidence is operator-attested; URLs are not independently verified.','No model signal promotion or broker execution.','Non-overlapping interval returns; gaps between intervals carry no interest. Drawdown is observed at interval exits, not intraday.','Cash and funding are simple annual rates, not a complete futures financing model.','Transaction costs and slippage are explicit research assumptions.']}
