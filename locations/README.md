# Locations Directory

This directory contains alternative coordinate data for Polish caves obtained from an independent source.

## Source

The original data was downloaded from the official Polish Geological Institute database:
- **URL**: https://dm.pgi.gov.pl/
- **Original file**: `cbdg_srodowisko_jaskinie_2025_11_20.zip`
- **Download date**: 2025-11-20

## Contents

### Original Files
- **`cbdg_srodowisko_jaskinie_2025_11_20.zip`** - Original ZIP archive downloaded from PGI
- **`cbdg_srodowisko_jaskinie_2025_11_20/`** - Extracted shapefile data containing:
  - `.shp` - Geometry (point locations)
  - `.dbf` - Attribute data (cave information)
  - `.prj` - Coordinate system definition
  - `.shp.xml` - Metadata
  - Other supporting files (.sbn, .sbx, .shx, .CPG)

### Processed Files
- **`jaskinie_wspolrzedne_wgs84.csv`** - Extracted cave coordinates in WGS84 format with attributes (converted from shapefile using `caves_to_csv.py`)
- **`jaskinie_wgs84.gpx`** - GPS Exchange Format for use in navigation applications (converted from shapefile using `caves_to_gpx.py`)

### Processing Scripts
- **`caves_to_csv.py`** - Converts the shapefile from ZIP to CSV with WGS84 coordinates
- **`caves_to_gpx.py`** - Converts the shapefile from ZIP to GPX format with waypoints

## Data Quality Notes

### Coordinate Comparison
A detailed comparison of cave locations between this dataset and the scraped data from the main directory was performed using the `compare_coordinates.py` script (in the root directory).

**Key Findings:**
- **5,326 caves matched** between both datasets by inventory number
- **82.1% of caves have effectively identical coordinates** (< 1cm difference)
- **Mean distance difference: 0.02 meters** (2 centimeters)
- **Maximum distance difference: 0.18 meters** (18 centimeters)
- **All caves within 1 meter** of each other

**Distance Distribution:**
- 0-1mm: 25.3% of caves (1,347 caves)
- 1-10mm: 56.8% of caves (3,024 caves)
- 10-50mm: 2.2% of caves (116 caves)
- 50-100mm: 7.1% of caves (378 caves)
- 100-150mm: 7.0% of caves (372 caves)
- 150-200mm: 1.7% of caves (89 caves)

This confirms that **the coordinates are essentially identical between both sources**, with differences being only due to floating-point precision and coordinate system conversion. This strongly suggests that the shapefile data from https://dm.pgi.gov.pl/ is automatically generated from the same source database that is scraped by this project.

### Quality Issues
Both data sources (scraped HTML and PGI shapefile) suffer from similar quality problems:

1. **Low coordinate accuracy** - The coordinates appear to be of limited precision
2. **Outdated information** - Both sources have not been updated recently
3. **Better alternatives exist** - For popular caves, coordinates from sources like **mapy.cz** appear to be more accurate and reliable

### Recommendation
When working with cave locations, especially for popular or well-known caves, consider cross-referencing with alternative mapping sources (e.g., mapy.cz, OpenStreetMap) to verify coordinate accuracy before using them for navigation or scientific purposes.

## Processing the Data

To regenerate the CSV and GPX files from the original shapefile:

```bash
# Generate CSV with WGS84 coordinates
poetry run python locations/caves_to_csv.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wspolrzedne_wgs84.csv

# Generate GPX file with waypoints
poetry run python locations/caves_to_gpx.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wgs84.gpx
```

Both scripts assume the source coordinate system is **EPSG:2180 (Poland CS92)** and reproject to **EPSG:4326 (WGS84)**.

## File Structure

```
locations/
├── README.md                                           # This file
├── caves_to_csv.py                                    # Script: Shapefile → CSV converter
├── caves_to_gpx.py                                    # Script: Shapefile → GPX converter
├── cbdg_srodowisko_jaskinie_2025_11_20.zip            # Original ZIP archive
├── cbdg_srodowisko_jaskinie_2025_11_20/               # Extracted shapefile
│   ├── cbdg_srodowisko_jaskinie_2025_11_20.shp        # Geometry
│   ├── cbdg_srodowisko_jaskinie_2025_11_20.dbf        # Attributes
│   ├── cbdg_srodowisko_jaskinie_2025_11_20.prj        # Projection
│   └── ...                                             # Other shapefile components
├── jaskinie_wspolrzedne_wgs84.csv                     # Processed CSV with WGS84 coordinates
└── jaskinie_wgs84.gpx                                 # GPX format for GPS devices
```

## CSV Format

The `jaskinie_wspolrzedne_wgs84.csv` file contains the following columns:
- `NR_INWENT` - Inventory number
- `NAZWA` - Cave name
- `REGION` - Region
- `GMINA` - Municipality
- `WLASCICIEL` - Land owner
- `DLUGOSC` - Length (m)
- `GLEBOKOSC` - Depth (m)
- `PRZEWYZSZE` - Elevation difference (m)
- `DENIWELACJ` - Denivelation (m)
- `OSUWISKOWA` - Landslide flag
- `X_1992`, `Y_1992` - Coordinates in PUWG 1992 coordinate system
- `ID` - Cave ID
- `ROK_AKTUAL` - Year of last update
- `lon`, `lat` - Coordinates in WGS84 (decimal degrees)
