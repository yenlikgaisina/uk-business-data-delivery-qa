-- =============================================================================
-- 07_final_delivery.sql
-- The validated, client-ready extract - one row per active Nottinghamshire
-- company, in exactly the shape agreed in docs/client_requirements.md.
-- =============================================================================

DROP TABLE IF EXISTS final_client_delivery;
CREATE TABLE final_client_delivery AS
SELECT
    company_number,
    company_name,
    company_status,
    company_type,
    incorporation_date,
    DATE_DIFF('year', incorporation_date, DATE '2026-09-01')          AS company_age_years,
    postcode,
    COALESCE(local_authority, 'Unmatched - see data-quality log')     AS local_authority,
    CASE WHEN region_code = 'E12000004' THEN 'East Midlands'
         WHEN region_code IS NULL THEN 'Unmatched - see data-quality log'
         ELSE region_code END                                        AS region,
    sic_code,
    sic_description,
    secondary_sic_codes,
    primary_industry,
    accounts_next_due_date                                            AS accounts_due_date,
    CASE WHEN accounts_next_due_date < DATE '2026-09-01' THEN 1 ELSE 0 END AS accounts_overdue_flag,
    confirmation_due_date                                             AS confirmation_due,
    DATE '2026-09-01'                                                 AS snapshot_date
FROM stg_companies_industry
WHERE company_status = 'Active'   -- per client requirement: currently-registered, actively trading companies
ORDER BY company_number;

-- Delivery sign-off counts - included at the top of every handover
SELECT
    (SELECT COUNT(*) FROM raw_companies)                     AS source_records_received,
    (SELECT COUNT(*) FROM stg_companies_industry)             AS records_after_transformation,
    (SELECT COUNT(*) FROM final_client_delivery)               AS records_delivered,
    (SELECT COUNT(*) FROM stg_companies_industry) - (SELECT COUNT(*) FROM final_client_delivery)
                                                                AS excluded_not_active_status,
    (SELECT COUNT(*) FROM final_client_delivery WHERE local_authority = 'Unmatched - see data-quality log')
                                                                AS delivered_with_unmatched_geography;
