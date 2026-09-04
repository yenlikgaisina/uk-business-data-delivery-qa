-- =============================================================================
-- 01_create_tables.sql
-- Raw / reference / staging / delivery table structure for the Nottinghamshire
-- business data delivery. Dialect: DuckDB.
--
-- SOURCES (all real, publicly published open data - see data/reference/SOURCES.md):
--   raw_companies     Companies House Free Company Data Product, 2026-09-01 snapshot,
--                      pre-filtered to Nottinghamshire postcodes
--   postcode_lookup   ONS Postcode Directory (Live) - postcode -> LAD & region codes
--   lad_lookup        ONS Local Authority Districts (April 2025) Names and Codes
-- =============================================================================

DROP TABLE IF EXISTS raw_companies;
DROP TABLE IF EXISTS postcode_lookup;
DROP TABLE IF EXISTS lad_lookup;
DROP TABLE IF EXISTS sic_lookup;

CREATE TABLE raw_companies (
    company_name                TEXT,
    company_number               TEXT,
    postcode                     TEXT,
    post_town                    TEXT,
    company_category             TEXT,
    company_status                TEXT,
    country_of_origin             TEXT,
    dissolution_date              TEXT,   -- DD/MM/YYYY text, as supplied
    incorporation_date            TEXT,
    accounts_next_due_date        TEXT,
    accounts_last_made_up_date    TEXT,
    accounts_category             TEXT,
    conf_stmt_next_due_date       TEXT,
    conf_stmt_last_made_up_date   TEXT,
    sic_text_1                    TEXT,   -- "62020 - Information technology consultancy activities"
    sic_text_2                    TEXT,
    sic_text_3                    TEXT,
    sic_text_4                    TEXT
);

CREATE TABLE postcode_lookup (
    postcode    TEXT,
    lad_code    TEXT,
    region_code TEXT
);

CREATE TABLE lad_lookup (
    lad_code TEXT,
    lad_name TEXT
);

-- Self-derived from the SIC text fields actually present in the extract
-- (Companies House embeds the SIC 2007 description in every SicText field,
-- so the code/description pairs used here are the real ONS UK SIC 2007
-- classification text as supplied by Companies House, not invented).
CREATE TABLE sic_lookup (
    sic_code        TEXT,
    sic_description TEXT
);
