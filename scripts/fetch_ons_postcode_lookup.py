"""
Looks up local authority district and region for every unique postcode found
in the pre-filtered Companies House extract, via the official ONS Postcode
Directory (Live) ArcGIS Feature Service:
https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Online_ONS_Postcode_Directory_Live/FeatureServer/1

No API key required. Queried in batches (the service caps IN-list length),
with a small retry loop for transient failures.

Reads:  raw_downloads/unique_postcodes.csv
Writes: raw_downloads/postcode_lookup.csv   (postcode, lad_code, region_code)
        raw_downloads/postcode_unmatched.csv (postcodes with no match)
"""
import csv
import time

import requests

URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Online_ONS_Postcode_Directory_Live/FeatureServer/1/query"
)

BATCH_SIZE = 800


def read_postcodes(path):
    with open(path) as f:
        reader = csv.DictReader(f)
        return [row["postcode"] for row in reader if row["postcode"]]


def query_batch(postcodes):
    in_list = ",".join("'" + pc.replace("'", "''") + "'" for pc in postcodes)
    where = f"PCDS IN ({in_list})"
    resp = requests.post(
        URL,
        data={
            "where": where,
            "outFields": "PCDS,LAD25CD,RGN25CD",
            "returnGeometry": "false",
            "f": "json",
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return [f["attributes"] for f in data.get("features", [])]


def main():
    postcodes = read_postcodes("raw_downloads/unique_postcodes.csv")
    print(f"Looking up {len(postcodes)} unique postcodes in batches of {BATCH_SIZE}...")

    out_rows = []
    found = set()
    for i in range(0, len(postcodes), BATCH_SIZE):
        batch = postcodes[i : i + BATCH_SIZE]
        attempts = 0
        while True:
            try:
                results = query_batch(batch)
                break
            except Exception as e:
                attempts += 1
                if attempts > 3:
                    print(f"  batch {i}: failed after retries: {e}")
                    results = []
                    break
                time.sleep(2)
        for r in results:
            out_rows.append(
                {
                    "postcode": r["PCDS"],
                    "lad_code": r["LAD25CD"],
                    "region_code": r["RGN25CD"],
                }
            )
            found.add(r["PCDS"])
        if (i // BATCH_SIZE) % 10 == 0:
            print(f"  {i + len(batch)}/{len(postcodes)} postcodes queried, {len(out_rows)} matched so far")

    missing = [pc for pc in postcodes if pc not in found]
    print(f"Total matched: {len(out_rows)} / {len(postcodes)}; unmatched: {len(missing)}")

    with open("raw_downloads/postcode_lookup.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["postcode", "lad_code", "region_code"])
        w.writeheader()
        w.writerows(out_rows)

    with open("raw_downloads/postcode_unmatched.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["postcode"])
        for pc in missing:
            w.writerow([pc])


if __name__ == "__main__":
    main()
