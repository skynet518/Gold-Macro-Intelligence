"""Monthly historical drawdown and macro event description; not a strategy backtest."""
import calendar,csv,json,hashlib
from pathlib import Path
from datetime import date,datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from .core import drawdowns,survival
from .adapters import import_cftc
from .research import cftc

FRED=('DGS2','DGS10','DFII10','T10YIE','DTWEXBGS')
TARGETS=(('1974–1976','1974-01','1974-12'),('1980 年代熊市','1980-01','1980-12'),('2008','2008-01','2008-12'),('2011–2015','2011-01','2011-12'),('2020–2022','2020-01','2020-12'))

def month_end(m):
 y,mo=map(int,m.split('-'));return date(y,mo,calendar.monthrange(y,mo)[1])
def add_months(m,n):
 y,mo=map(int,m.split('-'));x=y*12+mo-1+n;return f'{x//12:04d}-{x%12+1:02d}'

def load_prices(path):
 with Path(path).open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
 out=[]
 for r in rows:
  m=r.get('month');v=float(r['price_usd_troy_oz']);d=month_end(m)
  if v<=0:raise ValueError('invalid price')
  if out and (d<=out[-1]['date'] or m!=add_months(out[-1]['month'],1)):raise ValueError('monthly prices must be consecutive and strictly ordered')
  out.append({'month':m,'date':d,'price':v})
 if not out:raise ValueError('no prices')
 return out

def macro_data(cache):
 result={}
 for series in FRED:
  p=Path(cache)/(series+'.csv');mp=Path(cache)/(series+'.meta.json')
  if not p.exists() or not mp.exists():result[series]={'values':[],'source':None};continue
  b=p.read_bytes();meta=json.loads(mp.read_text())
  if hashlib.sha256(b).hexdigest()!=meta['sha256']:raise ValueError('FRED cache hash mismatch')
  with p.open(encoding='utf-8-sig',newline='') as f:
   rows=[]; seen={}
   for r in csv.DictReader(f):
    day=r.get('observation_date') or r.get('DATE');v=r.get(series)
    if day and v not in ('','. ','.',None):
     dt=date.fromisoformat(day); num=float(v)
     if dt in seen and seen[dt]!=num: raise ValueError('conflicting FRED observations for '+series+' '+day)
     if dt not in seen: rows.append((dt,num));seen[dt]=num
  result[series]={'values':rows,'source':meta}
 return result

def last_before(rows,day,max_age=10):
 seen={}
 for dt,value in rows:
  if dt in seen and seen[dt]!=value: raise ValueError('conflicting observations on '+dt.isoformat())
  seen[dt]=value
 eligible=[(d,v) for d,v in rows if d<=day]
 if not eligible:return {'value':None,'observation_date':None,'status':'MISSING'}
 d,v=max(eligible); gap=(day-d).days
 if gap>max_age:return {'value':None,'observation_date':d.isoformat(),'status':'STALE','age_days':gap}
 return {'value':v,'observation_date':d.isoformat(),'status':'AVAILABLE','age_days':gap}

def macro_phase(macro,peak,trough,end,recovered):
 # Month-end dates describe monthly averages, not executable price observations.
 anchors={'before':month_end(add_months(peak,-3)),'peak':month_end(peak),'trough':month_end(trough)}
 if recovered:anchors['recovery']=month_end(end)
 result={}
 for series in FRED:
  samples={k:last_before(macro[series]['values'],d) for k,d in anchors.items()}
  def diff(a,b):
   x=samples.get(a,{}).get('value');y=samples.get(b,{}).get('value')
   return y-x if x is not None and y is not None else None
  result[series]={'samples':samples,'before_to_peak':diff('before','peak'),'peak_to_trough':diff('peak','trough'),'trough_to_recovery':diff('trough','recovery') if recovered else None,'unit':'index points' if series=='DTWEXBGS' else 'percentage points','pit_eligible':False}
 return result

