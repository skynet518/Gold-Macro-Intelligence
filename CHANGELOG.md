# Changelog / 版本记录

[English](README.md) · [简体中文](README.zh-CN.md)

The versions below describe engineering milestones. **They are not evidence of profitable trading performance.** Historical source ZIP files are preserved privately; they are not part of the public Git repository by default.

以下各版本代表工程迭代，不代表策略已获得实盘有效性验证。历史源码全量 ZIP 作为私有资产保存，不默认进入公开 Git 仓库。

## v1.0.1 — Patch release

### Fixed

- Resolved broken documentation links when the Agent Skill is installed independently.
- Improved CLI error messages for invalid analysis inputs.

### Documentation

- Clarified the separate installation requirements for the Agent Skill and Python engine.
- Documented research and model-signal status fields across CLI commands.
- Clarified offline source execution and Python package build dependencies.

### Validation

- Added regression coverage for standalone Skill documentation portability and invalid input handling.
- Preserved existing research calculations and model-signal safety restrictions.

## v1.0.0 — Initial public research release / 首个公开研究版本

- English and Simplified Chinese documentation in one repository / 单仓库中英文双语文档。
- Stable Agent Skill entry and standalone Python CLI / 通用 Skill 入口与独立 Python CLI。
- Deterministic offline examples and data-contract checks / 可重复离线示例与数据合同检查。
- Gold drawdown research, macro/CFTC evidence handling and uncalibrated six-factor research interfaces / 黄金回撤研究、宏观与期货持仓处理、未经校准的六因子研究接口。
- Research-only status `NO_GO / NO_VALIDATED_SIGNAL` for real trading decisions / 真实交易信号仍不具验证资格。

## v0.7.0 — Portability baseline / 通用环境基线
- Raw feature identity consistency and synthetic JSON fixture comparison / 原始特征身份一致性及合成 JSON 对照。

## v0.6.0 — OOS framework / 样本外框架
- Time-aligned factor input, risk-rule separation and walk-forward research framework / 因子时点对齐、风控解耦、Walk-Forward 研究框架。

## v0.5.0 — Six-factor research / 六因子研究
- Exploratory research factors and coverage-aware scores / 探索性因子与覆盖率约束评分。

## v0.4.0 — Historical events / 历史事件
- Gold drawdown and recovery events with rates and available futures overlays / 黄金回撤回补及美债、可得期货持仓事件对齐。

## v0.3.0 — Official-data research pipeline / 官方数据研究流程
- CFTC report mapping, FRED snapshot handling and research report generation / CFTC 报告映射、FRED 快照与研究报告。

## v0.2.0 — Data contracts / 数据合同
- Unit, vintage, CFTC and central-bank quality checks / 单位、历史版本、期货及央行质量控制。

## v0.1.0 — Initial prototype / 初始原型
- Offline Agent Skill + Python engine and synthetic fixtures / 离线 Skill、Python 引擎及合成输入。
