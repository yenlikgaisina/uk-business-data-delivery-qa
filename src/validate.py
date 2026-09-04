"""
Runs the automated QA suite (sql/06_data_quality_checks.sql) against the
transformed data and writes outputs/qa_report.md - the sign-off document
that would accompany every client handover.

Run from the project root, after src/transform.py: python3 src/validate.py
"""
import duckdb
from datetime import datetime, timezone

DB_PATH = "delivery.duckdb"


def main():
    con = duckdb.connect(DB_PATH)

    source = con.execute("SELECT COUNT(*) FROM raw_companies").fetchone()[0]
    transformed = con.execute("SELECT COUNT(*) FROM stg_companies_industry").fetchone()[0]
    active_only = con.execute("SELECT COUNT(*) FROM stg_companies_industry WHERE company_status='Active'").fetchone()[0]
    excluded = transformed - active_only

    checks = con.execute("""
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
                    THEN 'PASS' ELSE 'FAIL' END
    """).fetchall()

    postcode_rate, sic_rate = con.execute("""
        SELECT ROUND(100.0 * COUNT(lad_code) / COUNT(*), 1),
               ROUND(100.0 * COUNT(sic_code) / COUNT(*), 1)
        FROM stg_companies_industry
    """).fetchone()

    legacy_sic, missing_sic = con.execute("""
        SELECT COUNT(*) FILTER (WHERE LENGTH(sic_code) = 4),
               COUNT(*) FILTER (WHERE sic_code IS NULL)
        FROM stg_companies_industry
    """).fetchone()

    overall = "APPROVED" if all(r[1] == "PASS" for r in checks) else "BLOCKED - see failing checks"

    lines = []
    lines.append("# Delivery QA Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Snapshot date: 2026-09-01 (Companies House data compiled to 31 Aug 2026)")
    lines.append(f"Scope: Nottinghamshire (Nottingham, Rushcliffe, Gedling, Broxtowe, Ashfield, Mansfield, Newark and Sherwood, Bassetlaw)")
    lines.append("")
    lines.append("```")
    lines.append("DELIVERY QA REPORT")
    lines.append("=" * 46)
    lines.append(f"Source records received:      {source:>10,}")
    lines.append(f"Records after transformation:  {transformed:>10,}")
    lines.append(f"Delivered (status = Active):   {active_only:>10,}")
    lines.append(f"Excluded (not Active status):  {excluded:>10,}")
    lines.append(f"Postcode match rate:              {postcode_rate:>6}%  {'PASS' if postcode_rate >= 95 else 'REVIEW'}")
    lines.append(f"SIC match rate:                   {sic_rate:>6}%  {'PASS' if sic_rate >= 95 else 'REVIEW'}")
    lines.append("")
    for name, result in checks:
        pad = "." * (48 - len(name))
        lines.append(f"{name} {pad} {result}")
    lines.append("")
    lines.append(f"DELIVERY STATUS: {overall}")
    lines.append("```")
    lines.append("")
    lines.append("## Informational findings (not delivery blockers)")
    lines.append("")
    lines.append(f"- {legacy_sic} companies ({legacy_sic/transformed*100:.1f}%) carry a legacy 4-digit")
    lines.append("  SIC 2003 code that was never re-filed under SIC 2007. Real Companies House")
    lines.append("  data quality characteristic, not a pipeline defect - see")
    lines.append("  docs/root_cause_analysis.md, incident 2.")
    lines.append(f"- {missing_sic} companies ({missing_sic/transformed*100:.1f}%) have no SIC code")
    lines.append("  recorded at all (source value \"None Supplied\").")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- All company, postcode and industry data is real, current, publicly")
    lines.append("  published open data (Companies House Free Company Data Product,")
    lines.append("  2026-09-01 snapshot; ONS Postcode Directory Live; ONS Local Authority")
    lines.append("  Districts April 2025). See docs/data_dictionary.md for full sourcing.")
    lines.append("- A deliberately broken transformation (a one-to-many SIC join that fans")
    lines.append("  out company rows) was found, root-caused and fixed during this pipeline's")
    lines.append("  build - see docs/root_cause_analysis.md.")

    with open("outputs/qa_report.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    con.close()


if __name__ == "__main__":
    main()