def compute_events(prices,threshold,segment_end='DATA_END'):
 raw=drawdowns([{'at':x['date'].isoformat()+'T00:00:00Z','price':x['price']} for x in prices],threshold);bydate={p['date'].isoformat():p for p in prices};out=[]
 for e in raw:
  peak=e['peak_at'][:10];trough=e['trough_at'][:10];end=e['end_at'][:10];p=bydate[peak];tr=bydate[trough];endrow=bydate[end]
  paths=[x for x in prices if p['date']<x['date']<=endrow['date']];trigger=next(x for x in paths if x['price']<=p['price']*(1-threshold))
  def months(a,b):return (b.year-a.year)*12+b.month-a.month
  out.append({'peak_month':p['month'],'peak_price':p['price'],'trough_month':tr['month'],'trough_price':tr['price'],'end_month':endrow['month'],'end_price':endrow['price'],'drawdown_fraction':e['drawdown'],'fall_calendar_days_month_end_proxy':(tr['date']-p['date']).days,'fall_trading_days':None,'fall_months':months(p['date'],tr['date']),'threshold':threshold,'first_threshold_month':trigger['month'],'threshold_price':trigger['price'],'recovery_month':endrow['month'] if e['recovered'] else None,'trough_to_recovery_months':months(tr['date'],endrow['date']) if e['recovered'] else None,'trough_to_recovery_calendar_days_month_end_proxy':(endrow['date']-tr['date']).days if e['recovered'] else None,'underwater_months':months(p['date'],endrow['date']),'underwater_calendar_days_month_end_proxy':(endrow['date']-p['date']).days,'right_censored':not e['recovered'],'censor_reason':None if e['recovered'] else segment_end,'selection':'retrospective peak-to-recovery; do not use trough to form signal'})
 return out,raw

def get_cftc_series(inputs,retrieved_at):
 allrows=[];status=[]
 for path,map_path in inputs:
  mapping=json.loads(Path(map_path).read_text());x=import_cftc(path,mapping.get('mapping',mapping),retrieved_at);allrows.extend(x['observations']);status.append({'input_sha256':x['input_sha256'],'release_map_sha256':hashlib.sha256(Path(map_path).read_bytes()).hexdigest(),'source_url':'https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm','matched':x['matched_rows'],'excluded':len(x['excluded_rows'])})
 return cftc(allrows)['reports'],status

