---
name: delivery-runbook
---
# Delivery runbook

The operational steps for producing and releasing one monthly delivery.
Written the way a Data Analyst on a Data Delivery team would document a
recurring handover, not just a one-off analysis.

## 1. Receive the new snapshot

Companies House publishes a new Free Company Data Product extract monthly
(within the first few days of the month). Download it and replace
`data/reference/companies_house_raw_extract.csv.gz` with the newly scoped
extract - `scripts/fetch_companies_house.py` followed by
`scripts/scope_to_nottinghamshire.py` automate this, including the
compression step (see `scripts/README.md`).
`data/reference/postcode_lookup.csv` and `lad_lookup.csv` only need
refreshing if new postcodes appear in scope; ONS geography codes change
rarely.

## 2. Run the pipeline

```bash
pip install -r requirements.txt
python3 src/ingest.py
python3 src/transform.py
pytest tests/test_data_quality.py -v
python3 src/validate.py
```

`pytest` and `src/validate.py` run the same checks (`sql/06_data_quality_checks.sql`)
two ways - pytest as a hard CI gate, `validate.py` to produce the
human-readable `outputs/qa_report.md` that accompanies the handover. Both
must pass before step 3.

## 3. Export and hand over

```bash
python3 src/export_delivery.py
```

Produces `outputs/client_delivery_full.csv`, `outputs/reconciliation_report.csv`
and refreshes `data/sample/client_delivery_sample.csv`. Send
`client_delivery_full.csv` alongside `outputs/qa_report.md` - the acceptance
criteria in `docs/client_requirements.md` require the QA report with every
delivery, not just the data.

## 4. Investigate before releasing, not after

Per the client's acceptance criteria, any month-on-month change greater than
5% in delivered row count is investigated and explained *before* release.
`sql/05_monthly_reconciliation.sql` is the reconciliation query; a jump like
the one in `docs/root_cause_analysis.md` (Incident 1, +32%) is exactly the
kind of thing this step exists to catch before it reaches a client, not
after.

## What changes once a second real monthly snapshot exists

This build only had one live Companies House snapshot to work from (see the
limitation documented in `sql/05_monthly_reconciliation.sql` and
`docs/root_cause_analysis.md`). Once this pipeline has run in two
consecutive months:

1. Persist each month's `stg_companies_industry` output (e.g. to a dated
   table or file) instead of only ever holding the current month.
2. Point `companies_previous_snapshot` in
   `sql/05_monthly_reconciliation.sql` at that persisted prior-month table
   instead of the same-extract proxy (`incorporation_date <= '2026-07-31'`)
   it currently uses.
3. No other SQL changes are required - the added / removed / status_changed
   reconciliation logic is already written against that shape and was
   validated against the proxy data during this build.

## Rollback

Every delivery is generated deterministically from the committed
`data/reference/*.csv` files plus that month's new Companies House extract
(`delivery.duckdb` itself is not committed - see `.gitignore`). If a
delivery needs to be withdrawn or re-issued, re-run steps 2-3 against the
same input extract to reproduce it exactly, or against the prior month's
retained extract to roll back.
