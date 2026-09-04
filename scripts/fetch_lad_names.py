"""
Downloads the full ONS Local Authority Districts (April 2025) Names and
Codes in the UK (V2) lookup, via the ONS Open Geography Portal ArcGIS
Feature Service:
https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/LAD_APR_2025_UK_NC_v2/FeatureServer

All 361 UK local authority districts are pulled in pages, since the service
caps records per request.

Writes: raw_downloads/lad_lookup.csv  (lad_code, lad_name)
"""
import csv

import requests

URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "LAD_APR_2025_UK_NC_v2/FeatureServer/0/query"
)

PAGE_SIZE = 2000


def main():
    rows = []
    offset = 0
    while True:
        resp = requests.get(
            URL,
            params={
                "where": "1=1",
                "outFields": "LAD25CD,LAD25NM",
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "f": "json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        features = data.get("features", [])
        if not features:
            break
        for feat in features:
            attrs = feat["attributes"]
            rows.append({"lad_code": attrs["LAD25CD"], "lad_name": attrs["LAD25NM"]})
        offset += len(features)
        if not data.get("exceededTransferLimit"):
            break

    print(f"Fetched {len(rows)} local authority districts")

    with open("raw_downloads/lad_lookup.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lad_code", "lad_name"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
