# 安装与使用指南

[English](USAGE.md) · [返回首页](../README.zh-CN.md)

## 1. 运行离线样例

在仓库根目录、Python 3.10 及以上环境运行：

```bash
python3 -m gmi env-check --skill gold-macro-intelligence/SKILL.md
python3 -m gmi analyze examples/analysis.json
python3 -m gmi drawdowns examples/prices.json --threshold 0.10
python3 -m gmi backtest examples/backtest.json
python3 -m gmi harness-probe --input fixtures/gmi_portability_input.json --output gmi-result.json
python3 -m gmi harness-verify --candidate gmi-result.json --expected fixtures/gmi_portability_expected.json
```

自带的快速运行输入全部是合成测试数据。`harness-verify` 显示 `MATCH`，只表示计算结果与固定样例相同，**不表示黄金涨跌预测有效**。支持 `--output` 的命令可以将 JSON 写入文件。

## 2. 作为 Agent Skill 使用

1. 将 `gold-macro-intelligence/` 文件夹放入所用 Agent 宿主能够发现的 Skill 目录。
2. 保证同一执行环境能导入 `gmi` 包：可以从项目根目录运行，或使用 `python3 -m pip install .` 安装。
3. 让 Agent 使用某个**明确的数据文件**运行对应 `python3 -m gmi ...` 命令。例如：“使用 GMI 分析 `my-gold-research.json`，说明数据截止日期和缺失项，不生成买卖指令。”
4. 核对结构化输出。Agent 的文字解释不能代替引擎实际执行结果。

Skill 遵循 Agent Skills 文件格式，但各宿主的文件访问和命令执行权限不同。不能假设所有 Agent 都自带 Python 运行权限。

## 3. 准备自己的数据

基础数据格式参考 `examples/analysis.json`。每条观测包括模块、指标、数值、单位、`observed_at`、`published_at`、`retrieved_at`、来源、链接及 `vintage`。CFTC 数据还需明确申报分类及报告口径；央行数据还需国家信息。字段应符合程序中的指标单位字典；发布时间未知或单位冲突时，不要靠猜测填补。

标准 CSV 导入命令：

```bash
python3 -m gmi import-csv my-observations.csv --output normalized.json
```

示例里的日期和数值均不代表真实行情。

## 4. 导入真实市场资料（需自行准备外部数据）

CFTC Disaggregated Futures Only 可从官方历史归档下载；FRED 有对应序列的导入或缓存接口，但需遵守其使用条款。示例研究命令：

```bash
python3 -m gmi update-report \
  --cftc /path/to/official-cftc-file.zip \
  --releases /path/to/verified-release-bounds.json \
  --fred-cache /path/to/fred-cache \
  --output my-market-report.json --markdown my-market-report.md
```

上述命令要求你自行准备官方文件、报告日期证据和 FRED 缓存。支持 `--fetch-fred` 获取官方快照，但不能据此声称掌握过去每个时点的真实数据版本。CFTC 网页的更新日期也不是首次公布时间的直接证据。ETF 和央行补充数据需要用户提供且有可追溯来源。

历史事件研究的 `event-study` 要求分开提供 `--fixing`、`--spot` 两种价格序列，并在 `--fred-cache` 与 `--fred-anchors` 之间二选一。后来下载的 FRED 数据或前期报告抽取的锚点，不能证明历史交易当时的可得性。详见[研究方法](METHODOLOGY.zh-CN.md)和[数据源说明](DATA_SOURCES.zh-CN.md)。

`walk-forward` 内置身份映射目前仅覆盖 FRED 的 `DFII10`、`DGS2`、`DGS10`、`T10YIE`、`DTWEXBGS`，须匹配字典单位和系列链接；尚无登记映射的其他已知指标会被拒绝。未知原始指标必须提供显式自定义特征合同，可参考 `examples/v060_walkforward_synthetic.json`。这些检查不会独立验证数据提供方或历史版本。

## 5. 如何阅读结论

- `NO_GO / NO_VALIDATED_SIGNAL`：未建立符合资格的真实预测交易信号。
- 个人仓位风险门槛可以限制继续加仓，但这不等于宏观模型看空黄金。
- 缺少数据就显示缺少，不能在六个模块只有少数可用时假称完成全面评分。
- 合成样例产生的收益率不得当成真实黄金策略业绩。

本项目不执行交易。任何涉及真实资金的使用，都应先理解[限制与风险](LIMITATIONS.zh-CN.md)。
