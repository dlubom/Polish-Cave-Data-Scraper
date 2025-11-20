#!/usr/bin/env python3
"""
Convert CBDG caves shapefile (packed in a ZIP) to CSV with WGS84 coordinates.

- Reads the first .shp file found inside the ZIP.
- Assumes source CRS is Poland CS92 (EPSG:2180) if CRS is missing.
- Reprojects to WGS84 (EPSG:4326).
- Adds "lon" and "lat" columns from geometry.
- Exports all attributes + lon/lat to CSV.

Usage:
    poetry run python locations/caves_to_csv.py \
        --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
        --output locations/jaskinie_wspolrzedne_wgs84.csv
"""

import argparse
import sys
from pathlib import Path
import zipfile
import tempfile

import geopandas as gpd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert CBDG caves shapefile (in ZIP) to CSV with WGS84 coordinates."
    )
    parser.add_argument(
        "--zip",
        required=True,
        help="Path to the ZIP file containing the caves shapefile.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output CSV file.",
    )
    parser.add_argument(
        "--src-crs",
        default="EPSG:2180",
        help=(
            "Source CRS to assume if shapefile has no CRS defined. "
            "Default: EPSG:2180 (Poland CS92)."
        ),
    )
    return parser.parse_args()


def find_shapefile(extract_dir: Path) -> Path:
    """Return the first .shp file found under extract_dir, or raise an error."""
    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp files found in extracted directory: {extract_dir}")
    if len(shp_files) > 1:
        # You can change this behavior if you want to handle multiple shapefiles.
        print(
            f"Warning: multiple .shp files found. Using the first one: {shp_files[0]}",
            file=sys.stderr,
        )
    return shp_files[0]


def main() -> None:
    args = parse_args()

    zip_path = Path(args.zip)
    out_csv_path = Path(args.output)

    if not zip_path.is_file():
        print(f"ERROR: ZIP file not found: {zip_path}", file=sys.stderr)
        sys.exit(1)

    # Extract ZIP to temporary directory
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmpdir)

        # Locate shapefile
        shp_path = find_shapefile(tmpdir)
        print(f"Using shapefile: {shp_path}", file=sys.stderr)

        # Read shapefile
        gdf = gpd.read_file(shp_path)

        # Ensure CRS is set
        if gdf.crs is None:
            print(
                f"No CRS found in shapefile. Setting CRS to {args.src_crs}.",
                file=sys.stderr,
            )
            gdf = gdf.set_crs(args.src_crs)
        else:
            print(f"Original CRS: {gdf.crs}", file=sys.stderr)

        # Reproject to WGS84
        gdf_wgs84 = gdf.to_crs(epsg=4326)
        print(f"Reprojected CRS: {gdf_wgs84.crs}", file=sys.stderr)

        # Add lon/lat columns from geometry
        gdf_wgs84["lon"] = gdf_wgs84.geometry.x
        gdf_wgs84["lat"] = gdf_wgs84.geometry.y

        # Drop geometry for a cleaner CSV (optional)
        cols = [c for c in gdf_wgs84.columns if c != "geometry"]
        df_export = gdf_wgs84[cols].copy()

        # Save to CSV
        out_csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_export.to_csv(out_csv_path, index=False, encoding="utf-8")

        print(
            f"Successfully written {len(df_export)} records to CSV: {out_csv_path}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
