"""Real-source gate before walk-forward; refuses fabricated performance metrics."""
import csv,json
from pathlib import Path
from .snapshots import check_manifest

def real_audit(cache,manifest,fixing,spot):
 hashes=check_manifest(cache,manifest)
 counts={}
 for name,path in [('fixing',fixing),('spot',spot)]:
  with Path(path).open(newline='',encoding='utf8') as f: rows=list(csv.DictReader(f))
  counts[name]={'observations':len(rows),'price_type':'monthly_average','executable_price':False}
 blockers=['FRED 快照缺少逐个历史决策日可验证的发布时间与历史版本。','CFTC 年度文件为事后获取，官方页面更新日期只是时间界限，不能证明当时的历史版本。','世界银行黄金月均价不是可执行的日收盘价或期货结算价。','最新观察月只有一个因子有足够真实输入，其他因子及可靠 CFTC 历史覆盖不足。','尚未建立同时满足可执行价格和点时数据合同的输入集。']
 if not hashes['all_match']:blockers.insert(0,'FRED 本地快照缺失或与清单哈希不符。')
 return {'schema_version':'0.6.0','validation_status':'NO_GO','model_signal':'NO_VALIDATED_SIGNAL','market_signal':'RESEARCH_ONLY','risk_action':'NOT_EVALUATED','final_action':'RESEARCH_ONLY','real_input_summary':{'fred_snapshot_check':hashes,'gold_prices':counts,'executable_pit_rows':0,'note':'zero means no input set has been established as meeting the combined execution and PIT contract; not a count of all source rows'},'out_of_sample':{'sample_count':0,'return':None,'max_drawdown':None,'transaction_cost':None,'benchmark_return':None,'reason':'PIT and executable-price input contract unmet'},'blockers':blockers,'method':'No trade returns or win rates are fabricated. Framework can be evaluated on user-provided, evidence-backed executable-price intervals.'}

def render_audit(x):
 lines=['# GMI v0.6 样本外验证审计','',f"结论：{x['validation_status']}；模型信号：{x['model_signal']}。没有执行订单。",'','## 阻碍','']
 lines.extend('- '+s for s in x['blockers']);lines+=['','## 样本外结果','', '严格资格样本数：0；策略收益、最大回撤、交易成本、基准收益均为缺失，原因是当前数据未满足历史 PIT 与可执行价格合同。该 0 表示没有建立合格输入集，不代表原始价格序列没有数据。','', 'Walk-forward 框架对输入做发布时间、获取时间、版本和价格合同检查，训练产生候选中心，验证区间在预先指定的候选中选择，样本外测试区间不参与选择；框架假定提供的来源证据由操作者独立核验。交易成本、滑点、现金和资金成本是显式配置，测试数据不可用时不生成绩效。','', '个人仓位风控与市场判断独立。风控阈值为用户配置，只有明确触及相应规则才给风险减仓候选；没有经过充分核验的模型驱动加减仓信号。']
 return '\n'.join(lines)+'\n'
