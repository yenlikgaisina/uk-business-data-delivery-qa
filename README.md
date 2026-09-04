# UK Business Data Delivery & Quality Assurance Pipeline

A monthly data delivery pipeline for a fictional client scenario, built on
**real, current UK open data** - not a synthetic or Kaggle dataset. It
ingests, cleans, enriches, validates and delivers a company dataset the way
a Data Analyst on a Data Delivery / data operations team actually would:
with agreed requirements, a documented data dictionary, an automated QA
gate, and two genuine data-quality incidents found and root-caused during
the build rather than hidden.

This is a SQL and data-quality project, deliberately **not** a machine
learning project - no models, no predictions, no training data. The skill
on display is turning messy, real administrative data into something a
client could actually rely on.

## The scenario

> I'm a Data Analyst on a Data Delivery team. A client needs a monthly,
> validated dataset of UK companies enriched with location and industry
> information, delivered as a clean, documented extract with a QA sign-off
> attached.

The client and requirement are fictional (see
[`docs/client_requirements.md`](docs/client_requirements.md)). The company,
postcode and industry data behind it is entirely real - see
[`data/reference/SOURCES.md`](data/reference/SOURCES.md).

## Data sources (all real, all open, all cited)

| Source | What it provides |
|---|---|
| [Companies House Free Company Data Product](https://download.companieshouse.gov.uk/en_output.html) | Company registration, status, dates, SIC codes - 2026-09-01 snapshot |
| [ONS Postcode Directory (Live)](https://geoportal.statistics.gov.uk/datasets/ons::online-ons-postcode-directory-live/about) | Postcode → local authority / region |
| [ONS Local Authority Districts (Apr 2025) Names & Codes](https://geoportal.statistics.gov.uk/) | Local authority code → name |
| UK SIC 2007 | Industry classification, embedded by Companies House and mapped to section by `sql/04_enrich_industry.sql` |

Full provenance, licences and match rates: [`data/reference/SOURCES.md`](data/reference/SOURCES.md).

## Pipeline

```
raw_companies ─┐
postcode_lookup ├─► clean ─► enrich geography ─► enrich industry ─► reconcile ─► validate ─► deliver
lad_lookup ─────┘                                       ▲
                                            (SIC join fan-out found & fixed here -
                                             see Root cause analysis below)
```

```bash
pip install -r requirements.txt
python3 src/ingest.py            # load data/reference/*.csv → delivery.duckdb
python3 src/transform.py         # sql/02–05: clean, enrich, reconcile
pytest tests/test_data_quality.py -v   # automated QA gate
python3 src/validate.py          # human-readable outputs/qa_report.md
python3 src/export_delivery.py   # sql/07 → outputs/client_delivery_full.csv
```

Fully reproducible offline from the committed `data/reference/*.csv`
extracts - no network access or API keys needed to run the pipeline itself.
Full stage-by-stage explanation: [`docs/methodology.md`](docs/methodology.md).
Operational runbook for a recurring monthly release:
[`docs/delivery_runbook.md`](docs/delivery_runbook.md).

## Root cause analysis

Two incidents are documented in
[`docs/root_cause_analysis.md`](docs/root_cause_analysis.md) - one simulated,
one real. Both are labelled as such, because being straight about which is
which matters more than looking impressive.

**Incident 1 (deliberately introduced).** A realistic delivery defect, built
into the pipeline on purpose to demonstrate detection, root-cause analysis,
remediation and regression testing: joining companies to their SIC codes the
naive way inflates the row count by **32%** (63,876 → 84,368 rows), because
~20% of companies have more than one SIC code on file. The broken query is
kept in `sql/04_enrich_industry.sql`, clearly marked, immediately above the
fix - the numbers quoted are the real output of running it against the real
data. The automated uniqueness check catches it, and a regression test now
prevents it recurring.

**Incident 2 (a real finding in the source data).** 627 companies carry a
non-standard SIC code - 140 legacy SIC 2003 four-digit codes and 487 with
Companies House's own `"None Supplied"` placeholder. This one was not
planted: it surfaced from the real Companies House register during QA, was
investigated, quantified and handled explicitly rather than silently
misclassified.

## Quality assurance

Every delivery runs the same checks two ways: `tests/test_data_quality.py`
as a hard pytest gate, and `sql/06_data_quality_checks.sql` /
`src/validate.py` producing the human-readable sign-off report attached to
every handover:

```
DELIVERY QA REPORT
==============================================
Source records received:          63,876
Records after transformation:      63,876
Delivered (status = Active):       58,226
Excluded (not Active status):       5,650
Postcode match rate:               100.0%  PASS
SIC match rate:                     99.2%  PASS

company_number not null ......................... PASS
company_number unique ........................... PASS
incorporation_date not in future ................ PASS
sic_code well-formed (4 or 5 digits, where present)  PASS
postcode well-formed (where present) ............ PASS
geography within client-requested scope ......... PASS

DELIVERY STATUS: APPROVED
```

Checks cover completeness, uniqueness, validity, referential integrity,
business rules and month-on-month reconciliation. Full report:
[`outputs/qa_report.md`](outputs/qa_report.md).

## SQL techniques used

Multi-CTE transformations, window functions (`ROW_NUMBER`, `STRING_AGG ...
ORDER BY`), `FULL OUTER JOIN` / `LEFT JOIN` reconciliation diffs,
`REGEXP_MATCHES` validation, `TRY_STRPTIME` / `TRY_CAST` defensive type
casting, `DATE_DIFF`, and a deliberately-fan-out `JOIN` kept in the codebase
(`sql/04_enrich_industry.sql`) alongside its fix, for the investigation to
be inspectable rather than just described. See [`sql/`](sql/) for all seven
numbered files in pipeline order.

## Repository structure

```
data/
  reference/       real, scoped input extracts + SOURCES.md
  sample/           500-row sample of the final delivery
sql/                01-07, run in order by src/transform.py and src/export_delivery.py
src/                ingest.py, transform.py, validate.py, export_delivery.py
tests/              automated QA gate (pytest)
scripts/            one-off scripts originally used to build data/reference/*.csv
docs/               client_requirements, data_dictionary, root_cause_analysis,
                    methodology, delivery_runbook
outputs/            qa_report.md, client_delivery_full.csv, reconciliation_report.csv
                    (generated - not committed, see .gitignore)
```

## Documentation

- [`docs/client_requirements.md`](docs/client_requirements.md) - the agreed business requirement and acceptance criteria
- [`docs/data_dictionary.md`](docs/data_dictionary.md) - every field, source and known data-quality characteristic
- [`docs/root_cause_analysis.md`](docs/root_cause_analysis.md) - both incidents, in full
- [`docs/methodology.md`](docs/methodology.md) - why each design decision was made
- [`docs/delivery_runbook.md`](docs/delivery_runbook.md) - how a recurring monthly release actually runs
- [`data/reference/SOURCES.md`](data/reference/SOURCES.md) - exact data provenance and licensing
