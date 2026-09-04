# Methodology

## Pipeline stages

1. **Ingest** (`src/ingest.py`, `sql/01_create_tables.sql`) - loads the
   scoped Companies House extract and the two ONS reference tables exactly
   as received, no cleaning.
2. **Clean** (`sql/02_clean_companies.sql`) - casts text dates to real
   `DATE` values, standardises postcode formatting, and unpivots the four
   `SicText_n` columns into a proper one-row-per-`(company, SIC code)`
   bridge table.
3. **Enrich geography** (`sql/03_enrich_geography.sql`) - joins postcode to
   local authority and region via the ONS Postcode Directory.
4. **Enrich industry** (`sql/04_enrich_industry.sql`) - joins SIC
   classification; this is where the deliberately introduced fan-out defect
   (Incident 1 in `docs/root_cause_analysis.md`) is demonstrated, detected
   and fixed.
5. **Reconcile** (`sql/05_monthly_reconciliation.sql`) - month-on-month
   comparison, scoped honestly to what a single snapshot can support.
6. **Validate** (`sql/06_data_quality_checks.sql`, `src/validate.py`,
   `tests/test_data_quality.py`) - the automated QA gate. Nothing reaches
   `sql/07_final_delivery.sql` conceptually "signed off" until every
   blocking check passes.
7. **Deliver** (`sql/07_final_delivery.sql`, `src/export_delivery.py`) -
   the validated, client-shaped extract.

## Why the snapshot date, not "today", is the reference point

`accounts_overdue_flag` and the age/date calculations are computed relative
to `2026-09-01` - the date the Companies House snapshot represents - not
the date this pipeline happens to be run. A delivery should be internally
consistent and reproducible: re-running this pipeline against the same
input file six months from now should produce the same `accounts_overdue_flag`
values, not different ones depending on when it happens to be executed.

## Why Nottinghamshire, and why "Active" only

The client requirement (`docs/client_requirements.md`) scopes the delivery
to Nottingham City and Nottinghamshire county, and to currently active
companies. This keeps the extract to a size that's easy to review end to
end (58,226 delivered rows) while still working from the genuine national
Companies House file rather than a pre-filtered or sampled dataset -
`data/reference/SOURCES.md` documents exactly how the national ~5.5M-row
file was filtered down.

## Reproducing this pipeline

```bash
pip install duckdb
python3 src/ingest.py
python3 src/transform.py
python3 src/validate.py
python3 src/export_delivery.py
```

Re-running end to end regenerates `delivery.duckdb`, `outputs/*` and
`data/sample/client_delivery_sample.csv` deterministically from the
committed `data/reference/*.csv` extracts - no network access or API keys
required. (`scripts/` in the project history contains the one-off scraping
scripts used to build those `data/reference/*.csv` files from the live
Companies House and ONS sources in the first place; they are not part of
the monthly pipeline itself, since production would receive a fresh
Companies House extract each month rather than re-scrape it.)
