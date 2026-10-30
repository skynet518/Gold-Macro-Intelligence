"""Update/validate/report workflow. FRED snapshots are descriptive, never PIT."""
import csv,hashlib,io,json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from .adapters import import_cftc,FRED
from .research import cftc,changes,asof,central,normalized_value

URL='https://fred.stlouisfed.org/graph/fredgraph.csv?id='
def fetch_fred(directory,refresh=False):
 root=Path(directory);root.mkdir(parents=True,exist_ok=True);result={}
 for series in FRED:
  path=root/(series+'.csv');meta=root/(series+'.meta.json')
  if refresh or not path.exists() or not meta.exists():
   with urlopen(Request(URL+series,headers={'User-Agent':'GMI-research/0.3'}),timeout=20) as response:data=response.read()
   timestamp=datetime.now(timezone.utc).isoformat()
   def rows(blob):
    if not blob:return {}
    return {r.get('observation_date',r.get('DATE')):r.get(series) for r in csv.DictReader(io.StringIO(blob.decode('utf-8-sig')))}
   old=rows(path.read_bytes()) if path.exists() else {}; new=rows(data)
   delta={'added':sum(k not in old for k in new),'revised':sum(k in old and old[k]!=new[k] for k in new),'removed':sum(k not in new for k in old)}
   path.write_bytes(data)
   meta.write_text(json.dumps({'url':URL+series,'retrieved_at':timestamp,'sha256':hashlib.sha256(data).hexdigest(),'publication_time':'UNKNOWN','vintage':'CURRENT_SNAPSHOT_ONLY','local_refresh_delta':delta},indent=2)+'\n')
  else:
   data=path.read_bytes()
  m=json.loads(meta.read_text());digest=hashlib.sha256(data).hexdigest()
  if m['sha256']!=digest:raise ValueError('FRED cache hash mismatch for '+series)
  result[series]=m
 return result

def descriptive_fred(directory,as_of):
 result={};cutoff=datetime.fromisoformat(as_of.replace('Z','+00:00')).date()
 for series,(metric,instrument,unit) in FRED.items():
  p=Path(directory)/(series+'.csv');m=Path(directory)/(series+'.meta.json')
  if not p.exists() or not m.exists():result[series]={'status':'MISSING','reason':'no cached CSV and metadata'};continue
  data=p.read_bytes();meta=json.loads(m.read_text())
  if hashlib.sha256(data).hexdigest()!=meta.get('sha256'):raise ValueError('FRED cache hash mismatch')
  if datetime.fromisoformat(meta['retrieved_at'].replace('Z','+00:00')) > datetime.fromisoformat(as_of.replace('Z','+00:00')):raise ValueError('snapshot retrieved after report as_of')
  rows=[];missing=0;seen={}
  for row in csv.DictReader(io.StringIO(data.decode('utf-8-sig'))):
   date=row.get('observation_date') or row.get('DATE') or row.get('date');v=row.get(series)
   if not date or datetime.fromisoformat(date).date()>cutoff: continue
   if not v or v=='.':missing+=1;continue
   number=float(v)
   if date in seen and seen[date]!=number:raise ValueError('conflicting FRED observations for '+series+' '+date)
   if date in seen:continue
   seen[date]=number
   rows.append({'metric':metric,'value':float(v),'unit':unit,'observed_at':date+'T00:00:00Z'})
  rows.sort(key=lambda r:r['observed_at'])
  if not rows: result[series]={'status':'MISSING','reason':'no numeric observations'};continue
  result[series]={'status':'DESCRIPTIVE_ONLY','series':series,'instrument':instrument,'unit':unit,'latest_observation_date':rows[-1]['observed_at'][:10],'latest_value':rows[-1]['value'],'observation_count':len(rows),'missing_values':missing,'change_20_observations':changes(rows,metric),'publication_date':None,'publication_status':'UNKNOWN','snapshot':meta,'pit_eligible':False}
 return result

