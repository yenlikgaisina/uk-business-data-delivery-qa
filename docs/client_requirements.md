# Client requirements

A short, realistic requirements document of the kind a data delivery analyst
would agree with a stakeholder before building a pipeline. The "client" here
is fictional; the underlying company, postcode and industry data is real.

## Business requirement

> The client needs a monthly, validated dataset of registered businesses in
> Nottinghamshire, enriched with location and industry information, to
> support operational planning. Each company must appear exactly once. The
> delivery must contain valid company identifiers, standardised postcodes,
> industry classification and filing-status information. Month-on-month
> changes and unexpected data-quality issues must be investigated before
> delivery.

## Scope

- **Geography:** Nottingham City and Nottinghamshire county (the local
  authority districts of Nottingham, Rushcliffe, Gedling, Broxtowe,
  Ashfield, Mansfield, Newark and Sherwood, and Bassetlaw)
- **Population:** companies with `CompanyStatus = Active` in the Companies
  House Free Company Data Product
- **Refresh cadence:** monthly, aligned to the Companies House snapshot
  publication schedule (within 5 working days of month-end)

## Acceptance criteria

- One row per company in the final delivery (`company_number` unique)
- UTF-8 CSV, comma-delimited, header row included
- `company_number` mandatory on every row
- Registered postcode standardised to `OUTWARD INWARD` format
- SIC description populated wherever a SIC code is present in the source
- Local authority populated wherever the postcode matches the ONS
  Postcode Directory
- Every delivery includes a `snapshot_date` column
- Zero duplicate `company_number` values
- A QA sign-off report (`outputs/qa_report.md`) is supplied alongside every
  extract
- Any month-on-month change greater than 5% in the delivered row count is
  investigated and explained before the delivery is released (see
  `docs/root_cause_analysis.md` for how the +32% incident found while
  building this pipeline was actually handled)

## Fields agreed for the final extract

See `docs/data_dictionary.md` for the full field-by-field specification.
