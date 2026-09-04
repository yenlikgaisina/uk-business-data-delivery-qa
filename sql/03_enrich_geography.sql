-- =============================================================================
-- 03_enrich_geography.sql
-- Joins the cleaned companies to real ONS geography: postcode -> local
-- authority district -> region, via the ONS Postcode Directory (Live) and
-- the ONS Local Authority Districts names/codes lookup.
-- =============================================================================

DROP TABLE IF EXISTS stg_companies_geo;
CREATE TABLE stg_companies_geo AS
SELECT
    c.*,
    pl.lad_code,
    pl.region_code,
    l.lad_name AS local_authority
FROM stg_companies c
LEFT JOIN postcode_lookup pl ON pl.postcode = c.postcode   -- LEFT JOIN: unmatched postcodes are kept and flagged, not dropped
LEFT JOIN lad_lookup l ON l.lad_code = pl.lad_code;

-- Postcode match-rate check - feeds the QA report
SELECT
    COUNT(*)                                                        AS total_companies,
    COUNT(lad_code)                                                 AS postcode_matched,
    ROUND(100.0 * COUNT(lad_code) / COUNT(*), 1)                    AS postcode_match_rate_pct
FROM stg_companies_geo;

-- Which postcodes failed to match, for investigation (typically PO boxes,
-- very recently issued postcodes not yet in the live directory, or a
-- formatting mismatch worth fixing upstream)
SELECT postcode, COUNT(*) AS affected_companies
FROM stg_companies_geo
WHERE lad_code IS NULL
GROUP BY postcode
ORDER BY affected_companies DESC
LIMIT 20;
