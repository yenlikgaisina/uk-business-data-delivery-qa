"""
Downloads the latest Companies House Free Company Data Product (published as
7 zip parts), unzips it, and pre-filters it down to companies whose
registered postcode falls in a broad East Midlands postcode-area prefix
(DE, LE, LN, NG, NN, S) using DuckDB - cheap enough to do on the full ~5.5M
row national file without loading it all into Python.

Source: https://download.companieshouse.gov.uk/en_output.html
        (no registration or API key required)

Writes:
    raw_downloads/companies_pre_filtered.csv - one row per matched company,
        columns already renamed to match this repo's schema
    raw_downloads/unique_postcodes.csv - the distinct postcodes present in
        that file, input to fetch_ons_postcode_lookup.py

In production this step is replaced by simply receiving next month's
Companies House extract rather than re-downloading and re-filtering the
national file from scratch.
"""
import csv
import os
import zipfile

import duckdb
import requests

BASE_URL = "https://download.companieshouse.gov.uk"
SNAPSHOT = "BasicCompanyData-2026-09-01"
N_PARTS = 7
DOWNLOAD_DIR = "raw_downloads/zips"
CSV_DIR = "raw_downloads/csv"

# Broad East Midlands postcode-area pre-filter. Deliberately wider than the
# final Nottinghamshire scope (NG) so that scope_to_nottinghamshire.py, not
# this download step, is the single place the client's actual scope is
# defined.
EAST_MIDLANDS_PREFIXES = ("DE", "LE", "LN", "NG", "NN", "S")

# Raw Companies House column -> this repo's schema
COLUMN_MAP = {
    "CompanyName": "company_name",
    "CompanyNumber": "company_number",
    "RegAddress.PostCode": "postcode",
    "RegAddress.PostTown": "post_town",
    "CompanyCategory": "company_category",
    "CompanyStatus": "company_status",
    "CountryOfOrigin": "country_of_origin",
    "DissolutionDate": "dissolution_date",
    "IncorporationDate": "incorporation_date",
    "Accounts.NextDueDate": "accounts_next_due_date",
    "Accounts.LastMadeUpDate": "accounts_last_made_up_date",
    "Accounts.AccountCategory": "accounts_category",
    "ConfStmtNextDueDate": "conf_stmt_next_due_date",
    "ConfStmtLastMadeUpDate": "conf_stmt_last_made_up_date",
    "SICCode.SicText_1": "sic_text_1",
    "SICCode.SicText_2": "sic_text_2",
    "SICCode.SicText_3": "sic_text_3",
    "SICCode.SicText_4": "sic_text_4",
}


def download_and_unzip():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(CSV_DIR, exist_ok=True)
    for part in range(1, N_PARTS + 1):
        fname = f"{SNAPSHOT}-part{part}_{N_PARTS}.zip"
        zpath = os.path.join(DOWNLOAD_DIR, fname)
        if not os.path.exists(zpath):
            print(f"Downloading {fname} ...")
            resp = requests.get(f"{BASE_URL}/{fname}", stream=True, timeout=120)
            resp.raise_for_status()
            with open(zpath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        else:
            print(f"{fname} already downloaded, skipping")
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(CSV_DIR)


def prefilter_and_rename():
    con = duckdb.connect()
    src_cols = ", ".join(f'"{raw}" AS "{new}"' for raw, new in COLUMN_MAP.items())
    prefix_check = " OR ".join(
        f'"RegAddress.PostCode" LIKE \'{p}%\'' for p in EAST_MIDLANDS_PREFIXES
    )
    query = f"""
        COPY (
            SELECT {src_cols}
            FROM read_csv(
                '{CSV_DIR}/{SNAPSHOT}-part*_{N_PARTS}.csv',
                header=True, all_varchar=True, strict_mode=False,
                ignore_errors=True, max_line_size=10000000
            )
            WHERE {prefix_check}
        ) TO 'raw_downloads/companies_pre_filtered.csv' (HEADER, DELIMITER ',')
    """
    con.execute(query)
    n = con.execute(
        "SELECT COUNT(*) FROM read_csv_auto('raw_downloads/companies_pre_filtered.csv')"
    ).fetchone()[0]
    print(f"Pre-filtered to {n} companies in East Midlands postcode areas")

    postcodes = con.execute(
        """
        SELECT DISTINCT postcode FROM read_csv_auto(
            'raw_downloads/companies_pre_filtered.csv'
        ) WHERE postcode IS NOT NULL AND postcode != ''
        """
    ).fetchall()
    with open("raw_downloads/unique_postcodes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["postcode"])
        w.writerows(postcodes)
    print(f"Wrote {len(postcodes)} unique postcodes")


def main():
    download_and_unzip()
    prefilter_and_rename()


if __name__ == "__main__":
    main()
