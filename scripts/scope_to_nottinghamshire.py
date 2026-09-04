"""
Joins the three raw_downloads/ files produced by the previous three scripts
and narrows the broad East-Midlands pre-filter down to the client's actual
scope (docs/client_requirements.md): Nottingham City and the seven
Nottinghamshire districts.

This is the one place that scope is defined - fetch_companies_house.py
deliberately over-fetches (a wider postcode-area prefix) so that a future
scope change (e.g. adding Derbyshire) only means editing the list below and
re-running this script, not re-downloading the ~2.8GB national file.

Reads:
    raw_downloads/companies_pre_filtered.csv
    raw_downloads/postcode_lookup.csv
    raw_downloads/lad_lookup.csv

Writes the three files this repository actually ships with:
    data/reference/companies_house_raw_extract.csv
    data/reference/postcode_lookup.csv
    data/reference/lad_lookup.csv
"""
import csv

import duckdb

NOTTINGHAMSHIRE_DISTRICTS = {
    "Nottingham",
    "Rushcliffe",
    "Gedling",
    "Broxtowe",
    "Ashfield",
    "Mansfield",
    "Newark and Sherwood",
    "Bassetlaw",
}

# Companies House raw_companies columns, in the order this repo's
# sql/01_create_tables.sql expects. Note geography (lad_code, region_code)
# is deliberately NOT joined into this file - it stays a "raw" one-row-
# per-company extract, and geography is enriched later by the pipeline
# itself (sql/03_enrich_geography.sql), so that step has real work to do.
COMPANIES_COLUMNS = [
    "company_name",
    "company_number",
    "postcode",
    "post_town",
    "company_category",
    "company_status",
    "country_of_origin",
    "dissolution_date",
    "incorporation_date",
    "accounts_next_due_date",
    "accounts_last_made_up_date",
    "accounts_category",
    "conf_stmt_next_due_date",
    "conf_stmt_last_made_up_date",
    "sic_text_1",
    "sic_text_2",
    "sic_text_3",
    "sic_text_4",
]


def main():
    con = duckdb.connect()

    con.execute(
        "CREATE TABLE companies AS SELECT * FROM read_csv_auto("
        "'raw_downloads/companies_pre_filtered.csv', all_varchar=True)"
    )
    con.execute(
        "CREATE TABLE postcodes AS SELECT * FROM read_csv_auto("
        "'raw_downloads/postcode_lookup.csv', all_varchar=True)"
    )
    con.execute(
        "CREATE TABLE lads AS SELECT * FROM read_csv_auto("
        "'raw_downloads/lad_lookup.csv', all_varchar=True)"
    )

    lad_list = ", ".join("'" + d + "'" for d in NOTTINGHAMSHIRE_DISTRICTS)

    # Which company_numbers fall inside the Nottinghamshire scope, judged by
    # postcode -> LAD -> LAD name (this join is ONLY used to decide scope
    # here; the shipped companies_house_raw_extract.csv stays un-enriched).
    con.execute(
        f"""
        CREATE TABLE in_scope AS
        SELECT DISTINCT c.company_number
        FROM companies c
        JOIN postcodes p ON p.postcode = c.postcode
        JOIN lads l ON l.lad_code = p.lad_code
        WHERE l.lad_name IN ({lad_list})
        """
    )
    n_scope = con.execute("SELECT COUNT(*) FROM in_scope").fetchone()[0]
    print(f"{n_scope} companies fall within the Nottinghamshire scope")

    cols = ", ".join(COMPANIES_COLUMNS)
    con.execute(
        f"""
        COPY (
            SELECT {cols}
            FROM companies
            WHERE company_number IN (SELECT company_number FROM in_scope)
        ) TO 'data/reference/companies_house_raw_extract.csv' (HEADER, DELIMITER ',')
        """
    )

    # Trim the postcode lookup to only postcodes actually present in the
    # scoped company extract, rather than shipping the full East-Midlands
    # lookup unnecessarily.
    con.execute(
        """
        COPY (
            SELECT DISTINCT p.postcode, p.lad_code, p.region_code
            FROM postcodes p
            WHERE p.postcode IN (
                SELECT DISTINCT postcode FROM companies
                WHERE company_number IN (SELECT company_number FROM in_scope)
            )
        ) TO 'data/reference/postcode_lookup.csv' (HEADER, DELIMITER ',')
        """
    )

    # lad_lookup ships in full (361 rows, ~8KB) - it's the standard national
    # lookup and there's no meaningful benefit to trimming it further.
    with open("raw_downloads/lad_lookup.csv") as src, open(
        "data/reference/lad_lookup.csv", "w", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=["lad_code", "lad_name"])
        writer.writeheader()
        for row in reader:
            writer.writerow(row)

    print("Wrote data/reference/companies_house_raw_extract.csv, postcode_lookup.csv, lad_lookup.csv")


if __name__ == "__main__":
    main()
