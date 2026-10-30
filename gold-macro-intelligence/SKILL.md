---
name: gold-macro-intelligence
description: >-
  Run evidence-bound, read-only gold macro research: drawdowns, US real yields
  and dollar, CFTC futures positioning, ETF and central-bank reserves, data
  timing and unvalidated risk checks. 黄金历史回撤、美债实际利率、CFTC持仓与央行储备的可复现研究；不执行交易。
license: MIT
metadata:
  version: "1.0.1"
  compatibility: >-
    Requires Python 3.10+ and access to the accompanying gmi package; live data
    are not bundled. 需要 Python 3.10+ 及配套 gmi 包，未内置全部实时数据。
---

# Gold Macro Intelligence (GMI)

## When to use / 何时使用

Use this Skill when a user needs an auditable study of gold drawdowns, Treasury yields, dollar conditions, COMEX positioning, central-bank holdings or ETF inputs. The Skill orchestrates a **deterministic Python engine**; the model must not invent prices, data publication dates, numerical scores, validated trade signals or source content.

适合对黄金历史大跌及回补、美债利率、美元、期货资金结构和央行/ETF 储备做有数据依据的研究。必须调用配套 Python 计算，**不能仅凭语言模型自行编造数据、分数或加减仓结论**。

## Procedure / 执行步骤

1. Identify the instrument, price type, currency, frequency, decision time and intended historical/research-only use. Do not mix spot, fixing and futures prices without a documented method. / 明确标的、价格口径、币种、频率及分析时点；不得混用现货、定盘价和期货。
2. Read the supplied data contract and check units, instrument/series identity, official source, vintage, observation/publication/retrieval times and whether historical evidence was actually available at the decision time. / 核对单位、序列身份、来源、修订及数据真正可得时间。
3. From the project root, run the appropriate engine command, for example `python3 -m gmi analyze INPUT.json`, `python3 -m gmi drawdowns PRICES.json`, `python3 -m gmi update-report ...`, `python3 -m gmi factor-research ...`, or `python3 -m gmi walk-forward INPUT.json`. Do not improvise missing CLI flags; consult the bundled references below. / 按真实 CLI 运行并读取 JSON，缺参数时查文档，不自行猜命令。
4. If data are absent, stale or unauditable, output explicit limitations. Never replace missing official-country observations with zero or turn a CFTC page *Updated* date into a first-release timestamp. A holdings change is not automatically a central-bank purchase or ETF dollar flow. / 缺失、过期或不能审计的数据必须明确说明；储备吨数变化不直接等于购金，网页更新日不等于历史首发时间。
5. Distinguish retrospective gold episodes, first threshold crossings and right-censored recovery; monthly averages are not executable daily fills. Historical snapshots and downloaded annual archives do not by themselves prove point-in-time backtest eligibility. / 事后峰谷与实时阈值触发分开，未回补事件按右删失，月均价格不冒充成交价。
6. Report sourced facts, calculations, missing modules, risk constraints and limitations. Separate a manually supplied hypothesis from any model signal and separate portfolio risk actions from market direction. Do not promote the model beyond `NO_GO / NO_VALIDATED_SIGNAL` without qualified independent evidence. / 区分人工观点、市场结论和仓位风控；未通过验证不得给出正式模型交易指令。

## Limits / 边界

Read-only; no broker access, orders, portfolio mutation or invented trading performance. Skill portability assumes a compatible host **and** authorized Python execution and file access. The Skill file alone is not the quantitative engine.

只读研究；不下单、不修改组合、不伪造收益。跨平台使用以宿主支持的文件与 Python 执行能力为前提，不能保证任意 Agent 开箱即用。

## References / 参考

- [English README](references/README.md) / [中文 README](references/README.zh-CN.md)
- [Usage](references/docs/USAGE.md) / [使用指南](references/docs/USAGE.zh-CN.md)
- [Methodology](references/docs/METHODOLOGY.md) / [研究方法](references/docs/METHODOLOGY.zh-CN.md)
- [Data sources](references/docs/DATA_SOURCES.md) / [数据源](references/docs/DATA_SOURCES.zh-CN.md)
- [Limitations](references/docs/LIMITATIONS.md) / [限制](references/docs/LIMITATIONS.zh-CN.md)

- [Status contract](references/docs/STATUS.md) / [状态契约](references/docs/STATUS.zh-CN.md)
