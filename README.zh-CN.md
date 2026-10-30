# Gold Macro Intelligence（GMI）｜黄金宏观量化研究工具

[English](README.md) · **简体中文**

GMI 是一套只读、可复现的黄金研究工具，由 [Agent Skill](gold-macro-intelligence/SKILL.md) 与确定性的 Python 命令行引擎组成。它把黄金价格、美国国债利率、期货资金结构和实物配置需求放在同一个分析框架中，而不是让语言模型凭盘面临时生成判断。

项目起点是几个实际交易中经常碰到的问题：**黄金经历一次大跌，到底跌了多久？回到前高用了多久？同期美国国债收益率和实际利率怎么变？哪些资金在离场，哪些资金仍在增持？** 只看 K 线，往往无法区分实际利率上升、美元流动性紧张、期货杠杆出清或中长期配置需求变化。

GMI 希望把这些线索变成有出处、能重算的研究结果。它目前是**研究工具，不是经过验证的交易信号系统，更不是自动交易程序**。

## 可以用它研究什么

| 研究问题 | 已有能力与边界 |
|---|---|
| 历史黄金跌幅和修复速度 | 识别峰谷、回撤阈值、回补前高、持续水下时间及未回补的右删失事件。 |
| 美债利率和美元是否同步变化 | 支持 2Y/10Y 名义收益率、10Y TIPS 实际收益率、盈亏平衡通胀以及广义贸易加权美元指数。 |
| 黄金期货是谁在加仓或减仓 | 解析 CFTC COMEX 分类持仓，计算多仓、空仓、净仓位、OI 和拥挤度研究指标。 |
| ETF 和各国央行买卖情况 | ETF 持仓、国别央行黄金储备及同月可比变化的数据结构、延迟公布及覆盖率检查。 |
| 流动性与期权结构的影响 | 提供独立因子接口；需要用户提供定义明确、来源可靠的数据。 |
| 因子是否有预测价值 | 提供探索性相关分析和独立的 Walk-Forward 验证框架，不能直接等同于策略已通过验证。 |

目前并非所有模块都有开箱即用的实时数据。CFTC 官方文件、FRED 快照已有导入或更新流程；ETF、央行、流动性和期权需要符合约定的外部输入。缺失数据如实显示缺失，不编造、不按零处理。

## 快速开始

**环境：** Python 3.10 及以上。从源码目录直接运行只依赖 Python 标准库；打包或安装可能需要 `setuptools`。


### 安装 Python 引擎与 Skill

Python 3.10+。从仓库根目录在 macOS / Linux 使用隔离环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m gmi env-check
.venv/bin/python -m gmi analyze examples/analysis.json
```

Windows 请使用 `.venv\Scripts\python.exe` 替代 `.venv/bin/python`。Skill 与 Python 引擎是两个独立组件：仅安装 Skill 不会安装 Python 包；宿主决定 Skill 安装位置，Agent 必须使用已安装 GMI 的解释器，并获得文件与终端访问授权。满足 Python 条件时也可在源码根目录直接运行 `python3 -m gmi`。完全离线环境可能缺少 pip 构建依赖；`pip install .` 可能需要获取 `setuptools>=68`。GMI 不自动下载、安装或配置 Agent 宿主。状态字段的精确定义见[状态契约](docs/STATUS.zh-CN.md)。

```bash
python3 -m unittest discover -s tests -v
python3 -m gmi analyze examples/analysis.json
python3 -m gmi drawdowns examples/prices.json --threshold 0.10
python3 -m gmi harness-probe --input fixtures/gmi_portability_input.json --output gmi-result.json
python3 -m gmi harness-verify --candidate gmi-result.json --expected fixtures/gmi_portability_expected.json
```

仓库自带的快速运行样例全部是**合成测试数据**，不代表真实黄金行情。最后一条命令只检查同一算法能否生成一致的结构化输出，不能证明预测准确率。

如需安装到 Python 环境，可在仓库根目录执行 `python3 -m pip install .`。如需作为 Agent Skill 使用，请将 `gold-macro-intelligence/` 放入宿主支持的 Skill 路径，并让该环境能访问 `gmi` Python 包。只安装 `SKILL.md` 不会获得计算能力；没有文件访问或 Python 执行权限的 Agent，需要用户授权的外部执行方式，不能承诺所有平台免适配。

真实数据导入方式见[使用指南](docs/USAGE.zh-CN.md)。

## 研究框架

GMI 将证据划分为六部分：

1. **利率与美元**：美债名义和实际收益率、通胀预期、美元变化。
2. **期货资金结构**：CFTC 管理基金多空、其他分类及未平仓量。
3. **ETF 与实物需求**：黄金 ETF 持仓及可比变动；持仓变化不直接等于资金净流入。
4. **各国央行**：官方黄金储备、披露滞后、统计覆盖率及同月可比变化；储备变化不自动等于已确认买卖。
5. **流动性**：跨资产或融资压力，需要明确的指标定义。
6. **期权与市场结构**：波动率和期权相关指标，依赖可比且有出处的数据。

每条数据尽量保留统计日期、公告日期、获取日期、指标单位、来源和修订版本。系统会区分**事后历史描述**与**当时真实能够获得的信息**。例如，CFTC 网站标注的 *Updated* 日期不一定是首次发布时间；今天下载的 FRED 历史序列也不等于过去每一天的实时历史版本。

详细参阅[研究方法](docs/METHODOLOGY.zh-CN.md)与[数据源说明](docs/DATA_SOURCES.zh-CN.md)。

## 不作出的承诺

- 不宣称已经得到有效的买卖胜率、夏普比率或最优加减仓比例。
- 不连接券商、不下单、不自动修改投资组合。
- 不承诺全球央行、ETF 和期权数据全部实时覆盖。
- 不把事后下载的历史快照当成严格的 Point-in-Time 数据。
- 不承诺任意 Agent 无需环境配置就能执行 Python 研究引擎。

在历史发布时间、可交易价格或足够样本外证据不足时，真实策略资格仍然是 **`NO_GO / NO_VALIDATED_SIGNAL`**。用户主动输入的看多、看空意见会明确标为研究假设，不能冒充模型预测。参见[验证与限制](docs/LIMITATIONS.zh-CN.md)。

## 适合谁使用

希望系统复盘黄金大跌的交易员、自主投资者；比较美债与商品资金关系的宏观研究者；需要可审计分析底座的量化研究者；以及希望在 Agent 中复用确定性研究流程的开发者。

## 开源与参与

项目原创代码及文档采用 [MIT License](LICENSE)，**不代表任何第三方数据获得了相同的再分发许可**。FRED、CFTC、世界黄金协会、世界银行及各国央行数据的使用和公开分发，应以各自条款为准。

欢迎提供能够重现的缺陷案例、发布时间证据、指标口径校正与文档改进。参见[贡献指南](CONTRIBUTING.zh-CN.md)、[安全说明](SECURITY.zh-CN.md)与[版本记录](CHANGELOG.md)。

如果一条研究结论无法找到数据依据，或者无法确定历史上何时可以知道这条信息，就应如实标明限制，而不是强行得出交易指令。
