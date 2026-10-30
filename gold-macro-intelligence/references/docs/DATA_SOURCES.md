# Data sources and provenance

[简体中文](DATA_SOURCES.zh-CN.md) · [Home](../README.md)

GMI has a data contract, not a promise of free and unrestricted access to every series. The maintainer's MIT license covers this project's original code and text only. Data access, permitted use and redistribution must be checked at each provider.

| Research area | Preferred source / family | What to record | Current caution |
|---|---|---|---|
| US nominal yields | FRED `DGS2`, `DGS10` | Series ID, level in %, observation/release/retrieval time and snapshot hash | Current snapshots alone do not establish intraday first publication or vintage. |
| US real yield / breakeven | FRED `DFII10`, `T10YIE` | Same plus missing-day handling | Not available as continuous comparable series over all post-1971 gold history. |
| Broad USD | FRED `DTWEXBGS` | Index identity, provider, observation and publication date | Not ICE DXY; index methodology can change. |
| Gold futures positions | CFTC Disaggregated Futures Only, COMEX gold | Report date, release evidence, category, long/short/spreading, OI, file hash | Website *Updated* date is not first release; later downloaded files are not historical vintages. |
| Gold price | Clearly identified licensed spot, fixing or futures series; historical World Bank Pink Sheet research | Price type, monthly/daily frequency, USD/troy oz, methodological breaks | Historical v0.4 study used third-party-mirrored workbook; do not bundle without permission. |
| Gold ETF | Fund issuers or WGC reporting | Tonnes held, dates, coverage, source definition | Holdings changes differ from dollar net inflows. |
| Central bank reserves | Official national banks, IMF/WGC reports | Country, gold tonnes, report month, published/retrieved date, revision and gaps | Reporting lag differs; holdings change is not necessarily verified purchase. |
| Liquidity/options | Licensed official/exchange/authorized sources | Instrument, unit, tenor/expiry, timestamp, rights | Not a complete turnkey dataset in this repository. |

## Source links

- FRED: https://fred.stlouisfed.org/ ; API/data rights: https://fred.stlouisfed.org/docs/api/fred/ and https://fred.stlouisfed.org/legal/
- CFTC COT: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm ; compressed archive: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
- World Gold Council: https://www.gold.org/goldhub/data
- World Bank commodity prices: https://www.worldbank.org/en/research/commodity-markets
- IMF data: https://data.imf.org/

## Publication timing: four dates, not one

`observed_at`: what period the observation describes. `published_at`: when a provider made this version public. `retrieved_at`: when a researcher actually downloaded or archived it. `vintage`: the version/revision identifier. These should never be silently substituted for each other. A reconstruction based on a contemporary download needs explicit caveats and independent evidence if it claims historical availability.

## What ships in the public repository

Only code, approved configuration, documentation, and **clearly marked synthetic examples/fixtures** ship by default. Official CFTC annual ZIP files, World Bank mirror extracts, FRED downloaded CSVs, WGC reports and private cache files stay out of Git. The importers work with user-provided data under appropriate terms. The historical project archive can contain research evidence, but it is not part of the public source distribution.

When adding a source, specify its owner, URL, license/terms, provenance, format, units, revision policy, release-time evidence and whether redistribution is permitted. A link to a public page is not blanket permission to republish its dataset.
