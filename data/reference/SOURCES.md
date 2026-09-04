---
name: sources
---
# Data sources

All data in this repository is real, current, and published as open data by
UK government bodies. Nothing here is synthetic or fabricated. Where a
"previous month" comparison point was needed and only one live snapshot was
available, that limitation is disclosed explicitly in
[`docs/root_cause_analysis.md`](../../docs/root_cause_analysis.md) and
[`sql/05_monthly_reconciliation.sql`](../../sql/05_monthly_reconciliation.sql)
rather than filled in with invented data.

## 1. Companies House Free Company Data Product

- **Source:** Companies House, https://download.companieshouse.gov.uk/en_output.html
- **Snapshot used:** `BasicCompanyData-2026-09-01` (7 parts), downloaded 2026-09-04
- **Coverage:** basic company data for all live companies on the UK register,
  compiled as at 31 August 2026 (Companies House refreshes this file monthly
  and does not retain prior months)
- **Licence:** free to use, no registration required
  ([Companies House data products guidance](https://www.gov.uk/guidance/companies-house-data-products))
- **What was kept:** rows whose registered postcode fell in an East
  Midlands-area outward code, further filtered (via the ONS postcode lookup
  below) to the eight Nottinghamshire local authority districts named in
  `docs/client_requirements.md`. The full national extract (~5.5M rows,
  ~2.8GB uncompressed) was processed locally and is not committed to this
  repository - only the ~64k-row scoped subset in
  `data/reference/companies_house_raw_extract.csv.gz` (gzip-compressed to
  keep the repository small; DuckDB reads it directly, no decompression
  needed).

## 2. ONS Postcode Directory (Live)

- **Source:** ONS Open Geography Portal, ArcGIS Feature Service
  `https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Online_ONS_Postcode_Directory_Live/FeatureServer`
  ([dataset page](https://geoportal.statistics.gov.uk/datasets/ons::online-ons-postcode-directory-live/about))
- **Queried:** 2026-09-04, filtered to the ~86.7k unique postcodes present in
  the pre-filtered Companies House extract (batched `PCDS IN (...)` queries)
- **Fields used:** `PCDS` (postcode), `LAD25CD` (local authority district
  code), `RGN25CD` (region code)
- **Match rate:** 85,781 / 86,675 postcodes matched (99.0%) against the
  broader pre-filter; 100% matched within the final Nottinghamshire scope
- **Licence:** Open Government Licence / ONS geography licence
  (https://www.ons.gov.uk/methodology/geography/licences)

## 3. ONS Local Authority Districts (April 2025) Names and Codes in the UK (V2)

- **Source:** ONS Open Geography Portal, ArcGIS Feature Service
  `https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/LAD_APR_2025_UK_NC_v2/FeatureServer`
- **Queried:** 2026-09-04, all 361 UK local authority districts
- **Fields used:** `LAD25CD`, `LAD25NM`

## 4. UK SIC 2007 industry classification

- Not fetched as a separate file - Companies House embeds the ONS UK SIC 2007
  classification text directly in each `SICCode.SicText_n` field (e.g.
  `"62020 - Information technology consultancy activities"`), so the
  code/description pairs in `sic_lookup` are exactly what Companies House
  supplied, self-derived from `data/reference/companies_house_raw_extract.csv.gz`
  by `sql/02_clean_companies.sql`.
- The mapping from a 5-digit SIC 2007 code to its broad **section** (e.g.
  "Information & Communication") uses the standard published UK SIC 2007
  section boundaries (division ranges), encoded directly in
  `sql/04_enrich_industry.sql`.
