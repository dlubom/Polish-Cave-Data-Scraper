# Location data

This directory contains a shapefile export of Polish cave locations from the [PIG-PIB download manager](https://dm.pgi.gov.pl/) and scripts for converting it into CSV and GPX. The shapefile and the cave website are distribution channels of the same [CBDG caves subsystem](https://baza.pgi.gov.pl/podsystemy/jaskinie), so this is an alternative representation rather than an independent survey.

## Source and files

The archived download is dated **2025-11-20**, with the original filename `cbdg_srodowisko_jaskinie_2025_11_20.zip`. That date identifies the stored export, not a claim about when each cave was last surveyed or when the live service was last updated.

| File or directory | Purpose |
| --- | --- |
| `cbdg_srodowisko_jaskinie_2025_11_20.zip` | Original shapefile archive |
| `cbdg_srodowisko_jaskinie_2025_11_20/` | Extracted geometry, attributes, projection, and supporting shapefile components |
| `caves_to_csv.py` | Converts the archive to CSV with WGS84 coordinates |
| `caves_to_gpx.py` | Converts the archive to GPX 1.1 waypoints |
| `jaskinie_wspolrzedne_wgs84.csv` | Exported attributes and decimal longitude/latitude |
| `jaskinie_wgs84.gpx` | Exported cave waypoints |
| `coordinate_comparison.csv` | Stored comparison against an earlier scraped dataset |

## Convert the data

From the repository root, install the locked environment and run the required export:

```bash
uv sync --locked

# CSV with WGS84 coordinates
uv run python locations/caves_to_csv.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wspolrzedne_wgs84.csv

# GPX waypoints
uv run python locations/caves_to_gpx.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wgs84.gpx
```

Each script extracts the ZIP to a temporary directory and reads the first shapefile it finds. It uses the shapefile's declared coordinate reference system (CRS), then reprojects to **EPSG:4326 (WGS84)**. If the source has no CRS, it assumes **EPSG:2180 (Poland CS92)**; `--src-crs` changes that fallback. It does not override an existing CRS declaration.

The commands replace the named output files. Use a different `--output` path to inspect a conversion before replacing the stored export.

## Coordinate comparison

The root script [compare_coordinates.py](../compare_coordinates.py) reads `caves_transformed.jsonl` and `locations/jaskinie_wspolrzedne_wgs84.csv`. It joins records on inventory number, calculates Haversine distances, prints statistics, and writes `locations/coordinate_comparison.csv`:

```bash
uv run python compare_coordinates.py
```

The checked-in comparison CSV is a **historical report** with the following values:

| Measure | Stored report |
| --- | ---: |
| Matched rows | 5,326 |
| Difference below 1 cm | 4,371 (82.1%) |
| Mean difference | 0.020 m |
| Maximum difference | 0.179 m |
| Difference at most 1 m | 5,326 (100%) |

These statistics describe that report only. It contains neither input hashes nor a generation timestamp, so they should not be treated as a fresh comparison of the current input files. Regenerate the report when the inputs change, and record which input versions were compared.

Close agreement shows consistency between the compared coordinates. It does not by itself establish absolute positional accuracy, the cause of the differences, the age of individual records, or whether another map has better coordinates. Those claims require separate evidence, such as dated survey measurements.

## CSV fields

The stored `jaskinie_wspolrzedne_wgs84.csv` contains these columns. The converter preserves the source attributes, so the attribute set can differ for another shapefile export.

| Fields | Meaning |
| --- | --- |
| `NR_INWENT`, `NAZWA` | Inventory number and cave name |
| `REGION`, `GMINA` | Region and municipality |
| `WLASCICIEL` | Land owner |
| `DLUGOSC`, `GLEBOKOSC` | Length and depth in metres |
| `PRZEWYZSZE`, `DENIWELACJ` | Elevation difference and vertical range in metres |
| `OSUWISKOWA` | Landslide flag |
| `X_1992`, `Y_1992` | Source coordinates in the Polish 1992 coordinate system |
| `ID`, `ROK_AKTUAL` | Source cave ID and recorded update year |
| `lon`, `lat` | Longitude and latitude in WGS84 decimal degrees |

GPX waypoints use the cave name and include inventory number, region, and municipality in the description.
