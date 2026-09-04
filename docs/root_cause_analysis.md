# Root cause analysis

Two incidents are documented here. **Incident 1 was deliberately introduced**
as part of this portfolio case study - a realistic delivery defect planted to
demonstrate detection, root-cause analysis, remediation and regression
testing. **Incident 2 is a genuine data-quality finding** in the real
Companies House register, discovered through the QA process rather than
planted.

Both are left in the codebase (`sql/04_enrich_industry.sql` still contains
the broken query, clearly labelled) rather than tidied away, because the
investigation is the point.

---

## Incident 1: delivery row count 32% higher than expected

> **Simulated, not a production incident.** This defect was written into the
> pipeline on purpose, as a realistic worked example of a fault a data
> delivery analyst genuinely does meet. The scenario is constructed; the
> numbers below are not - they are the real output of running the broken
> query against the real Companies House extract in `data/reference/`.

**Detection.** The automated uniqueness check
(`company_number` must appear exactly once) fails on the broken
transformation.
Expected row count (one per company in scope): **63,876**. Actual row count
in the delivery candidate: **84,368** - 20,492 more rows than there should
have been, a 32.1% inflation.

**Impact.** Had this shipped, the client would have received duplicate
company records - every company with more than one SIC code on file would
appear once per SIC code, corrupting any downstream count or join on
`company_number`.

**Investigation.** Isolating a handful of the duplicated `company_number`
values (e.g. `00304247`, appearing 4 times) and inspecting the source data
showed each affected company had 2-4 populated `SicText_n` fields. Companies
House allows up to four SIC codes per company; 12,900 of the 63,876
companies in scope (20.2%) have more than one.

**Root cause.** The transformation joined the one-row-per-company staging
table directly to `stg_company_sic`, which is intentionally modelled as one
row per `(company_number, sic_code)` - the correct shape for "a company can
have many SIC codes". Joining a 1-row-per-company table to a
many-rows-per-company table on `company_number`, without first collapsing
to a single row per company, produces exactly one output row per matching
SIC code - a classic join fan-out. The query ran without error; it just
returned the wrong number, silently.

**Corrective action.** Defined a single **primary SIC code** per company
(rank 1, i.e. `SicText_1` - the field Companies House itself treats as
primary) and aggregated any secondary codes into a separate
`secondary_sic_codes` column instead of letting them multiply rows. See
`sql/04_enrich_industry.sql` for the broken query (kept, clearly marked
`_BROKEN`) immediately followed by the fix.

**Validation.** Re-running the uniqueness check against the corrected table
(`stg_companies_industry`) returns zero duplicate `company_number` values;
row count matches the expected 63,876 exactly.

**Preventative action.** The uniqueness check now runs as an automated,
non-optional gate in `sql/06_data_quality_checks.sql` /
`tests/test_data_quality.py` before any extract is exported - a repeat of
this fan-out on a future SIC-related join would fail the pipeline
immediately rather than reach a client.

---

## Incident 2: 627 companies with a non-standard SIC code

> **Real, not simulated.** Unlike Incident 1, nothing here was planted. These
> are genuine characteristics of the live Companies House register that this
> pipeline's QA surfaced, investigated and handled.

**Detection.** The SIC-code format validity check
(`sql/06_data_quality_checks.sql`) flagged 627 companies whose SIC code did
not match the expected 5-digit SIC 2007 pattern.

**Investigation.** Grouping the offending values by length showed two
distinct, genuine source data-quality issues, not a parsing bug:

- **140 companies** have a 4-digit code (e.g. `5010`, `4521`, `2125`).
  Cross-checking a sample against Companies House's own published field
  documentation confirmed these are legacy **SIC 2003** codes - the
  classification scheme in use before SIC 2007 was introduced. These
  companies have simply never re-filed a confirmation statement that would
  trigger a refresh to the current 5-digit scheme, so the old code has
  persisted in the register for decades in some cases (one affected company
  was incorporated in 1875).
- **487 companies** have the literal source value `"None Supplied"` in
  place of a SIC code - Companies House's own placeholder for "no
  classification on file", not a code to look up.

**Root cause.** Real, upstream source data-quality gaps in Companies House's
register, not an artefact of this pipeline. Mapping a 4-digit SIC 2003 code
through the SIC 2007 section-boundary logic used for current codes would
silently misclassify these companies (the numbering schemes overlap but
mean different things), which would have been a second, quieter version of
Incident 1.

**Corrective action.**
1. `"None Supplied"` is normalised to `NULL` during cleaning
   (`sql/02_clean_companies.sql`) rather than kept as a fake code string.
2. The SIC-format validity check was widened to accept both 4-digit
   (legacy) and 5-digit (current) codes as *well-formed*, since both are
   genuine, expected values in this source - but `primary_industry` labels
   4-digit and missing codes explicitly (`"Not classified (legacy SIC 2003
   code - not migrated)"` / `"Not classified (no SIC code recorded)"`)
   instead of guessing a section for them.

**Validation.** The QA report now shows these as an explicit, quantified
informational finding (not a pass/fail blocker), and `primary_industry`
never claims a section for a code it can't reliably classify.

**Preventative action.** Any future SIC-derived field takes the same
"classify only current 5-digit codes, label everything else explicitly"
approach - encoded once in `sql/04_enrich_industry.sql`, not re-implemented
per report.

---

## A note on the month-on-month reconciliation

This pipeline was built from a single Companies House snapshot (the free
product only ever publishes the current month - it does not archive
history). `sql/05_monthly_reconciliation.sql` and
`docs/delivery_runbook.md` explain exactly what that does and doesn't allow
to be measured honestly, and what changes (nothing, by design) the next
time this pipeline runs against a second real monthly snapshot.
