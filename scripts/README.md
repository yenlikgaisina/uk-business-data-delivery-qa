---
name: scripts-readme
---
# One-off extraction scripts

These are **not** part of the monthly delivery pipeline (that's
`src/ingest.py` onward, running against the committed
`data/reference/*.csv` files). They're the scripts originally used to build
those `data/reference/*.csv` files from the live Companies House and ONS
sources, kept here for transparency and reproducibility rather than deleted
after use.

Running them again downloads the current Companies House national data
product (~490MB compressed, ~2.8GB uncompressed) and queries the ONS
Postcode Directory API for every postcode found - expect this to take
several minutes and require several GB of free disk.

1. `fetch_companies_house.py` - downloads and unzips the latest Companies
   House Free Company Data Product, then filters it down to a broad
   East-Midlands-area postcode pre-filter with DuckDB.
2. `fetch_ons_postcode_lookup.py` - looks up local authority and region for
   every unique postcode found in step 1, via the ONS Postcode Directory
   (Live) ArcGIS feature service.
3. `fetch_lad_names.py` - downloads the full ONS Local Authority Districts
   names/codes lookup.
4. `scope_to_nottinghamshire.py` - joins the three together and writes the
   final scoped `data/reference/*.csv` files this repository ships with.

In production, step 1 would be replaced by simply receiving next month's
Companies House extract rather than re-scraping it.
