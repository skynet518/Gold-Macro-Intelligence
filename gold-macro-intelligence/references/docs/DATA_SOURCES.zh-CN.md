# 数据来源与可追溯性

[English](DATA_SOURCES.md) · [返回首页](../README.zh-CN.md)

GMI 有固定的数据合同，但不承诺所有数据都能免费、实时、无限制访问。项目 MIT 许可证只覆盖原创代码和文档；每个第三方数据源仍需单独核对使用、下载和再分发条件。

| 研究模块 | 推荐数据源 | 必须记录的信息 | 当前限制 |
|---|---|---|---|
| 美国名义利率 | FRED `DGS2`、`DGS10` | 序列 ID、百分比单位、统计/公告/获取时间、快照哈希 | 当前下载的快照不能直接证明历史首次发布时间及版本。 |
| 实际利率/通胀预期 | FRED `DFII10`、`T10YIE` | 同上，另需处理缺失交易日 | 无法无条件向前覆盖全部 1971 年以后黄金历史。 |
| 广义美元指数 | FRED `DTWEXBGS` | 指数定义、来源、时间及修订 | 与 ICE DXY 不是同一指数。 |
| 黄金期货持仓 | CFTC COMEX Disaggregated Futures Only | 统计日、可用时间证据、分类、多空及 Spreading、OI、文件哈希 | 网页 *Updated* 并不等于首次公布；后来下载的年度文件不是历史原始版本。 |
| 黄金价格 | 来源明确、有合法使用权的现货、定盘或期货序列；历史研究使用世界银行 Pink Sheet 线索 | 价格类型、日/月频率、美元/金衡盎司及口径变更 | v0.4 用过第三方镜像工作簿，未获再分发确认前不打入公开仓库。 |
| 黄金 ETF | 基金发行方或 WGC 统计 | 持仓吨数、日期、覆盖范围、数据定义 | 持仓吨数变化不等于美元资金净流入。 |
| 各国央行 | 国家央行官网、IMF/WGC 汇总 | 国家、吨数、报告月份、公告/获取时间、修订、缺报 | 更新频率不同；储备变动不直接等于已证实购金。 |
| 流动性与期权 | 交易所或合规授权数据商 | 标的、单位、期限/到期日、时间和权利 | 目前并非仓库内完整开箱即用的数据集。 |

## 官方数据入口

- FRED：https://fred.stlouisfed.org/ ；API/条款：https://fred.stlouisfed.org/docs/api/fred/ 、https://fred.stlouisfed.org/legal/
- CFTC 持仓：https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm ；历史压缩文件：https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
- 世界黄金协会：https://www.gold.org/goldhub/data
- 世界银行商品价格：https://www.worldbank.org/en/research/commodity-markets
- IMF：https://data.imf.org/

## 四个时间字段不能混为一谈

`observed_at` 是数据所属统计期；`published_at` 是该版本实际公开时间；`retrieved_at` 是研究者下载/归档时间；`vintage` 是版本或修订身份。今天下载的历史数据可以用于**有说明的事后研究**，但如果要说“2015 年的交易者当时知道什么”，必须另有证据证明当时的发布时间与数据版本。

## 公开仓库默认包含什么

只发布原创代码、已核验配置、文档以及**明确标注为合成的示例与测试输入**。CFTC 年度 ZIP、世界银行镜像抽取 CSV、FRED 下载缓存、WGC 报告和个人研究缓存默认不提交 Git。用户可按各自授权下载后经适配器导入。历史全量归档与公开源码是两套资产，不应混放。

未来添加数据源时，请同时记录归属方、链接、许可、文件格式、单位、数据修订策略、发布时间证据及再分发许可。网站能公开访问，不意味着可以把全部数据重新打包分发。
