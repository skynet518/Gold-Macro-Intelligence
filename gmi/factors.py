"""Six factor research interfaces, time-ordered ranks and descriptive associations.

No trading decisions, optimization, or point-in-time claims for snapshot data.
"""
from math import sqrt,isfinite
from .events import month_end,add_months,last_before,FRED

SPECS={
 'macro':{'fields':['real_yield_change_3m','usd_index_change_3m'],'formula':'mean(-rank(real yield 3m change), -rank(broad dollar 3m change))','direction':'rising yield and broad dollar assumed negative for gold, unvalidated','window':'36 prior monthly observations, minimum 24','source':'Federal Reserve Board via FRED DFII10, DTWEXBGS'},
 'cftc':{'fields':['managed_money_net_oi'],'formula':'-rank(managed money net contracts / open interest)','direction':'higher net concentration treated as crowded, unvalidated','window':'12 prior monthly observations, minimum 6','source':'CFTC disaggregated futures-only'},
 'etf_physical':{'fields':['etf_physical_change'],'formula':'rank(comparable holdings or physical demand change)','direction':'positive demand assumed supportive, unvalidated','window':'36 prior monthly observations, minimum 24','source':'issuer/official or licensed data supplied by user'},
 'central_banks':{'fields':['central_bank_breadth'],'formula':'rank(fraction of comparable countries with positive same-month holdings change)','direction':'broader positive holdings assumed supportive, unvalidated','window':'36 prior monthly observations, minimum 24','source':'IMF / central banks, country-month aligned'},
 'liquidity':{'fields':['liquidity_stress'],'formula':'-rank(user-defined liquidity stress)','direction':'higher stress assumed negative, unvalidated','window':'36 prior monthly observations, minimum 24','source':'Federal Reserve / authorized provider'},
 'options':{'fields':['option_stress'],'formula':'-rank(user-defined comparable option stress)','direction':'higher stress assumed negative, unvalidated','window':'36 prior monthly observations, minimum 24','source':'exchange / authorized provider'},
}
DEFAULT_WEIGHTS={k:1/6 for k in SPECS}

def rank_prior(current,history,minimum,window):
 h=history[-window:]
 if len(h)<minimum:return None
 # Ties use midpoint. History must be strictly prior to current; no full-sample fit.
 less=sum(v<current for v in h);equal=sum(v==current for v in h)
 return 2*((less+0.5*equal)/len(h))-1

def factor_packet(name,month,value,score,n,valid,reason,source_time=None):
 spec=SPECS[name]
 return {'factor':name,'as_of_month':month,'value':value,'normalized_score':score,'formula':spec['formula'],'direction':spec['direction'],'window':spec['window'],'sample_count':n,'source':spec['source'],'latest_observation_date':source_time,'publication_time':'UNKNOWN_UNVERIFIED','vintage':'CURRENT_SNAPSHOT_NOT_PIT','coverage':1.0 if valid else 0.0,'status':'AVAILABLE_UNCALIBRATED' if valid else 'INSUFFICIENT_DATA','reason':reason,'pit_eligible':False}

