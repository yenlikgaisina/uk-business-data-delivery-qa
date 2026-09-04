# Delivery QA Report

Generated: 2026-09-04 20:34 UTC
Snapshot date: 2026-09-01 (Companies House data compiled to 31 Aug 2026)
Scope: Nottinghamshire (Nottingham, Rushcliffe, Gedling, Broxtowe, Ashfield, Mansfield, Newark and Sherwood, Bassetlaw)

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

## Informational findings (not delivery blockers)

- 140 companies (0.2%) carry a legacy 4-digit
  SIC 2003 code that was never re-filed under SIC 2007. Real Companies House
  data quality characteristic, not a pipeline defect - see
  docs/root_cause_analysis.md, incident 2.
- 487 companies (0.8%) have no SIC code
  recorded at all (source value "None Supplied").

## Notes

- All company, postcode and industry data is real, current, publicly
  published open data (Companies House Free Company Data Product,
  2026-09-01 snapshot; ONS Postcode Directory Live; ONS Local Authority
  Districts April 2025). See docs/data_dictionary.md for full sourcing.
- Incident 1 in docs/root_cause_analysis.md (a one-to-many SIC join that
  fans out company rows) is a DELIBERATELY INTRODUCED defect, included as a
  worked example of QA detection, root-cause analysis and regression
  control - not a real production incident. Incident 2 (legacy and missing
  SIC codes, above) is a genuine finding in the source register.
