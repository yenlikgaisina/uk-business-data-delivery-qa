"""
Automated QA gate. These are the same checks as sql/06_data_quality_checks.sql
and outputs/qa_report.md, expressed as pytest assertions so they can run in
CI and fail the build before a bad extract ever reaches export_delivery.py.

Run from the project root, after src/ingest.py and src/transform.py:

    pip install -r requirements.txt
    python3 src/ingest.py
    python3 src/transform.py
    pytest tests/test_data_quality.py -v
"""
import duckdb
import pytest

DB_PATH = "delivery.duckdb"

NOTTINGHAMSHIRE_DISTRICTS = (
    "Nottingham", "Rushcliffe", "Gedling", "Broxtowe",
    "Ashfield", "Mansfield", "Newark and Sherwood", "Bassetlaw",
)


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(DB_PATH, read_only=True)
    yield connection
    connection.close()


# --- completeness -----------------------------------------------------------

def test_company_number_not_null(con):
    n = con.execute(
        "SELECT COUNT(*) FROM stg_companies_industry "
        "WHERE company_number IS NULL OR company_number = ''"
    ).fetchone()[0]
    assert n == 0, f"{n} rows missing company_number"


def test_company_name_not_null(con):
    n = con.execute(
        "SELECT COUNT(*) FROM stg_companies_industry "
        "WHERE company_name IS NULL OR company_name = ''"
    ).fetchone()[0]
    assert n == 0, f"{n} rows missing company_name"


def test_incorporation_date_not_null(con):
    n = con.execute(
        "SELECT COUNT(*) FROM stg_companies_industry WHERE incorporation_date IS NULL"
    ).fetchone()[0]
    assert n == 0, f"{n} rows missing incorporation_date"


# --- uniqueness --------------------------------------------------------------

def test_company_number_unique(con):
    """
    Regression test for Incident 1 (docs/root_cause_analysis.md): a
    one-to-many join against the SIC bridge table previously fanned this
    table out to more than one row per company.
    """
    dupes = con.execute(
        "SELECT company_number, COUNT(*) FROM stg_companies_industry "
        "GROUP BY company_number HAVING COUNT(*) > 1"
    ).fetchall()
    assert dupes == [], f"{len(dupes)} duplicated company_number values, e.g. {dupes[:5]}"


def test_row_count_matches_expected(con):
    """Row count in stg_companies_industry must equal distinct companies in scope."""
    staged = con.execute("SELECT COUNT(*) FROM stg_companies_industry").fetchone()[0]
    scoped = con.execute("SELECT COUNT(DISTINCT company_number) FROM stg_companies_geo").fetchone()[0]
    assert staged == scoped, f"staged={staged} vs scoped={scoped} - possible join fan-out"


# --- validity ----------------------------------------------------------------

def test_incorporation_date_not_in_future(con):
    n = con.execute(
        "SELECT COUNT(*) FROM stg_companies_industry WHERE incorporation_date > CURRENT_DATE"
    ).fetchone()[0]
    assert n == 0, f"{n} companies with a future incorporation_date"


def test_sic_code_well_formed(con):
    """
    4 or 5 digits accepted (see Incident 2: legacy SIC 2003 codes are real
    and expected, not malformed) - anything outside that shape is a genuine
    format problem.
    """
    n = con.execute(
        "SELECT COUNT(*) FROM stg_companies_industry "
        "WHERE sic_code IS NOT NULL AND NOT REGEXP_MATCHES(sic_code, '^[0-9]{4,5}$')"
    ).fetchone()[0]
    assert n == 0, f"{n} companies with a malformed sic_code"


def test_postcode_well_formed(con):
    n = con.execute(
        "SELECT COUNT(*) FROM stg_companies_industry WHERE postcode IS NOT NULL "
        "AND NOT REGEXP_MATCHES(postcode, '^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$')"
    ).fetchone()[0]
    assert n == 0, f"{n} companies with a malformed postcode"


# --- referential integrity ---------------------------------------------------

def test_postcode_match_rate_within_scope(con):
    rate = con.execute(
        "SELECT ROUND(100.0 * COUNT(lad_code) / COUNT(*), 1) FROM stg_companies_industry"
    ).fetchone()[0]
    assert rate == 100.0, f"postcode match rate only {rate}% within the final Nottinghamshire scope"


# --- business rules -----------------------------------------------------------

def test_accounts_overdue_flag_uses_snapshot_date_not_run_date():
    """
    accounts_overdue_flag (sql/07_final_delivery.sql) must be derived from
    the fixed snapshot date (2026-09-01), never CURRENT_DATE - see
    docs/methodology.md on why re-running this pipeline later must not
    change historic flags. A static check on the SQL source rather than a
    query against the database: run against stg_companies_industry (this
    check runs before sql/07 has produced final_client_delivery, per
    docs/delivery_runbook.md), and deliberately does not compare against
    CURRENT_DATE, which would make a *query-based* version of this test's
    result depend on what day it happens to run.
    """
    sql_text = open("sql/07_final_delivery.sql").read()
    flag_line = next(
        line for line in sql_text.splitlines() if "accounts_overdue_flag" in line.lower()
    )
    assert "CURRENT_DATE" not in flag_line.upper(), (
        "accounts_overdue_flag must not be computed from CURRENT_DATE: " + flag_line
    )
    assert "2026-09-01" in flag_line, (
        "accounts_overdue_flag should be computed against the fixed snapshot date: " + flag_line
    )


def test_geography_within_client_scope(con):
    rows = con.execute(
        f"SELECT DISTINCT local_authority FROM stg_companies_industry "
        f"WHERE local_authority NOT IN {NOTTINGHAMSHIRE_DISTRICTS} AND local_authority IS NOT NULL"
    ).fetchall()
    assert rows == [], f"out-of-scope local authorities found: {rows}"


# --- informational (non-blocking) --------------------------------------------

def test_known_sic_data_quality_characteristics_are_quantified(con):
    """
    Not an assertion that these are zero - Incident 2 established they're
    real and expected. This test just guards against the counts silently
    drifting to an unexpectedly large share of the dataset.
    """
    total = con.execute("SELECT COUNT(*) FROM stg_companies_industry").fetchone()[0]
    legacy, missing = con.execute(
        "SELECT COUNT(*) FILTER (WHERE LENGTH(sic_code) = 4), "
        "COUNT(*) FILTER (WHERE sic_code IS NULL) FROM stg_companies_industry"
    ).fetchone()
    assert legacy / total < 0.05, f"legacy SIC 2003 codes jumped to {legacy}/{total}"
    assert missing / total < 0.05, f"missing SIC codes jumped to {missing}/{total}"