def build_report(cftc_path,releases_path,fred_dir,as_of,output,supplement=None):
 stamp=datetime.fromisoformat(as_of.replace('Z','+00:00'))
 if stamp.tzinfo is None:raise ValueError('as-of must include timezone')
 m=json.loads(Path(releases_path).read_text()); mapping=m.get('mapping',m)
 # snapshot is obtained now; as_of is report run timestamp, not historic trade timestamp.
 retrieval=datetime.now(timezone.utc).isoformat()
 if datetime.fromisoformat(retrieval)>stamp: raise ValueError('as-of must not predate data retrieval; use current time after retrieval')
 imported=import_cftc(cftc_path,mapping,retrieval); position=cftc(imported['observations']); macro=descriptive_fred(fred_dir,as_of)
 latest=position['latest']; result={'schema_version':'0.3.0','report_as_of':as_of,'mode':'DESCRIPTIVE_SNAPSHOT_NOT_PIT_BACKTEST','cftc_import':{'matched':imported['matched_rows'],'excluded':len(imported['excluded_rows']),'excluded_rows':imported['excluded_rows'],'valid_reports':position['valid_report_count'],'latest':latest},'fred':macro,'central_banks':{'status':'MISSING','reason':'no supplied official country holdings'},'etf':{'status':'MISSING','reason':'no supplied licensed ETF holdings'},'liquidity':{'status':'MISSING'},'options':{'status':'MISSING'},'model_status':'UNCALIBRATED','market_signal':'RESEARCH_ONLY','risk_action':'NOT_AVAILABLE','final_action':'无模型建议','signal_confidence':'NOT_ESTIMATED','warnings':['FRED release dates and historical vintages not verified; not PIT eligible.','CFTC archive Updated date only provides a conservative upper bound and is not necessarily first publication.','Annual CFTC snapshot is available from retrieval only; no retrospective claim.','Incomplete modules; no validated prediction or order execution.']}
 if supplement:
  extra=json.loads(Path(supplement).read_text()); rows=asof(extra['observations'],as_of,'strict_archive')
  cb=central([x for x in rows if x['module']=='central_banks'],stamp,extra.get('central_bank_coverage',{}),extra.get('max_age_days',{}).get('central_banks',0))
  result['central_banks']={'status':'AVAILABLE' if cb['countries'] else 'MISSING','details':cb}
  etf=sorted([x for x in rows if x['metric']=='etf_tonnes'],key=lambda x:x['observed_at'])
  if etf:
   last=etf[-1]; previous=etf[-2] if len(etf)>1 else None
   comparable=previous and all(last.get(k)==previous.get(k) for k in ('source','instrument','market','unit','series_id','methodology_id')) and last.get('series_id') and last.get('methodology_id')
   result['etf']={'status':'AVAILABLE','latest_observation':last,'previous_observation':previous,'change_tonnes':normalized_value(last)-normalized_value(previous) if comparable else None,'change_status':'COMPARABLE_ACTUAL_SPAN' if comparable else 'INCOMPLETE_OR_UNVERIFIED_COMPARABILITY'}
 Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result


