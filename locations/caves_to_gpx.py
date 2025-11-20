#!/usr/bin/env python3
"""
Convert CBDG caves shapefile (packed in a ZIP) to a GPX file with waypoints.

- Reads the first .shp file found inside the ZIP.
- Assumes source CRS is Poland CS92 (EPSG:2180) if CRS is missing.
- Reprojects to WGS84 (EPSG:4326).
- Exports each cave as a <wpt> in GPX 1.1.

Waypoint fields:
    <wpt lat="..." lon="...">
        <name>NAZWA</name>
        <desc>NR_INWENT: ... | REGION: ... | GMINA: ...</desc>

Usage:
    poetry run python locations/caves_to_gpx.py \
        --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
        --output locations/jaskinie_wgs84.gpx
"""

import argparse
import math
import sys
from pathlib import Path
import zipfile
import tempfile
from xml.sax.saxutils import escape

import geopandas as gpd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert CBDG caves shapefile (in ZIP) to GPX waypoints."
    )
    parser.add_argument(
        "--zip",
        required=True,
        help="Path to the ZIP file containing the caves shapefile.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output GPX file.",
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
        print(
            f"Warning: multiple .shp files found. Using the first one: {shp_files[0]}",
            file=sys.stderr,
        )
    return shp_files[0]


def build_gpx(gdf) -> str:
    """Build GPX 1.1 content string with <wpt> for each row."""
    gpx_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    gpx_header += '<gpx version="1.1" creator="caves_to_gpx.py" '
    gpx_header += 'xmlns="http://www.topografix.com/GPX/1/1" '
    gpx_header += 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    gpx_header += 'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
    gpx_header += 'http://www.topografix.com/GPX/1/1/gpx.xsd">\n'

    gpx_footer = "</gpx>\n"

    wpts = []

    for _, row in gdf.iterrows():
        lon = row.get("lon", None)
        lat = row.get("lat", None)

        # Skip records without valid coordinates
        if lon is None or lat is None:
            continue
        if (isinstance(lon, float) and math.isnan(lon)) or (
            isinstance(lat, float) and math.isnan(lat)
        ):
            continue

        name = str(row.get("NAZWA", "") or "").strip()
        nr_inv = str(row.get("NR_INWENT", "") or "").strip()
        region = str(row.get("REGION", "") or "").strip()
        gmina = str(row.get("GMINA", "") or "").strip()

        # Build description string from a few attributes
        desc_parts = []
        if nr_inv:
            desc_parts.append(f"NR_INWENT: {nr_inv}")
        if region:
            desc_parts.append(f"REGION: {region}")
        if gmina:
            desc_parts.append(f"GMINA: {gmina}")
        desc = " | ".join(desc_parts)

        # Escape XML special chars
        name_xml = escape(name) if name else ""
        desc_xml = escape(desc) if desc else ""

        wpt_lines = [f'  <wpt lat="{lat:.8f}" lon="{lon:.8f}">']
        if name_xml:
            wpt_lines.append(f"    <name>{name_xml}</name>")
        if desc_xml:
            wpt_lines.append(f"    <desc>{desc_xml}</desc>")
        wpt_lines.append("  </wpt>")

        wpts.append("\n".join(wpt_lines) + "\n")

    gpx_content = gpx_header + "".join(wpts) + gpx_footer
    return gpx_content


def main() -> None:
    args = parse_args()

    zip_path = Path(args.zip)
    out_gpx_path = Path(args.output)

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

        # Compute lon/lat columns
        gdf_wgs84["lon"] = gdf_wgs84.geometry.x
        gdf_wgs84["lat"] = gdf_wgs84.geometry.y

        # Build GPX content and write file
        gpx_content = build_gpx(gdf_wgs84)

        out_gpx_path.parent.mkdir(parents=True, exist_ok=True)
        out_gpx_path.write_text(gpx_content, encoding="utf-8")

        print(
            f"Successfully written GPX with {len(gdf_wgs84)} features: {out_gpx_path}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
