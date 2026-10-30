"""Version 0.2 point-in-time validation and evidence-based research."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from math import isfinite
from copy import deepcopy

CATEGORIES=('producer','swap_dealer','managed_money','other_reportable')
MODULES=('macro','cftc','etf_physical','central_banks','liquidity','options')
# metric: module, canonical unit, instruments, markets, frequencies, min, max
DICTIONARY={
 'real_yield_10y':('macro','percent',('US_TIPS_10Y',),('US',),('daily',),-20,50),
 'nominal_yield_2y':('macro','percent',('US_TREASURY_2Y',),('US',),('daily',),-20,100),
 'nominal_yield_10y':('macro','percent',('US_TREASURY_10Y',),('US',),('daily',),-20,100),
 'breakeven_10y':('macro','percent',('US_BREAKEVEN_10Y',),('US',),('daily',),-20,100),
 'usd_index':('macro','index',('DTWEXBGS',),('US',),('daily',),0,10000),
 'gold_tonnes':('central_banks','tonnes',('MONETARY_GOLD',),('OFFICIAL_RESERVES',),('monthly',),0,100000),
 'etf_tonnes':('etf_physical','tonnes',('GOLD_ETF',),('GLOBAL',),('daily','monthly'),0,100000),
 'liquidity_proxy':('liquidity','index',('LIQUIDITY_PROXY',),('US',),('daily','weekly','monthly'),-1e12,1e12),
 'put_call_ratio':('options','ratio',('GOLD_OPTIONS',),('COMEX',),('daily','weekly'),0,10000),
 'gold_price':('etf_physical','USD/troy_oz',('XAUUSD','GC','LBMA_PM','LBMA_AM'),('SPOT','COMEX','LBMA'),('daily','monthly'),0,1e7),
}
for k in ('long','short','spreading','open_interest','reportable_long','reportable_short','nonreportable_long','nonreportable_short'):
 DICTIONARY[k]=('cftc','contracts',('GC',),('COMEX',),('weekly',),0,10**10)
SOURCE_TYPES=('official','licensed','user_supplied','synthetic')

def timestamp(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00'))
 if d.tzinfo is None: raise ValueError('timestamp requires timezone')
 return d.astimezone(timezone.utc)

def number(v):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v): raise ValueError('expected finite number')
 return float(v)

def validate_observation(o):
 required=('module','metric','value','unit','instrument','market','observation_frequency','source_type','observed_at','published_at','retrieved_at','source','url','vintage')
 if any(k not in o or o[k] in ('',None) for k in required): raise ValueError('missing provenance or dictionary field')
 if o['metric'] not in DICTIONARY: raise ValueError('unknown metric '+str(o['metric']))
 mod,unit,instruments,markets,freq,low,high=DICTIONARY[o['metric']]
 if o['module']!=mod or o['instrument'] not in instruments or o['market'] not in markets or o['observation_frequency'] not in freq: raise ValueError('invalid metric dimensions')
 if o['source_type'] not in SOURCE_TYPES or not isinstance(o['source'],str) or not str(o['url']).startswith(('https://','synthetic://')): raise ValueError('invalid source')
 v=number(o['value']); u=o['unit']
 if u=='basis_points' and unit=='percent':
  if o.get('conversion_rule')!='basis_points_to_percent': raise ValueError('basis points require explicit conversion rule')
  v/=100
 elif u!=unit: raise ValueError('invalid unit for '+o['metric'])
 if not low<=v<=high or (o['metric']=='gold_price' and v<=0): raise ValueError('value out of range')
 if unit=='contracts' and v!=int(v): raise ValueError('contracts must be integers')
 observed,published,retrieved=(timestamp(o[k]) for k in ('observed_at','published_at','retrieved_at'))
 if not observed<=published<=retrieved: raise ValueError('invalid observation/publication/retrieval order')
 if o.get('vintage_available_at') and not published<=timestamp(o['vintage_available_at'])<=retrieved: raise ValueError('invalid vintage availability')
 if mod=='central_banks' and not o.get('country'): raise ValueError('central bank requires country')
 if mod=='cftc':
  for k in ('contract_market_id','report_type','report_date'):
   if not o.get(k): raise ValueError('CFTC missing '+k)
  if o['report_type']!='disaggregated_futures_only' or o['contract_market_id']!='088691': raise ValueError('unsupported CFTC report/market')
  if timestamp(o['report_date'])!=observed: raise ValueError('CFTC report date mismatch')
  if o['metric'] in ('long','short') and o.get('category') not in CATEGORIES: raise ValueError('invalid CFTC category')
  if o['metric']=='spreading' and o.get('category') not in CATEGORIES[1:]: raise ValueError('invalid CFTC spreading category')
 return o

def normalized_value(o):
 return number(o['value'])/100 if o['unit']=='basis_points' else number(o['value'])

def key(o):
 return (o['module'],o['metric'],o['instrument'],o['market'],o.get('country',''),o.get('category',''),o.get('contract_market_id',''),o.get('report_type',''),timestamp(o['observed_at']))

def asof(observations,when,mode='strict_archive'):
 if mode not in ('strict_archive','historical_reconstruction'): raise ValueError('invalid PIT mode')
 t=timestamp(when); groups={}; versions={}; releases={}
 for o in observations:
  validate_observation(o); k=key(o); pub=timestamp(o['published_at']); ret=timestamp(o['retrieved_at'])
  # Same exact release and vintage must not change by input order.
  vk=(k,pub,o['vintage']); v=normalized_value(o)
  if vk in versions and versions[vk]!=v: raise ValueError('conflicting values for same key and vintage')
  versions[vk]=v
  release_key=(k,pub)
  if release_key in releases and releases[release_key]!=v: raise ValueError('ambiguous conflicting values at same release time')
  releases[release_key]=v
  if pub>t or (mode=='strict_archive' and ret>t): continue
  if mode=='historical_reconstruction' and (not o.get('publication_evidence') or not o.get('vintage_available_at') or timestamp(o['vintage_available_at'])>t): continue
  candidate=(pub,str(o['vintage']),ret)
  if k not in groups or candidate>groups[k][0]: groups[k]=(candidate,deepcopy(o))
 return [groups[k][1] for k in sorted(groups,key=lambda x:tuple(str(y) for y in x))]

def metric_result(value,formula,window,n,at,valid,reason=None):
 return {'value':value,'formula':formula,'window':window,'sample_count':n,'data_cutoff':at,'valid':valid,'missing_reason':reason}

def changes(rows,metric):
 r=sorted((o for o in rows if o['metric']==metric),key=lambda x:timestamp(x['observed_at']))
 if len(r)<21: return metric_result(None,'latest minus value 20 observations earlier','20 observations',len(r),r[-1]['observed_at'] if r else None,False,'need 21 distinct observations')
 r=r[-21:]; dates=[timestamp(o['observed_at']).date() for o in r]; start,end=dates[0],dates[-1]
 weekdays=sum((start+timedelta(days=i)).weekday()<5 for i in range((end-start).days+1))
 observed_weekdays=len({d for d in dates if d.weekday()<5}); coverage=observed_weekdays/weekdays if weekdays else 0
 gaps=[(b-a).days for a,b in zip(dates,dates[1:])]; maxgap=max(gaps,default=0)
 warnings=[]
 if coverage<.8: warnings.append('weekday coverage below 80%; exchange holidays not adjusted')
 if maxgap>7: warnings.append('gap exceeds seven calendar days')
 if len(set(dates))!=21: warnings.append('duplicate dates')
 if any(d.weekday()>=5 for d in dates): warnings.append('weekend observations require manual verification')
 result=metric_result(normalized_value(r[-1])-normalized_value(r[0]) if not warnings else None,'latest minus value 20 observations earlier','20 observations',21,r[-1]['observed_at'],not warnings,'; '.join(warnings) if warnings else None)
 result.update(start_date=start.isoformat(),end_date=end.isoformat(),expected_weekdays=weekdays,observed_weekdays=observed_weekdays,weekday_coverage=coverage,max_gap_calendar_days=maxgap,warnings=warnings,calendar_method='weekday approximation; holidays not adjusted')
 return result

def month(o):
 d=timestamp(o['observed_at']); return d.year*12+d.month

def central(rows,now,config,limit):
 countries=sorted(set(config.get('core',[])+config.get('extended',[])) | {o['country'] for o in rows})
 anchor=config.get('report_month'); target=None
 if anchor:
  try:
   parsed=datetime.strptime(anchor,'%Y-%m'); target=parsed.year*12+parsed.month
  except ValueError: raise ValueError('central report_month must be YYYY-MM')
 result={}; valid=0; groups={'COMPARABLE':[],'UNREPORTED':[],'STALE':[],'NONCOMPARABLE':[]}; comparable=[]
 def compute(bymonth,end,n):
  months=range(end-n,end+1)
  if not all(len(bymonth[m])==1 for m in months): return {'value':None,'status':'MISSING_OR_DUPLICATE_MONTH'}
  seq=[bymonth[m][0] for m in months]
  # comparability is a documented source/series/methodology identity; a publication vintage is allowed to change.
  identities={(o['source'],o.get('series_id'),o.get('methodology_id'),o['unit']) for o in seq}
  if len(identities)!=1 or not all(o.get('series_id') and o.get('methodology_id') for o in seq): return {'value':None,'status':'UNVERIFIED_COMPARABILITY'}
  return {'value':normalized_value(seq[-1])-normalized_value(seq[0]),'status':'COMPARABLE','actual_months':n,'vintages':[o['vintage'] for o in seq]}
 for c in countries:
  rr=sorted((o for o in rows if o.get('country')==c and o['metric']=='gold_tonnes'),key=lambda x:timestamp(x['observed_at']))
  if not rr:
   result[c]={'coverage_status':'MISSING','latest_holdings_tonnes':None}; groups['UNREPORTED'].append(c); continue
  x=rr[-1]; stale=(now-timestamp(x['observed_at'])).total_seconds()/86400>limit
  if not stale: valid+=1
  bymonth=defaultdict(list)
  for o in rr:bymonth[month(o)].append(o)
  ch={str(n):compute(bymonth,month(x),n) for n in (1,3,6,12)}
  streak=0
  while streak<120:
   v=compute(bymonth,month(x)-streak,1)
   if v['status']!='COMPARABLE' or v['value']<=0: break
   streak+=1
  if target is None: status='UNREPORTED'
  elif len(bymonth[target])==0: status='UNREPORTED'
  elif len(bymonth[target])>1: status='NONCOMPARABLE'
  elif (now-timestamp(bymonth[target][0]['observed_at'])).total_seconds()/86400>limit: status='STALE'
  else:
   v=compute(bymonth,target,1); status='COMPARABLE' if v['status']=='COMPARABLE' else 'NONCOMPARABLE'
   if status=='COMPARABLE': comparable.append(v['value'])
  groups[status].append(c)
  result[c]={'latest_observation':x['observed_at'],'reported_month':timestamp(x['observed_at']).strftime('%Y-%m'),'publication_date':x['published_at'],'source':x['source'],'coverage_status':'STALE' if stale else 'CURRENT','latest_holdings_tonnes':normalized_value(x),'previous_period_change':ch['1'],'changes_months':ch,'positive_holding_change_streak_months':streak,'data_revision_status':'selected point-in-time vintages; verify source revisions','vintage':x['vintage'],'inferred_net_purchase':None,'breadth_status':status}
 core=config.get('core',[]); coregood=sum(result[c]['coverage_status']=='CURRENT' for c in core)
 return {'countries':result,'coverage':{'core_valid':coregood,'core_total':len(core),'core_ratio':coregood/len(core) if core else None,'all_valid':valid,'all_total':len(countries),'all_ratio':valid/len(countries) if countries else None},'buying_breadth':{'report_month':anchor,'positive_holding_change_countries':sum(x>0 for x in comparable),'comparable_countries':len(comparable),'country_status':groups,'interpretation':'same-month holdings change only; not confirmed net purchases'}}

def cftc(rows,tolerance=0):
 tolerance=number(tolerance)
 if tolerance<0: raise ValueError('negative CFTC tolerance')
 groups=defaultdict(list)
 for o in rows:
  if o['module']=='cftc': groups[(timestamp(o['observed_at']),o['contract_market_id'],o['report_type'],timestamp(o['published_at']))].append(o)
 reports=[]
 for k,rs in sorted(groups.items()):
  vals={(o['metric'],o.get('category','')):normalized_value(o) for o in rs}
  needed=[('long',c) for c in CATEGORIES]+[('short',c) for c in CATEGORIES]+[('spreading',c) for c in CATEGORIES[1:]]+[(x,'') for x in ('open_interest','reportable_long','reportable_short','nonreportable_long','nonreportable_short')]
  missing=[str(x) for x in needed if x not in vals]
  meta=rs[0]; sem=meta.get('publication_time_semantics','operator supplied exact publication time'); bounded=sem.startswith('conservative next midnight')
  result={'report_date':k[0].isoformat(),'contract_market_id':k[1],'report_type':k[2],'release_date':None if bounded else k[3].isoformat(),'availability_bound_at':k[3].isoformat() if bounded else None,'source_updated_date':meta.get('source_update_date'),'source_evidence_url':meta.get('publication_evidence'),'publication_time_semantics':sem,'missing_fields':missing,'validation_passed':False}
  if not missing:
   spread=sum(vals['spreading',c] for c in CATEGORIES[1:]); oi=vals['open_interest','']
   side={s:sum(vals[s,c] for c in CATEGORIES)+spread for s in ('long','short')}
   errors={s:{'classified_minus_reportable':side[s]-vals['reportable_'+s,''],'reportable_plus_nonreportable_minus_oi':vals['reportable_'+s,'']+vals['nonreportable_'+s,'']-oi} for s in ('long','short')}
   valid=oi>0 and all(abs(v)<=tolerance for s in errors.values() for v in s.values())
   mm=vals['long','managed_money']-vals['short','managed_money']
   result.update(open_interest=oi,positions={c:{'long':vals['long',c],'short':vals['short',c],'net':vals['long',c]-vals['short',c],'spreading':vals.get(('spreading',c))} for c in CATEGORIES},nonreportable={'long':vals['nonreportable_long',''],'short':vals['nonreportable_short','']},totals_check=errors,tolerance_contracts=tolerance,validation_passed=valid,managed_money_net=mm,managed_money_net_oi=mm/oi if oi else None)
  reports.append(result)
 good=[r for r in reports if r['validation_passed']]
 if good:
  current=good[-1]; prev=good[-2] if len(good)>1 else None
  current['changes']={'long':current['positions']['managed_money']['long']-prev['positions']['managed_money']['long'] if prev else None,'short':current['positions']['managed_money']['short']-prev['positions']['managed_money']['short'] if prev else None,'net':current['managed_money_net']-prev['managed_money_net'] if prev else None,'previous_report_date':prev['report_date'] if prev else None}
  current['net_percentile']=sum(r['managed_money_net']<=current['managed_money_net'] for r in good)/len(good) if len(good)>=20 else None
  current['percentile_sample_count']=len(good)
 # Never replace a failed most recent report with an older clean one.
 return {'latest':reports[-1] if reports else None,'valid_report_count':len(good),'reports':reports,'interpretation':'categories are not named traders, flows, or directional intent'}

def report(data):
 now=timestamp(data['as_of']); raw=data['observations']; mode=data.get('pit_mode','strict_archive'); rows=asof(raw,data['as_of'],mode)
 issues=[]; statuses={}
 for mod in MODULES:
  rs=[x for x in rows if x['module']==mod]; latest=max((timestamp(x['observed_at']) for x in rs),default=None)
  limit=number(data.get('max_age_days',{}).get(mod,0)); stale=bool(latest and (now-latest).total_seconds()/86400>limit)
  statuses[mod]={'status':'MISSING' if not rs else ('STALE' if stale else 'AVAILABLE'),'latest_observation':latest.isoformat() if latest else None,'source_count':len({x['source'] for x in rs})}
  if not rs or stale: issues.append(mod+': '+statuses[mod]['status'])
  if mod not in ('central_banks','cftc'):
   dimensions={(x['metric'],x['instrument'],x.get('country',''),x.get('category','')) for x in rs}
   for metric,instrument,country,category in dimensions:
    latest_dim=max(timestamp(x['observed_at']) for x in rs if (x['metric'],x['instrument'],x.get('country',''),x.get('category',''))==(metric,instrument,country,category))
    if (now-latest_dim).total_seconds()/86400>limit: issues.append(mod+': stale metric '+metric)
 for mod,metric in (('macro','real_yield_10y'),('macro','usd_index'),('etf_physical','etf_tonnes'),('central_banks','gold_tonnes'),('liquidity','liquidity_proxy'),('options','put_call_ratio')):
  if not any(x['module']==mod and x['metric']==metric for x in rows): issues.append('missing metric '+mod+'.'+metric)
 if mode=='historical_reconstruction' and any(timestamp(x['published_at'])<=now and (not x.get('publication_evidence') or not x.get('vintage_available_at')) for x in raw): issues.append('PIT publication evidence missing; potential look-ahead')
 cb=central([r for r in rows if r['module']=='central_banks'],now,data.get('central_bank_coverage',{}),number(data.get('max_age_days',{}).get('central_banks',0)))
 ct=cftc(rows,data.get('cftc_tolerance_contracts',0))
 if not ct['latest'] or not ct['latest']['validation_passed']: issues.append('CFTC latest report incomplete or inconsistent')
 core=cb['coverage'];
 if core['core_total'] and core['core_valid']<core['core_total']: issues.append('central bank core coverage incomplete')
 factors={'real_yield_10y_20_observation_change':changes(rows,'real_yield_10y'),'usd_index_20_observation_change':changes(rows,'usd_index')}
 latest_ct=ct['latest']
 if latest_ct and latest_ct['validation_passed']:
  t=latest_ct['report_date']; n=latest_ct['percentile_sample_count']; ch=latest_ct['changes']
  factors.update({'managed_money_net':metric_result(latest_ct['managed_money_net'],'managed money long minus short','one report',1,t,True),'managed_money_net_oi':metric_result(latest_ct['managed_money_net_oi'],'managed money net divided by open interest','one report',1,t,True),'managed_money_net_percentile':metric_result(latest_ct['net_percentile'],'fraction of valid reports with net <= latest','all available valid reports',n,t,n>=20,None if n>=20 else 'need at least 20 reports'),'managed_money_long_change':metric_result(ch['long'],'current long minus previous valid report','two valid reports',2 if ch['long'] is not None else 1,t,ch['long'] is not None,None if ch['long'] is not None else 'previous report unavailable'),'managed_money_short_change':metric_result(ch['short'],'current short minus previous valid report','two valid reports',2 if ch['short'] is not None else 1,t,ch['short'] is not None,None if ch['short'] is not None else 'previous report unavailable')})
 risk=data.get('risk'); action='NOT_AVAILABLE'; final='观望'; riskstate=[]
 if risk:
  try:
   w=number(risk['portfolio_weight']); cap=number(risk['max_gold_weight'])
   if not 0<=w<=1 or not 0<cap<=1: raise ValueError('invalid position cap')
   action='BLOCK_ADD' if w>=cap else 'WITHIN_LIMIT'; riskstate.append(action)
   if w>cap: action='REDUCE_CANDIDATE'; riskstate.append('OVER_CAP')
   if 'loss_fraction' in risk or 'max_loss_fraction' in risk:
    loss=number(risk['loss_fraction']); stop=number(risk['max_loss_fraction'])
    if not 0<=loss<=1 or not 0<stop<=1: raise ValueError('invalid loss limits')
    if loss>=stop and w>0: action='REDUCE_CANDIDATE'; riskstate.append('STOP_THRESHOLD')
  except (KeyError,TypeError): raise ValueError('incomplete risk configuration')
  if action=='REDUCE_CANDIDATE': final='减仓候选'
  elif w>0: final='无模型建议'
 if issues and action!='REDUCE_CANDIDATE': final='数据不足'
 hypothesis=data.get('research_hypothesis','observe')
 if hypothesis not in ('bullish','neutral','bearish','observe'): raise ValueError('invalid hypothesis')
 return {'chinese_summary':f'研究状态：仅供研究；数据问题 {len(issues)} 项；人工假设：{hypothesis}；风控状态：{action}；未校准模型，不构成交易指令。','schema_version':'0.3.0','as_of':data['as_of'],'pit_mode':mode,'pit_quality':'ARCHIVED_AT_DECISION' if mode=='strict_archive' else ('RECONSTRUCTED_WITH_PUBLICATION_EVIDENCE' if not any('PIT publication' in x for x in issues) else 'POTENTIAL_LOOKAHEAD'),'market_signal':{'type':'MANUAL_HYPOTHESIS','hypothesis':hypothesis},'risk_action':action,'risk_status':riskstate,'final_action':final,'model_status':'UNCALIBRATED','data_quality_status':'INSUFFICIENT_DATA' if issues else 'AVAILABLE_UNVERIFIED','signal_confidence':'NOT_ESTIMATED','model_signal_eligible':False,'market_research_judgment':'RESEARCH_ONLY','source_status':statuses,'factors':factors,'cftc':ct,'central_banks':cb,'issues':issues,'observations_used':rows,'audit_input_records':deepcopy(raw),'warnings':['No validated predictive model or automatic trading.','Manual hypothesis is not a model signal.','Country holdings change is not confirmed buying.']}

def validate_price_contract(data):
 """Require one explicit price series identity for CLI drawdown/backtest."""
 contract=data.get('price_contract',{})
 for field in ('instrument','market','price_type','currency','unit','provider','observation_frequency'):
  if not contract.get(field): raise ValueError('price_contract missing '+field)
 allowed={'XAUUSD':('SPOT',('spot_close',)), 'GC':('COMEX',('futures_settlement','futures_close')), 'LBMA_AM':('LBMA',('fixing',)), 'LBMA_PM':('LBMA',('fixing',))}
 instrument=contract['instrument']
 if instrument not in allowed or contract['market']!=allowed[instrument][0] or contract['price_type'] not in allowed[instrument][1] or contract['currency']!='USD' or contract['unit']!='troy_oz' or contract['observation_frequency'] not in ('daily','monthly'):
  raise ValueError('invalid or mixed price contract')
 for row in data['prices']:
  if any(k in row and row[k]!=contract[k] for k in contract): raise ValueError('mixed price series')