def render_markdown(result):
 lines=['# GMI 多因子市场研究报告','',f"研究生成时间（UTC）：{result['report_as_of']}。模式：真实来源的描述性快照；不是点时回测，也不是交易建议。",'','## 美国利率及美元','', '| 指标 | 最新观察日期 | 最新值 | 20 个有效观察变化 | 发布日期 |','|---|---|---:|---:|---|']
 names={'DGS2':'美国 2 年名义收益率 %','DGS10':'美国 10 年名义收益率 %','DFII10':'美国 10 年实际收益率 %','T10YIE':'10 年盈亏平衡通胀率 %','DTWEXBGS':'名义广义贸易加权美元指数'}
 for k in ('DGS2','DGS10','DFII10','T10YIE','DTWEXBGS'):
  v=result['fred'][k]; change=v.get('change_20_observations',{}).get('value'); lines.append(f"| {names[k]} | {v.get('latest_observation_date','缺失')} | {v.get('latest_value','缺失')} | {round(change,4) if change is not None else '缺失'} | 未核验 |")
 lines += ['', '来源：美国财政部、美国联邦储备委员会，经 [FRED](https://fred.stlouisfed.org/)；FRED 当前版本的精确首次发布时间及历史版本未核实。20 个有效观测的实际起止日、周内覆盖率和来源哈希见 JSON。DTWEXBGS 不是 ICE DXY。','','## CFTC 黄金期货仓位','']
 c=result['cftc_import']['latest']
 if c and c.get('validation_passed'):
  p=c['positions']['managed_money']; d=c['changes']; lines += [f"统计日 {c['report_date'][:10]}；官方页面更新日 {c.get('source_updated_date') or '未知'}，精确首次发布时间未知；保守可用时间界限 {c.get('availability_bound_at') or '未知'}。",f"管理基金多头 {p['long']:,.0f} 手，空头 {p['short']:,.0f} 手，净多 {c['managed_money_net']:,.0f} 手，净多/OI {c['managed_money_net_oi']:.2%}。相对 {d['previous_report_date'][:10] if d['previous_report_date'] else '缺失'}：多头 {d['long'] if d['long'] is not None else '缺失'} 手，空头 {d['short'] if d['short'] is not None else '缺失'} 手，净多 {d['net'] if d['net'] is not None else '缺失'} 手。",f"官方数据：[该期黄金报告]({c.get('source_evidence_url') or 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm'})。分类不代表交易者身份、现金流或确定的交易动机。"]
 else:lines.append('缺少经过一致性检验的 CFTC 报告。')
 lines += ['', '## 央行、ETF 和其他模块','',f"央行：{result['central_banks']['status']}；ETF：{result['etf']['status']}；流动性和期权：缺失。若输入未包含来源，不推断国别购买或 ETF 资金流。"]
 if result['central_banks']['status']=='AVAILABLE':
  details=result['central_banks']['details']; breadth=details['buying_breadth']
  lines.append(f"同月广度基准：{breadth['report_month'] or '未配置'}；可比国家 {breadth['comparable_countries']}，持仓正变化国家 {breadth['positive_holding_change_countries']}。")
  for name,country in details['countries'].items():
   change=country.get('previous_period_change',{}); lines.append(f"- {name}：报告月 {country.get('reported_month','缺失')}，持仓 {country.get('latest_holdings_tonnes')} 吨，持仓变化 {change.get('value')} 吨（{change.get('status','缺失')}），连续正变化 {country.get('positive_holding_change_streak_months','未知')} 月。")
 if result['etf']['status']=='AVAILABLE':
  etf=result['etf'];lines.append(f"ETF 持仓 {etf['latest_observation']['value']} 吨，变化 {etf['change_tonnes']} 吨（{etf['change_status']}）。")
 real=result['fred'].get('DFII10',{}).get('change_20_observations',{}).get('value')
 usd=result['fred'].get('DTWEXBGS',{}).get('change_20_observations',{}).get('value')
 net=c.get('changes',{}).get('net') if c else None
 def direction(v): return '上升' if v>0 else ('下降' if v<0 else '持平')
 summary='；'.join(f'{name}{direction(value)}' for name,value in [('实际利率',real),('广义美元指数',usd),('管理基金净多',net)] if value is not None)
 lines += ['', '## 研究判断与数据可信度','']
 if summary: lines.append('本期组合观察：'+summary+'。三者的数据截止日不同，这些方向不是经验证的金价预测。')
 lines += ['', '这些指标可能对应不同的黄金定价力量，但方向关系不是本模型验证的结论。不同指标时点和经济含义不一致，不能单独确定金价方向。没有真实黄金价格序列、央行国别持仓、ETF 完整数据及经独立检验的历史因子关系；因此当前仅为 RESEARCH_ONLY，模型未校准，不具备正式交易信号资格。', '', '输入为实际下载的最新官方快照；FRED 不用于声称历史 PIT。所有数据的原始来源、哈希、排除原因和时间界限见伴随 JSON。']
 return '\n'.join(lines)+'\n'
