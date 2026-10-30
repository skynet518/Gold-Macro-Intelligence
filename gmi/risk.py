"""Independent risk rules; no trade routing or automatic model promotion."""
from math import isfinite

def decision(market_hypothesis,risk):
 if market_hypothesis not in ('bullish','bearish','neutral','observe'):raise ValueError('invalid hypothesis')
 market={'type':'MANUAL_HYPOTHESIS','value':market_hypothesis,'model_signal':'NO_VALIDATED_SIGNAL'}
 required=('portfolio_weight','max_position_weight','portfolio_drawdown','max_portfolio_drawdown','risk_budget','asset_stress_loss')
 if not risk or any(k not in risk for k in required):return {'market_signal':market,'risk_action':'RISK_INPUTS_MISSING','final_action':'RESEARCH_ONLY','model_status':'NO_VALIDATED_SIGNAL'}
 vals=[]
 for k in required:
  v=risk[k]
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) or not 0<=v<=1:raise ValueError('risk fields must be finite fractions')
  vals.append(float(v))
 w,cap,dd,ddcap,budget,stress=vals
 if cap<=0 or ddcap<=0 or budget<=0 or stress<=0:raise ValueError('risk limits and stress must be positive')
 risk_cap=min(cap,budget/stress);breaches=[]
 if w>cap:breaches.append('POSITION_LIMIT')
 if w*stress>budget:breaches.append('RISK_BUDGET')
 if dd>=ddcap:breaches.append('DRAWDOWN_LIMIT')
 if breaches and w>0: action='REDUCE_CANDIDATE';final='RISK_REDUCE_CANDIDATE'
 elif w>=risk_cap or dd>=ddcap:action='BLOCK_ADD';final='RESEARCH_ONLY'
 else:action='WITHIN_LIMIT';final='RESEARCH_ONLY'
 return {'market_signal':market,'risk_action':action,'risk_breaches':breaches,'max_allowed_weight':risk_cap,'final_action':final,'model_status':'NO_VALIDATED_SIGNAL','warning':'risk thresholds are user assumptions; no order is sent'}
