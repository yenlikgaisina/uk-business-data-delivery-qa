# Data dictionary

## Source tables (loaded by `src/ingest.py`, defined in `sql/01_create_tables.sql`)

### `raw_companies` - Companies House Free Company Data Product (2026-09-01 snapshot)

| Field | Type | Notes |
|---|---|---|
| company_name | text | as registered |
| company_number | text | Companies House unique identifier |
| postcode | text | registered office postcode, as supplied (not yet standardised) |
| post_town | text | |
| company_category | text | e.g. "Private Limited Company" |
| company_status | text | e.g. Active, Liquidation, Active - Proposal to Strike off |
| country_of_origin | text | |
| dissolution_date | text | `DD/MM/YYYY`, populated only where applicable |
| incorporation_date | text | `DD/MM/YYYY` |
| accounts_next_due_date | text | `DD/MM/YYYY` |
| accounts_last_made_up_date | text | `DD/MM/YYYY` |
| accounts_category | text | e.g. "MICRO ENTITY", "TOTAL EXEMPTION FULL" |
| conf_stmt_next_due_date | text | `DD/MM/YYYY` |
| conf_stmt_last_made_up_date | text | `DD/MM/YYYY` |
| sic_text_1..4 | text | up to four `"CODE - Description"` strings per company |

### `postcode_lookup` - ONS Postcode Directory (Live)

| Field | Notes |
|---|---|
| postcode | `PCDS`, standard-formatted postcode |
| lad_code | `LAD25CD`, ONS local authority district code |
| region_code | `RGN25CD`, ONS region code (`E12000004` = East Midlands) |

### `lad_lookup` - ONS Local Authority Districts (April 2025) Names and Codes

| Field | Notes |
|---|---|
| lad_code | `LAD25CD` |
| lad_name | `LAD25NM`, e.g. "Rushcliffe" |

### `sic_lookup` - self-derived from `raw_companies`

| Field | Notes |
|---|---|
| sic_code | as embedded by Companies House |
| sic_description | as embedded by Companies House |

## Final delivery - `final_client_delivery` / `outputs/client_delivery_full.csv`

| Field | Type | Description |
|---|---|---|
| company_number | text | unique identifier, primary key of this extract |
| company_name | text | |
| company_status | text | filtered to `Active` in the final delivery |
| company_type | text | Companies House company category |
| incorporation_date | date | |
| company_age_years | integer | whole years between incorporation and the snapshot date |
| postcode | text | standardised `OUTWARD INWARD` format |
| local_authority | text | ONS local authority district name; `"Unmatched..."` where the postcode didn't match the ONS directory |
| region | text | `"East Midlands"` for every row in this scoped extract |
| sic_code | text | primary SIC code (Companies House `SicText_1`); may be a legacy 4-digit SIC 2003 code (see root-cause analysis) or absent |
| sic_description | text | matching description |
| secondary_sic_codes | text | any further SIC codes (2nd-4th), comma-separated |
| primary_industry | text | UK SIC 2007 section grouping, or an explicit "Not classified (...)" label |
| accounts_due_date | date | |
| accounts_overdue_flag | 0/1 | 1 if `accounts_due_date` is before the snapshot date |
| confirmation_due | date | next confirmation statement due date |
| snapshot_date | date | `2026-09-01` for this delivery |

## Known, quantified data-quality characteristics of the source

These are documented here so they are never mistaken for a pipeline defect
by a future reviewer - see `docs/root_cause_analysis.md` for the full
investigation.

- **140 companies (0.2%)** carry a legacy 4-digit SIC 2003 code that was
  never re-filed under the current 5-digit SIC 2007 scheme.
- **487 companies (0.8%)** have no SIC code recorded at all (source value
  `"None Supplied"`, normalised to `NULL`).
- **0 companies** have an unmatched postcode within the final Nottinghamshire
  scope (100% match rate); a small number did not match within the broader
  East-Midlands pre-filter used earlier in the pipeline (see
  `data/reference/SOURCES.md`).
