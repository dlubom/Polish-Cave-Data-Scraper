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
- **`jaskinie_wspolrzedne_wgs84.csv`** - Extracted cave coordinates in WGS84 format with attributes (converted from shapefile using Python scripts)
- **`jaskinie_wgs84.gpx`** - GPS Exchange Format for use in navigation applications (converted from CSV)

## Data Quality Notes

### Coordinate Comparison
A comparison of several cave locations between this dataset and the scraped data from the main directory revealed that **the coordinates are identical**. This suggests that the shapefile data from https://dm.pgi.gov.pl/ is automatically generated from the same source database that is scraped by this project.

### Quality Issues
Both data sources (scraped HTML and PGI shapefile) suffer from similar quality problems:

1. **Low coordinate accuracy** - The coordinates appear to be of limited precision
2. **Outdated information** - Both sources have not been updated recently
3. **Better alternatives exist** - For popular caves, coordinates from sources like **mapy.cz** appear to be more accurate and reliable

### Recommendation
When working with cave locations, especially for popular or well-known caves, consider cross-referencing with alternative mapping sources (e.g., mapy.cz, OpenStreetMap) to verify coordinate accuracy before using them for navigation or scientific purposes.

## File Structure

```
locations/
├── README.md                                           # This file
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
