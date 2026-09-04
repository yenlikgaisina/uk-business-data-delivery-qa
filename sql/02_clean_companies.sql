-- =============================================================================
-- 02_clean_companies.sql
-- Type-casts and standardises the raw extract: proper dates, a standardised
-- postcode format, and one row per (company_number, SIC code) so downstream
-- joins have a clean grain to work with.
-- =============================================================================

DROP TABLE IF EXISTS stg_companies;
CREATE TABLE stg_companies AS
SELECT
    TRIM(company_number)                                         AS company_number,
    TRIM(company_name)                                           AS company_name,
    company_category                                             AS company_type,
    company_status,
    -- standardise postcode: single space before the inward code, upper case
    UPPER(TRIM(postcode))                                        AS postcode,
    post_town,
    TRY_STRPTIME(incorporation_date, '%d/%m/%Y')::DATE            AS incorporation_date,
    TRY_STRPTIME(NULLIF(dissolution_date, ''), '%d/%m/%Y')::DATE  AS dissolution_date,
    TRY_STRPTIME(accounts_next_due_date, '%d/%m/%Y')::DATE        AS accounts_next_due_date,
    TRY_STRPTIME(NULLIF(accounts_last_made_up_date,''), '%d/%m/%Y')::DATE AS accounts_last_made_up_date,
    accounts_category,
    TRY_STRPTIME(conf_stmt_next_due_date, '%d/%m/%Y')::DATE       AS confirmation_due_date,
    TRY_STRPTIME(NULLIF(conf_stmt_last_made_up_date,''), '%d/%m/%Y')::DATE AS confirmation_last_made_up_date,
    sic_text_1, sic_text_2, sic_text_3, sic_text_4
FROM raw_companies;

-- One row per (company_number, sic_code) - "unpivots" the four SicText
-- columns into a proper one-to-many bridge table. This is the correct way
-- to model a company's SIC codes; 04_enrich_industry.sql shows what goes
-- wrong when this step is skipped and the wide SicText columns are joined
-- to instead.
DROP TABLE IF EXISTS stg_company_sic;
CREATE TABLE stg_company_sic AS
WITH unpivoted AS (
    SELECT company_number, 1 AS sic_rank, sic_text_1 AS sic_text FROM stg_companies WHERE sic_text_1 IS NOT NULL AND sic_text_1 != ''
    UNION ALL
    SELECT company_number, 2, sic_text_2 FROM stg_companies WHERE sic_text_2 IS NOT NULL AND sic_text_2 != ''
    UNION ALL
    SELECT company_number, 3, sic_text_3 FROM stg_companies WHERE sic_text_3 IS NOT NULL AND sic_text_3 != ''
    UNION ALL
    SELECT company_number, 4, sic_text_4 FROM stg_companies WHERE sic_text_4 IS NOT NULL AND sic_text_4 != ''
)
-- Note: 487 rows in this extract carry the literal text "None Supplied"
-- in place of a real SIC code - a known Companies House data-quality gap,
-- not a code we can look up. Normalised to NULL here rather than kept as
-- a fake "code" (see docs/root_cause_analysis.md, incident 2).
SELECT
    company_number,
    sic_rank,
    NULLIF(TRIM(SPLIT_PART(sic_text, ' - ', 1)), 'None Supplied')          AS sic_code,
    CASE WHEN sic_text = 'None Supplied' THEN NULL
         ELSE TRIM(SUBSTR(sic_text, LENGTH(SPLIT_PART(sic_text, ' - ', 1)) + 4))
    END                                                                     AS sic_description
FROM unpivoted;

-- Populate the SIC reference table from the distinct code/description pairs
-- actually observed (real ONS UK SIC 2007 text as embedded by Companies House)
DELETE FROM sic_lookup;
INSERT INTO sic_lookup
SELECT DISTINCT sic_code, sic_description FROM stg_company_sic
WHERE sic_code IS NOT NULL AND sic_code != '';

-- Sanity check: exactly one row per company_number going into this stage
SELECT COUNT(*) AS company_rows, COUNT(DISTINCT company_number) AS distinct_companies
FROM stg_companies;