def score_factors(packets,weights=None,min_factors=2):
 weights=DEFAULT_WEIGHTS if weights is None else weights
 if set(weights)!=set(SPECS) or any(not isinstance(v,(int,float)) or not isfinite(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:raise ValueError('invalid factor weights')
 if not isinstance(min_factors,int) or not 1<=min_factors<=6:raise ValueError('invalid min_factors')
 for k,p in packets.items():
  score=p.get('normalized_score')
  if score is not None and (not isinstance(score,(int,float)) or isinstance(score,bool) or not isfinite(score) or not -1<=score<=1):raise ValueError('invalid normalized factor score')
 months={p.get('as_of_month') for p in packets.values() if p.get('normalized_score') is not None}
 if len(months)>1:raise ValueError('factor months are not aligned')
 total=sum(weights.values());eligible={k:v for k,v in packets.items() if k in weights and v.get('normalized_score') is not None and v.get('status')=='AVAILABLE_UNCALIBRATED' and weights[k]>0}
 used=sum(weights[k] for k in eligible);coverage=used/total
 value=sum(weights[k]*v['normalized_score'] for k,v in eligible.items())/used if len(eligible)>=min_factors and used else None
 return {'score':value,'score_type':'RESEARCH_SCORE' if value is not None else 'INSUFFICIENT_DATA','model_status':'UNCALIBRATED','weighted_coverage':coverage,'available_factors':list(eligible),'missing_factors':[k for k in SPECS if k not in eligible],'weights':weights,'min_factors':min_factors,'warning':'renormalizes available weights only for research; not optimized or a trading signal'}

def calendar_history(current_month,history,window,minimum):
 """Bound history by actual preceding calendar months; duplicates fail closed."""
 start=add_months(current_month,-window); selected={}
 for m,v in history:
  if start<=m<current_month:
   if m in selected:raise ValueError('duplicate calendar month in rolling history')
   selected[m]=v
 expected=[add_months(current_month,-i) for i in range(window,0,-1)]
 missing=[m for m in expected if m not in selected]
 info={'window_start':start,'window_end':add_months(current_month,-1),'expected_months':window,'available_months':len(selected),'missing_months':missing,'coverage':len(selected)/window,'minimum_observations':minimum}
 return [selected[m] for m in expected if m in selected],info

def monthly_macro(months,macro):
 samples={k:{} for k in ('DFII10','DTWEXBGS')}
 for m in months:
  d=month_end(m)
  for series in samples:samples[series][m]=last_before(macro[series]['values'],d)
 history={'real':[],'usd':[]}; result={}
 for m in months:
  prev=add_months(m,-3);now_r=samples['DFII10'][m];now_u=samples['DTWEXBGS'][m];old_r=samples['DFII10'].get(prev,{});old_u=samples['DTWEXBGS'].get(prev,{})
  def diff(a,b):return a['value']-b['value'] if a.get('status')=='AVAILABLE' and b.get('status')=='AVAILABLE' else None
  real=diff(now_r,old_r);usd=diff(now_u,old_u)
  rh,ri=calendar_history(m,history['real'],36,24);uh,ui=calendar_history(m,history['usd'],36,24)
  rr=rank_prior(real,rh,24,36) if real is not None else None;ur=rank_prior(usd,uh,24,36) if usd is not None else None
  n=min(len(rh),len(uh));valid=rr is not None and ur is not None
  packet=factor_packet('macro',m,{'real_yield_change_3m':real,'usd_index_change_3m':usd},-(rr+ur)/2 if valid else None,n,valid,None if valid else 'missing current input or fewer than 24 observations in preceding 36 calendar months',{'DFII10':now_r.get('observation_date'),'DTWEXBGS':now_u.get('observation_date')})
  packet['window_quality']={'real_yield':ri,'usd':ui}; result[m]=packet
  if real is not None:history['real'].append((m,real))
  if usd is not None:history['usd'].append((m,usd))
 return result

def monthly_cftc(months,reports):
 from .events import cftc_at
 history=[];result={}
 for m in months:
  pos=cftc_at(reports,m);value=pos.get('net_oi') if pos['status']=='AVAILABLE' else None
  prev,quality=calendar_history(m,history,12,6)
  r=rank_prior(value,prev,6,12) if value is not None else None
  net=pos.get('long')-pos.get('short') if pos.get('long') is not None and pos.get('short') is not None else None
  matched=next((r for r in reports if r['report_date'][:10]==pos.get('report_date') and r['validation_passed']),None)
  packet=factor_packet('cftc',m,{'managed_money_long':pos.get('long'),'managed_money_short':pos.get('short'),'managed_money_net':net,'open_interest':matched.get('open_interest') if matched else None,'managed_money_net_oi':value,'managed_money_long_change':pos.get('long_change'),'managed_money_short_change':pos.get('short_change'),'net_change':pos.get('long_change')-pos.get('short_change') if pos.get('long_change') is not None and pos.get('short_change') is not None else None,'oi_concentration_direction':'crowding hypothesis'},-r if r is not None else None,len(prev),r is not None,None if r is not None else 'position missing or fewer than six prior calendar-month observations',pos.get('report_date'))
  packet['availability_bound_at']=pos.get('availability_bound_at');packet['window_quality']=quality;result[m]=packet
  if value is not None:history.append((m,value))
 return result

def pearson(xs,ys):
 if len(xs)!=len(ys) or len(xs)<2:return None
 mx=sum(xs)/len(xs);my=sum(ys)/len(ys);a=sum((x-mx)**2 for x in xs);b=sum((y-my)**2 for y in ys)
 return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sqrt(a*b) if a>0 and b>0 else None

def associations(prices,factor_by_month,horizon,minimum=30):
 # t factor -> monthly mean t+1 is descriptive baseline, followed by t+1+h; never join price definitions.
 pairs=[]
 for i,p in enumerate(prices):
  if i+1+horizon>=len(prices):continue
  packet=factor_by_month.get(p['month'],{});value=packet.get('normalized_score')
  if value is None:continue
  pairs.append((p['month'],value,prices[i+1+horizon]['price']/prices[i+1]['price']-1))
 n=len(pairs);base={'horizon_months':horizon,'sample_count':n,'sample_start':pairs[0][0] if pairs else None,'sample_end':pairs[-1][0] if pairs else None,'formula':'factor at month t vs return of monthly mean from t+1 to t+1+h','signal_standardization':'trailing-only, excludes current and future','pit_eligible':False,'limitations':'descriptive snapshot; monthly means not executable; overlapping forward returns; no significance or causal claims'}
 if n<minimum:return dict(base,status='INSUFFICIENT_DATA',correlation=None,first_half=None,second_half=None,minimum=minimum)
 def calc(a):return pearson([x[1] for x in a],[x[2] for x in a])
 cut=n//2;return dict(base,status='EXPLORATORY_ONLY',correlation=calc(pairs),first_half=calc(pairs[:cut]),second_half=calc(pairs[cut:]),minimum=minimum)

def research(prices_by_segment,macro,reports,source_info,weights=None,supplement=None):
 allprices=sorted([p for v in prices_by_segment.values() for p in v],key=lambda p:p['month']);months=[p['month'] for p in allprices]
 macro_packets=monthly_macro(months,macro);cftc_packets=monthly_cftc(months,reports)
 available=[m for m in months if macro_packets[m]['normalized_score'] is not None or cftc_packets[m]['normalized_score'] is not None];current=available[-1] if available else months[-1]
 packets={'macro':macro_packets[current],'cftc':cftc_packets[current]}
 for k in SPECS:
  if k not in packets:packets[k]=generic_factor(k,current,supplement.get(k,[])) if supplement and k in supplement else factor_packet(k,current,None,None,0,False,'source data not supplied')
 associations_by_factor={}
 for factor,values in [('macro',macro_packets),('cftc',cftc_packets)]:
  associations_by_factor[factor]={segment:[associations(prices,values,h) for h in (1,3,6,12)] for segment,prices in prices_by_segment.items()}
 return {'schema_version':'0.5.0','as_of_observation_month':current,'model_status':'UNCALIBRATED','decision':'RESEARCH_ONLY','factor_packets':packets,'research_score':score_factors(packets,weights),'validation':associations_by_factor,'data_sources':source_info,'limitations':['Exploratory in-sample correlations only, not independent OOS validation or statistical proof.','FRED and annual CFTC snapshots downloaded later, missing point-in-time vintage; possible look-ahead bias.','World Bank monthly means cannot define execution price, and release time is unknown.','No future observations enter percentile normalization; overlapping horizons reduce independent information.','Four modules are missing; no missing factor is set to zero.']}

def generic_factor(name,month,observations,decision_at=None,max_reporting_lag_months=3):
 """Select latest reporting period actually published and retrieved by decision_at.

 `month` labels the decision month; `decision_at` optionally sets exact UTC cutoff.
 Publication, retrieval and revisions are input assertions, not verified evidence.
 """
 from datetime import datetime,timezone
 if name not in ('etf_physical','central_banks','liquidity','options'):raise ValueError('unsupported generic factor')
 def dt(x):
  z=datetime.fromisoformat(x.replace('Z','+00:00'))
  if z.tzinfo is None:raise ValueError('timestamp requires timezone')
  return z.astimezone(timezone.utc)
 cutoff=dt(decision_at) if decision_at else datetime.combine(month_end(month),datetime.max.time(),tzinfo=timezone.utc)
 if cutoff.strftime('%Y-%m')!=month:raise ValueError('decision timestamp must be in decision month')
 metric=SPECS[name]['fields'][0]; rows={};identity=None; versions={}
 for o in observations:
  required=('metric','value','observed_at','published_at','retrieved_at','source','vintage','unit','series_id')
  if any(not o.get(k) and o.get(k)!=0 for k in required):raise ValueError('factor observation missing provenance')
  if o['metric']!=metric:continue
  observed,published,retrieved=map(dt,(o['observed_at'],o['published_at'],o['retrieved_at']))
  if not observed<=published<=retrieved:raise ValueError('invalid observation chronology')
  if published>cutoff or retrieved>cutoff:continue
  ident=(o['source'],o['series_id'],o['unit']);value=o['value']
  if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value):raise ValueError('invalid factor value')
  if name=='central_banks' and not 0<=value<=1:raise ValueError('central-bank breadth must be between zero and one')
  if identity is None:identity=ident
  elif ident!=identity:raise ValueError('incomparable factor series')
  period=observed.strftime('%Y-%m');version_key=(period,published,str(o['vintage']))
  if version_key in versions and versions[version_key]!=value:raise ValueError('conflicting monthly factor values')
  versions[version_key]=value
  cand=(published,retrieved,str(o['vintage']))
  if period in rows and rows[period][0][:2]==cand[:2] and rows[period][1]['value']!=value:raise ValueError('conflicting monthly factor values')
  if period not in rows or cand>rows[period][0]:rows[period]=(cand,o)
 if rows:
  observed_month=max(rows);current=rows[observed_month][1]
  history,quality=calendar_history(observed_month,[(k,v[1]['value']) for k,v in rows.items() if k<observed_month],36,24)
 else:observed_month=None;current=None;history=[];quality={'expected_months':36,'available_months':0,'coverage':0.0,'missing_months':[]}
 val=current['value'] if current else None
 lag=(int(month[:4])-int(observed_month[:4]))*12+int(month[5:])-int(observed_month[5:]) if observed_month else None
 if not isinstance(max_reporting_lag_months,int) or max_reporting_lag_months<0:raise ValueError('invalid reporting lag')
 stale=lag is not None and lag>max_reporting_lag_months
 r=rank_prior(val,history,24,36) if val is not None and not stale else None
 sign=-1 if name in ('liquidity','options') else 1
 result=factor_packet(name,month,val,sign*r if r is not None else None,len(history),r is not None,None if r is not None else 'stale observation' if stale else 'no available observation or fewer than 24 observations in preceding 36 calendar months',current.get('observed_at') if current else None)
 result.update(source=current.get('source') if current else SPECS[name]['source'],pit_eligible=False,reporting_month=observed_month,decision_at=cutoff.isoformat(),reporting_lag_months=lag,window_quality=quality)
 result['input_metadata']={k:current[k] for k in ('unit','series_id','observed_at','published_at','retrieved_at','vintage')} if current else None
 return result

def render_research(data):
 lines=['# GMI 六因子研究与初步关联检验','',f"观察月：{data['as_of_observation_month']}；模型状态：UNCALIBRATED；仅研究，不生成交易信号。",'', '| 因子 | 状态 | 覆盖 | 研究标准分 |','|---|---|---:|---:|']
 labels={'macro':'实际利率与美元','cftc':'CFTC 管理基金拥挤度','etf_physical':'ETF 与实物','central_banks':'央行','liquidity':'跨资产流动性','options':'黄金期权结构'}
 for k,p in data['factor_packets'].items():lines.append(f"| {labels[k]} | {p['status']} | {p['coverage']:.0%} | {round(p['normalized_score'],3) if p['normalized_score'] is not None else '缺失'} |")
 x=data['research_score'];lines += ['',f"研究总分：{round(x['score'],3) if x['score'] is not None else '数据不足，不计算'}；有效权重覆盖 {x['weighted_coverage']:.1%}。默认等权是未校准假设，缺失因子不按零处理。",'', '## 历史关联（探索性、非严格 PIT）','', '| 因子 / 价格段 | 未来月数 | 样本数 | 相关系数 | 前半 / 后半 | 状态 |','|---|---:|---:|---:|---|---|']
 def fmt(x):return '缺失' if x is None else f'{x:.3f}'
 for f,segments in data['validation'].items():
  for segment,results in segments.items():
   for r in results:lines.append(f"| {labels[f]} / {segment} | {r['horizon_months']} | {r['sample_count']} | {fmt(r['correlation'])} | {fmt(r['first_half'])} / {fmt(r['second_half'])} | {r['status']} |")
 lines+=['','相关系数为样本内 Pearson；因子标准化只使用当前之前的滚动样本，价格收益按 t+1 的月平均价至 t+1+h 的月平均价计算。不同价格定义分段，未拼接；月均价不是可执行价格。多个期限的未来收益重叠，不能把样本数当作独立交易次数。','', 'FRED 与 CFTC 历史版本和实际发布时间未逐条验证，结果只能作为探索性关联，不能解释为无前瞻偏差或样本外验证；也不能推断因果、交易胜率或预测能力。ETF、央行、流动性及期权由于缺乏符合合同的数据，保留接口并标记缺失。']
 return '\n'.join(lines)+'\n'
