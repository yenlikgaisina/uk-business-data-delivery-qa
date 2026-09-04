"""
Loads the real source extracts into the DuckDB project database and creates
the raw/reference table structure (sql/01_create_tables.sql), exactly as
they were received - no cleaning happens here, that's sql/02 onward.

Run from the project root: python3 src/ingest.py
"""
import duckdb

DB_PATH = "delivery.duckdb"


def main():
    con = duckdb.connect(DB_PATH)

    with open("sql/01_create_tables.sql") as f:
        con.execute(f.read())

    con.execute("""
        INSERT INTO raw_companies
        SELECT
            company_name, company_number, postcode, post_town, company_category,
            company_status, country_of_origin, dissolution_date, incorporation_date,
            accounts_next_due_date, accounts_last_made_up_date, accounts_category,
            conf_stmt_next_due_date, conf_stmt_last_made_up_date,
            sic_text_1, sic_text_2, sic_text_3, sic_text_4
        FROM read_csv_auto('data/reference/companies_house_raw_extract.csv', ALL_VARCHAR=TRUE)
    """)
    con.execute("""
        INSERT INTO postcode_lookup
        SELECT postcode, lad_code, region_code
        FROM read_csv_auto('data/reference/postcode_lookup.csv', ALL_VARCHAR=TRUE)
    """)
    con.execute("""
        INSERT INTO lad_lookup
        SELECT lad_code, lad_name
        FROM read_csv_auto('data/reference/lad_lookup.csv', ALL_VARCHAR=TRUE)
    """)

    n_companies = con.execute("SELECT COUNT(*) FROM raw_companies").fetchone()[0]
    n_postcodes = con.execute("SELECT COUNT(*) FROM postcode_lookup").fetchone()[0]
    n_lads = con.execute("SELECT COUNT(*) FROM lad_lookup").fetchone()[0]
    print(f"Loaded: raw_companies={n_companies}, postcode_lookup={n_postcodes}, lad_lookup={n_lads}")

    con.close()


if __name__ == "__main__":
    main()
