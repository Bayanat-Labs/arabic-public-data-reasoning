# Frozen source register

World Bank: World Development Indicators (WDI), API source 2. Requested period: 2000–2024. Acquisition: 26 October 2026. Observation API update field: 8 October 2026. Exactly 550 source observations were returned for each series (22 economies × 25 years). The API observation `unit` fields are empty, so the dataset uses the explicit `Unitofmeasure` in series metadata; authored `unit_code` and Arabic unit glosses make it executable. Original status and decimal-hint fields are retained.

| Series | Official English label | Official source unit | Individual license evidence |
|---|---|---|---|
| `SP.POP.TOTL` | Population, total | Unit | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/SP.POP.TOTL/metadata?format=json) |
| `NY.GDP.MKTP.CD` | GDP (current US$) | Current US$ | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/NY.GDP.MKTP.CD/metadata?format=json) |
| `NY.GDP.PCAP.CD` | GDP per capita (current US$) | Current US$ | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/NY.GDP.PCAP.CD/metadata?format=json) |
| `NY.GDP.MKTP.KD.ZG` | GDP growth (annual %) | % | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/NY.GDP.MKTP.KD.ZG/metadata?format=json) |
| `SP.DYN.LE00.IN` | Life expectancy at birth, total (years) | Years | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/SP.DYN.LE00.IN/metadata?format=json) |
| `EG.ELC.ACCS.ZS` | Access to electricity (% of population) | % (share) of population | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/EG.ELC.ACCS.ZS/metadata?format=json) |
| `FP.CPI.TOTL.ZG` | Inflation, consumer prices (annual %) | % | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/FP.CPI.TOTL.ZG/metadata?format=json) |
| `SP.URB.TOTL.IN.ZS` | Urban population (% of total population) | Percentage | [CC BY-4.0 metadata](https://api.worldbank.org/v2/sources/2/series/SP.URB.TOTL.IN.ZS/metadata?format=json) |

Native Arabic labels and source definitions are retained from `/v2/ar/`. Some definitions returned by that endpoint are English, and some Arabic metadata lag the current English metadata. Bayanat does not silently describe those as verified official Arabic translations. No facts are independently audited against national source systems. The [raw manifest](https://huggingface.co/datasets/Bayanat-Labs/arabic-public-data-reasoning/resolve/v0.1.0/raw/manifest.json) supplies every exact request, retrieval time, status and SHA256. Mutable URLs alone do not reproduce the frozen release.

## Provider attributions

### `SP.POP.TOTL` — Population, total

World Population Prospects, United Nations (UN), uri: https://population.un.org/wpp/, publisher: UN Population Division;
Statistical databases and publications from national statistical offices, National Statistical Offices (NSOs), uri: https://unstats.un.org/home/nso_sites/, publisher: National Statistical Offices;
Eurostat: Demographic Statistics, Eurostat (ESTAT), uri: https://ec.europa.eu/eurostat/data/database?node_code=earn_ses_monthly, publisher: Eurostat;
Population and Vital Statistics Report (various years), United Nations (UN), uri: https://unstats.un.org, publisher: UN Statistics Division

[Indicator page](https://data.worldbank.org/indicator/SP.POP.TOTL) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/SP.POP.TOTL/metadata?format=json)

### `NY.GDP.MKTP.CD` — GDP (current US$)

Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)

[Indicator page](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/NY.GDP.MKTP.CD/metadata?format=json)

### `NY.GDP.PCAP.CD` — GDP per capita (current US$)

Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)

[Indicator page](https://data.worldbank.org/indicator/NY.GDP.PCAP.CD) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/NY.GDP.PCAP.CD/metadata?format=json)

### `NY.GDP.MKTP.KD.ZG` — GDP growth (annual %)

Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)

[Indicator page](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/NY.GDP.MKTP.KD.ZG/metadata?format=json)

### `SP.DYN.LE00.IN` — Life expectancy at birth, total (years)

World Population Prospects, United Nations (UN), uri: UN Population Division;
Statistical databases and publications from national statistical offices, National Statistical Offices (NSOs), note: Derived from male and female life expectancy at birth from sources such as statistical databases and publications from national statistical offices.;
Demographic Statistics, Eurostat (ESTAT), note: Derived from male and female life expectancy at birth from sources such as Eurostat: Demographic Statistics.

[Indicator page](https://data.worldbank.org/indicator/SP.DYN.LE00.IN) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/SP.DYN.LE00.IN/metadata?format=json)

### `EG.ELC.ACCS.ZS` — Access to electricity (% of population)

SDG 7.1.1 Electrification Dataset, World Bank (WB), uri: https://trackingsdg7.esmap.org/downloads, note: Data is downloaded from ESMAP website. Data is released when a new Tracking SDG7 report is released., publisher: World Bank (WB), date accessed: 2024-05-16, date published: 2023

[Indicator page](https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/EG.ELC.ACCS.ZS/metadata?format=json)

### `FP.CPI.TOTL.ZG` — Inflation, consumer prices (annual %)

International Financial Statistics database, International Monetary Fund (IMF)

[Indicator page](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/FP.CPI.TOTL.ZG/metadata?format=json)

### `SP.URB.TOTL.IN.ZS` — Urban population (% of total population)

World Urbanization Prospects, United Nations (UN), uri: https://population.un.org/wup/, note: United Nations Population Division's World Urbanization Prospects, National definitions, publisher: UN Population Division

[Indicator page](https://data.worldbank.org/indicator/SP.URB.TOTL.IN.ZS) · [Exact metadata](https://api.worldbank.org/v2/sources/2/series/SP.URB.TOTL.IN.ZS/metadata?format=json)

## Source policy

[World Bank public licenses](https://datacatalog.worldbank.org/public-licenses) and [Summary Terms of Use](https://data.worldbank.org/summary-terms-of-use) were frozen with receipts in `raw/`. The legacy `terms-of-use-for-datasets` URL redirects to general site terms, so this release cites the operative dataset-license and summary pages directly. Only these eight individually qualified indicators are included; an open API is not a blanket clearance for every series.
