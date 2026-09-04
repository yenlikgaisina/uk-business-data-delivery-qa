-- =============================================================================
-- 04_enrich_industry.sql
-- Joins industry classification onto each company - and deliberately shows
-- the wrong way to do it before the right way. See docs/root_cause_analysis.md
-- for the incident write-up this section reproduces.
--
-- A company can legitimately have up to four SIC codes (SicText_1..4). The
-- client delivery needs exactly one row per company_number. Joining directly
-- to a table keyed on (company_number, sic_code) - the natural, correct
-- shape of "a company has many SIC codes" - creates a one-to-many join and
-- silently multiplies every multi-SIC company's row in the output.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- BROKEN: join stg_companies_geo directly to stg_company_sic
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS _delivery_candidate_BROKEN;
CREATE TABLE _delivery_candidate_BROKEN AS
SELECT
    g.company_number,
    g.company_name,
    s.sic_code,
    s.sic_description
FROM stg_companies_geo g
JOIN stg_company_sic s ON s.company_number = g.company_number;   -- <- one-to-many fan-out

SELECT
    (SELECT COUNT(*) FROM stg_companies_geo)          AS expected_company_count,
    (SELECT COUNT(*) FROM _delivery_candidate_BROKEN)  AS actual_row_count_BROKEN,
    (SELECT COUNT(*) FROM _delivery_candidate_BROKEN)
        - (SELECT COUNT(*) FROM stg_companies_geo)     AS excess_rows;

-- QA uniqueness check catches it immediately:
SELECT company_number, COUNT(*) AS times_appearing
FROM _delivery_candidate_BROKEN
GROUP BY company_number
HAVING COUNT(*) > 1
ORDER BY times_appearing DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- ROOT CAUSE (see docs/root_cause_analysis.md for the full write-up):
-- stg_company_sic is one row per (company_number, sic_code) by design -
-- joining a one-row-per-company table directly to it, without first
-- collapsing to one row per company, will always fan out for every company
-- that has more than one SIC code.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- FIX: decide a single "primary SIC" per company (rank 1, i.e. SicText_1 -
-- this is what Companies House itself treats as the primary classification),
-- and aggregate any secondary codes into a separate column instead of
-- fanning out rows.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS stg_companies_industry;
CREATE TABLE stg_companies_industry AS
WITH primary_sic AS (
    SELECT company_number, sic_code, sic_description
    FROM stg_company_sic
    WHERE sic_rank = 1
),
secondary_sic AS (
    SELECT company_number,
           STRING_AGG(sic_code, ', ' ORDER BY sic_rank) AS secondary_sic_codes
    FROM stg_company_sic
    WHERE sic_rank > 1
    GROUP BY company_number
)
SELECT
    g.*,
    p.sic_code,
    p.sic_description,
    sec.secondary_sic_codes,
    -- Standard UK SIC 2007 section grouping, derived from the 2-digit
    -- division - only valid for current 5-digit SIC 2007 codes. 140
    -- companies in this extract still carry a legacy 4-digit SIC 2003 code
    -- (never re-filed under SIC 2007); mapping those through the SIC 2007
    -- section ranges would silently misclassify them, so they're labelled
    -- explicitly instead. See docs/root_cause_analysis.md, incident 2.
    CASE
        WHEN p.sic_code IS NULL                    THEN 'Not classified (no SIC code recorded)'
        WHEN LENGTH(p.sic_code) = 4                 THEN 'Not classified (legacy SIC 2003 code - not migrated)'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 1 AND 3   THEN 'Agriculture, Forestry & Fishing'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 5 AND 9   THEN 'Mining & Quarrying'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 10 AND 33 THEN 'Manufacturing'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) = 35              THEN 'Electricity, Gas & Air Conditioning Supply'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 36 AND 39 THEN 'Water Supply, Sewerage & Waste Management'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 41 AND 43 THEN 'Construction'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 45 AND 47 THEN 'Wholesale & Retail Trade'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 49 AND 53 THEN 'Transportation & Storage'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 55 AND 56 THEN 'Accommodation & Food Service'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 58 AND 63 THEN 'Information & Communication'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 64 AND 66 THEN 'Financial & Insurance Activities'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) = 68              THEN 'Real Estate Activities'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 69 AND 75 THEN 'Professional, Scientific & Technical'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 77 AND 82 THEN 'Administrative & Support Service'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) = 84              THEN 'Public Administration & Defence'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) = 85              THEN 'Education'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 86 AND 88 THEN 'Human Health & Social Work'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 90 AND 93 THEN 'Arts, Entertainment & Recreation'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 94 AND 96 THEN 'Other Service Activities'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) BETWEEN 97 AND 98 THEN 'Households as Employers'
        WHEN TRY_CAST(SUBSTR(p.sic_code, 1, 2) AS INTEGER) = 99              THEN 'Extraterritorial Organisations'
        ELSE 'Not classified'
    END AS primary_industry
FROM stg_companies_geo g
LEFT JOIN primary_sic p ON p.company_number = g.company_number
LEFT JOIN secondary_sic sec ON sec.company_number = g.company_number;

-- CORRECTED uniqueness check - zero rows expected
SELECT company_number, COUNT(*) AS times_appearing
FROM stg_companies_industry
GROUP BY company_number
HAVING COUNT(*) > 1;

SELECT COUNT(*) AS final_row_count, COUNT(DISTINCT company_number) AS distinct_companies
FROM stg_companies_industry;