def cftc_at(reports,m):
 boundary=month_end(m)+timedelta(days=1); end=datetime.combine(boundary,datetime.min.time(),tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
 eligible=[x for x in reports if x['validation_passed'] and x.get('availability_bound_at') and datetime.fromisoformat(x['availability_bound_at'])<=end]
 if not eligible:return {'status':'MISSING','reason':'no report with verified availability bound by month end'}
 r=max(eligible,key=lambda x:x['report_date']);d=date.fromisoformat(r['report_date'][:10]);gap=(month_end(m)-d).days
 if gap>14:return {'status':'STALE','report_date':d.isoformat(),'age_days':gap}
 mm=r['positions']['managed_money']; prior=[x for x in eligible if x['report_date']<r['report_date']];p=max(prior,key=lambda x:x['report_date']) if prior else None
 valid_prior=p and (d-date.fromisoformat(p['report_date'][:10])).days<=14
 return {'status':'AVAILABLE','report_date':d.isoformat(),'availability_bound_at':r['availability_bound_at'],'long':mm['long'],'short':mm['short'],'net_oi':r['managed_money_net_oi'],'long_change':mm['long']-p['positions']['managed_money']['long'] if valid_prior else None,'short_change':mm['short']-p['positions']['managed_money']['short'] if valid_prior else None,'net_percentile':None,'percentile_status':'not computed; incomplete comparable PIT history','pit_eligible':False}

def study(fixing,spot,cache,inputs,retrieved,threshold=.1,fred_anchors=None):
 hist=load_prices(fixing);recent=load_prices(spot)
 if hist[-1]['month']>='2025-06' or recent[0]['month']<'2025-06':raise ValueError('price series crosses source-definition break')
 h,hr=compute_events(hist,threshold,'SOURCE_DEFINITION_CHANGE'); r,rr=compute_events(recent,threshold,'LATEST_OBSERVATION')
 selected=[]
 for name,low,high in TARGETS:
  matches=[x for x in h if low<=x['peak_month']<=high]
  if not matches:selected.append({'name':name,'status':'NOT_FOUND','reason':'no non-overlapping episode at threshold with peak in specified year'});continue
  event=max(matches,key=lambda x:-x['drawdown_fraction']).copy();event['name']=name;event['status']='AVAILABLE';selected.append(event)
 if r:
  unfinished=[x for x in r if x['right_censored']];event=(unfinished[-1] if unfinished else r[-1]).copy();event['name']='最新现货口径分段回撤';event['status']='AVAILABLE';event['segment_left_truncated']=True;selected.append(event)
 else:selected.append({'name':'最新现货口径分段回撤','status':'NOT_FOUND'})
 macro=macro_data(cache) if not fred_anchors else None
 anchor_data=json.loads(Path(fred_anchors).read_text()) if fred_anchors else None
 if anchor_data:
  actual={'fixing':hashlib.sha256(Path(fixing).read_bytes()).hexdigest(),'spot':hashlib.sha256(Path(spot).read_bytes()).hexdigest()}
  if anchor_data.get('price_sha256')!=actual or anchor_data.get('threshold')!=threshold:raise ValueError('fixed anchors require original price data and threshold')
 positions,position_sources=get_cftc_series(inputs,retrieved)
 for e in selected:
  if e['status']!='AVAILABLE':continue
  anchor_key='|'.join([e['peak_month'],e['trough_month'],e['end_month'],str(not e['right_censored'])])
  if fred_anchors:
   if anchor_key not in anchor_data['events']: raise ValueError('no fixed FRED anchors for event '+anchor_key)
   e['macro']=anchor_data['events'][anchor_key]
  else:e['macro']=macro_phase(macro,e['peak_month'],e['trough_month'],e['end_month'],not e['right_censored'])
  e['cftc']={'peak':cftc_at(positions,e['peak_month']),'trough':cftc_at(positions,e['trough_month']),'interpretation':'available-bound matched, later-downloaded current vintage; descriptive only; no trader identity'}
  p=e['cftc']['peak']; t=e['cftc']['trough']
  if p['status']==t['status']=='AVAILABLE':
   e['cftc']['phase_change']={'long':t['long']-p['long'],'short':t['short']-p['short'],'net_contracts':(t['long']-t['short'])-(p['long']-p['short']),'net_oi':t['net_oi']-p['net_oi'],'price_position_divergence':(t['long']-t['short'])>(p['long']-p['short']),'caveat':'monthly gold averages versus weekly report snapshots; divergence is descriptive, not causation'}
  real=e['macro']['DFII10']['peak_to_trough']; usd=e['macro']['DTWEXBGS']['peak_to_trough']; nominal=e['macro']['DGS10']['peak_to_trough']
  e['descriptive_mechanism']={'nominal_10y':'unknown' if nominal is None else ('up' if nominal>0 else ('down' if nominal<0 else 'flat')),'real_10y':'unknown' if real is None else ('up' if real>0 else ('down' if real<0 else 'flat')),'broad_usd':'unknown' if usd is None else ('up' if usd>0 else ('down' if usd<0 else 'flat')),'caveat':'directional co-movement only; not causal attribution'}
 return {'schema_version':'0.4.0','price_frequency':'monthly average','price_contracts':{'historical':'London PM fixing monthly mean through 2025-05','recent':'spot daily rates monthly mean since 2025-06','unit':'USD/troy_oz','structural_break':'2025-06','no_cross_segment_join':True},'inputs':{'fixing_start':hist[0]['month'],'fixing_end':hist[-1]['month'],'spot_start':recent[0]['month'],'spot_end':recent[-1]['month'],'price_sha256':{'fixing':hashlib.sha256(Path(fixing).read_bytes()).hexdigest(),'spot':hashlib.sha256(Path(spot).read_bytes()).hexdigest()},'fred_sources':anchor_data['fred_sources'] if fred_anchors else {k:v['source'] for k,v in macro.items()},'cftc_sources':position_sources},'threshold':threshold,'events':selected,'survival':{'fixing_peak_to_recovery':survival(hr),'spot_peak_to_recovery':survival(rr),'interpretation':'retrospective selected drawdowns; not a trading signal or causal evidence'},'limitations':['Monthly means and end-of-month macro values are not daily prices, releases, or tradeable observations.','Trading-day durations unavailable; calendar days are month-end proxies.','Latest segment starts in 2025-06; prior peak not comparable and left truncation applies.','FRED current snapshot and CFTC annual snapshots lack verified historical vintages; retrospective description only; no trading or PIT backtest.','Return to nominal former peak ignores inflation.']}

def render_study(result):
 lines=['# 黄金历史回撤与宏观联合事件研究','', '数据来源：世界银行 Pink Sheet 黄金月平均价；工作簿通过第三方缓存获取，来源、原始哈希、许可及分段见 `sources/v4/world_bank_source.json`。名义美元/金衡盎司。FRED 为当次下载的最新历史快照。**所有结论均为事后描述性分析，不是历史时点交易回测。**','',f"阈值 {result['threshold']:.0%}；历史定盘月均价 {result['inputs']['fixing_start']} 至 {result['inputs']['fixing_end']}；现货月均价 {result['inputs']['spot_start']} 至 {result['inputs']['spot_end']}，两段独立计峰值。",'', '| 事件 | 峰值（月／价格） | 谷底（月／价格） | 峰谷跌幅 | 首次触及阈值 | 下跌月数 | 谷底到回补月数 | 水下月数 | 状态 |','|---|---|---|---:|---|---:|---:|---:|---|']
 for e in result['events']:
  if e['status']!='AVAILABLE':lines.append(f"| {e['name']} | — | — | — | — | — | — | — | 未找到 | ");continue
  rec='右删失' if e['right_censored'] else '已回补'
  lines.append(f"| {e['name']} | {e['peak_month']} / {e['peak_price']:.2f} | {e['trough_month']} / {e['trough_price']:.2f} | {e['drawdown_fraction']:.1%} | {e['first_threshold_month']} | {e['fall_months']} | {e['trough_to_recovery_months'] if e['trough_to_recovery_months'] is not None else '未回补'} | {e['underwater_months']} | {rec} |")
 lines+=['','日期为月份，日历天数在 JSON 中以月末日期作为近似；**交易日数不可由月均价计算，均为缺失**。右删失是到样本结尾尚未回补，最新现货段还存在左截断。2025-06 以前定盘月均价与之后现货月均价不跨口径拼接。','','## 宏观变化：峰值月至谷底月','', '| 事件 | 2Y 名义收益率 | 10Y 名义收益率 | 10Y 实际收益率 | 10Y 盈亏平衡通胀率 | 广义美元 |','|---|---:|---:|---:|---:|---:|']
 def show(x):return f'{x:+.2f}' if x is not None else '缺失'
 for e in result['events']:
  if e['status']!='AVAILABLE':continue
  vals=[show(e['macro'][k]['peak_to_trough']) for k in FRED]
  lines.append('| '+e['name']+' | '+' | '.join(vals)+' |')
 lines+=['','利率单位为百分点，美元为指数点；每月取该月末或之前最近有效观测，距离月末不超过 10 天；峰值前 3 个月和修复期数值、实际观察日期在 JSON 中。历史 FRED 最新版本不证明当时已公布，禁止据此声明无前瞻偏差。DTWEXBGS 是广义美元指数，不是 ICE DXY。','','## 持仓与机制','']
 for e in result['events']:
  if e['status']!='AVAILABLE':continue
  p,t=e['cftc']['peak'],e['cftc']['trough']
  if p['status']==t['status']=='AVAILABLE':
   change=e['cftc']['phase_change']; lines.append(f"- {e['name']}：峰值月最近报告 {p['report_date']} 管理基金多／空 {p['long']:.0f} / {p['short']:.0f} 手、净多/OI {p['net_oi']:.1%}；谷底月 {t['report_date']} 为 {t['long']:.0f} / {t['short']:.0f} 手、{t['net_oi']:.1%}。两端净多变化 {change['net_contracts']:+.0f} 手；价格下跌而净多增加的描述性背离：{'是' if change['price_position_divergence'] else '否'}。月均价与周报不是同一时点。")
  else:lines.append(f"- {e['name']}：CFTC 峰值期 {p['status']}，谷底期 {t['status']}；缺失时不推测资金方向。")
 lines+=['','## 回撤期间的描述性组合','']
 for e in result['events']:
  if e['status']!='AVAILABLE':continue
  m=e['descriptive_mechanism']; labels={'up':'上行','down':'下行','flat':'持平','unknown':'缺失'}
  lines.append(f"- {e['name']}：10Y 名义利率 {labels[m['nominal_10y']]}、10Y 实际利率 {labels[m['real_10y']]}、广义美元 {labels[m['broad_usd']]}；这是同期方向组合，不是下跌成因的证明。")
 lines+=['','上述回撤是事后按峰值与谷底识别的路径；首次阈值月份只是当时能观察到的阈值事件，不是基于事后谷底建立的交易信号。机制分类仅可根据已观测的同向/分化关系描述；缺失时不归因，不能把同步变化当作因果。','', '名义回补未调整通胀；月平均价格不同于盘中最高价或日收盘价。完整输入、来源、事件边界、样本及月末日历天数在 JSON；不提供胜率优化或加减仓信号。']
 return '\n'.join(lines)+'\n'
