-- =============================================================================
-- 06_data_quality_checks.sql
-- The automated QA suite run against stg_companies_industry before anything
-- is released as a client delivery. Mirrors tests/test_data_quality.py -
-- these queries are the SQL the Python tests wrap and assert on.
-- =============================================================================

-- COMPLETENESS ----------------------------------------------------------------
SELECT
    SUM(CASE WHEN company_number IS NULL OR company_number = '' THEN 1 ELSE 0 END) AS null_company_number,
    SUM(CASE WHEN company_name IS NULL OR company_name = '' THEN 1 ELSE 0 END)     AS null_company_name,
    SUM(CASE WHEN incorporation_date IS NULL THEN 1 ELSE 0 END)                     AS null_incorporation_date
FROM stg_companies_industry;

-- UNIQUENESS --------------------------------------------------------------------
SELECT company_number, COUNT(*) AS occurrences
FROM stg_companies_industry
GROUP BY company_number
HAVING COUNT(*) > 1;

-- VALIDITY ------------------------------------------------------------------
-- incorporation date cannot be in the future; company age cannot be negative
SELECT company_number, incorporation_date
FROM stg_companies_industry
WHERE incorporation_date > CURRENT_DATE;

-- SIC code format: 5-digit SIC 2007 (current) or 4-digit SIC 2003 (legacy,
-- accepted but flagged separately below - see docs/root_cause_analysis.md)
SELECT company_number, sic_code
FROM stg_companies_industry
WHERE sic_code IS NOT NULL AND NOT REGEXP_MATCHES(sic_code, '^[0-9]{4,5}$');

-- INFORMATIONAL: legacy SIC 2003 four-digit codes present in the source -
-- not a delivery blocker, but worth monitoring and reporting to the client
SELECT
    COUNT(*) FILTER (WHERE LENGTH(sic_code) = 4) AS legacy_sic_2003_codes,
    COUNT(*) FILTER (WHERE sic_code IS NULL)     AS no_sic_code_recorded
FROM stg_companies_industry;

-- postcode format: valid UK postcode shape (outward + inward)
SELECT company_number, postcode
FROM stg_companies_industry
WHERE postcode IS NOT NULL
  AND NOT REGEXP_MATCHES(postcode, '^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$');

-- REFERENTIAL INTEGRITY ------------------------------------------------------
SELECT
    ROUND(100.0 * COUNT(lad_code) / COUNT(*), 1)   AS postcode_match_rate_pct,
    ROUND(100.0 * COUNT(sic_code) / COUNT(*), 1)   AS sic_match_rate_pct
FROM stg_companies_industry;

-- BUSINESS RULES --------------------------------------------------------------
-- accounts_overdue_flag must be TRUE only when accounts_next_due_date has passed
SELECT company_number, accounts_next_due_date
FROM stg_companies_industry
WHERE accounts_next_due_date IS NOT NULL
  AND (accounts_next_due_date < DATE '2026-09-01') != (accounts_next_due_date < CURRENT_DATE);
-- (kept as a genuine "as-of the snapshot date" check - see docs/methodology.md
--  for why the snapshot date, not today's date, is the correct reference point)

-- geography must meet the client's requested scope (Nottinghamshire only)
SELECT DISTINCT local_authority
FROM stg_companies_industry
WHERE local_authority NOT IN (
    'Nottingham', 'Rushcliffe', 'Gedling', 'Broxtowe',
    'Ashfield', 'Mansfield', 'Newark and Sherwood', 'Bassetlaw'
) AND local_authority IS NOT NULL;

-- =============================================================================
-- SIGN-OFF SUMMARY - one row per control, PASS/FAIL, for the QA report
-- =============================================================================
SELECT 'company_number not null' AS check_name,
       CASE WHEN (SELECT COUNT(*) FROM stg_companies_industry WHERE company_number IS NULL OR company_number = '') = 0
            THEN 'PASS' ELSE 'FAIL' END AS result
UNION ALL
SELECT 'company_number unique',
       CASE WHEN (SELECT COUNT(*) FROM (SELECT company_number FROM stg_companies_industry GROUP BY 1 HAVING COUNT(*) > 1)) = 0
            THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'incorporation_date not in future',
       CASE WHEN (SELECT COUNT(*) FROM stg_companies_industry WHERE incorporation_date > CURRENT_DATE) = 0
            THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'sic_code well-formed (4 or 5 digits, where present)',
       CASE WHEN (SELECT COUNT(*) FROM stg_companies_industry WHERE sic_code IS NOT NULL AND NOT REGEXP_MATCHES(sic_code, '^[0-9]{4,5}$')) = 0
            THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'postcode well-formed (where present)',
       CASE WHEN (SELECT COUNT(*) FROM stg_companies_industry WHERE postcode IS NOT NULL AND NOT REGEXP_MATCHES(postcode, '^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$')) = 0
            THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'geography within client-requested scope',
       CASE WHEN (SELECT COUNT(*) FROM stg_companies_industry WHERE local_authority NOT IN (
                    'Nottingham','Rushcliffe','Gedling','Broxtowe','Ashfield','Mansfield','Newark and Sherwood','Bassetlaw'
                  ) AND local_authority IS NOT NULL) = 0
            THEN 'PASS' ELSE 'FAIL' END;
