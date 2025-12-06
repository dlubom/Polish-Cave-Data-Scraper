#!/usr/bin/env python3
"""
Apply World File (.tfw) to an image and generate GeoTIFF.

Usage:
    poetry run python apply_worldfile.py image.jpg [worldfile.tfw] [--crs EPSG:2180]

If worldfile is not specified, looks for image.tfw or image.jgw in the same directory.
Output is saved as image_georef.tif in the same directory.
"""

import argparse
from pathlib import Path
import sys
from typing import Optional

from affine import Affine
import numpy as np
from PIL import Image
from rasterio.crs import CRS
from rasterio.io import MemoryFile

# Increase PIL image size limit for large upscaled images
Image.MAX_IMAGE_PIXELS = None


def parse_worldfile(worldfile_path: Path) -> Affine:
    """Parse a world file and return an Affine transformation."""
    with open(worldfile_path) as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]

    if len(lines) < 6:
        raise ValueError(f"World file must have 6 lines, got {len(lines)}")

    # World file format:
    # Line 1: A (pixel size in x direction)
    # Line 2: D (rotation about y axis)
    # Line 3: B (rotation about x axis)
    # Line 4: E (pixel size in y direction, usually negative)
    # Line 5: C (x coordinate of upper-left pixel center)
    # Line 6: F (y coordinate of upper-left pixel center)
    a = float(lines[0])
    d = float(lines[1])
    b = float(lines[2])
    e = float(lines[3])
    c = float(lines[4])
    f_val = float(lines[5])

    return Affine(a, b, c, d, e, f_val)


def find_worldfile(image_path: Path) -> Optional[Path]:
    """Find a world file for the given image."""
    stem = image_path.stem
    parent = image_path.parent

    # Common world file extensions
    extensions = [".tfw", ".jgw", ".pgw", ".wld"]

    for ext in extensions:
        wf = parent / f"{stem}{ext}"
        if wf.exists():
            return wf

    return None


def create_geotiff(
    image_path: Path,
    transform: Affine,
    crs: str,
    output_path: Optional[Path] = None,
) -> Path:
    """Create a GeoTIFF from an image and transformation."""
    # Load image
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)

    height, width, bands = img_array.shape

    # Default output path
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_georef.tif"

    # Create GeoTIFF
    crs_obj = CRS.from_string(crs)

    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            height=height,
            width=width,
            count=bands,
            dtype=img_array.dtype,
            crs=crs_obj.wkt,
            transform=transform,
            compress="lzw",
        ) as dst:
            # Rasterio expects bands first (bands, height, width)
            for i in range(bands):
                dst.write(img_array[:, :, i], i + 1)

        # Write to file
        with open(output_path, "wb") as f:
            f.write(memfile.read())

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply World File to image and create GeoTIFF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Auto-detect world file (looks for image.tfw)
    poetry run python apply_worldfile.py caves_upscaled/000390/image_19_zoom_10.jpg

    # Specify world file explicitly
    poetry run python apply_worldfile.py plan.jpg plan.tfw

    # Specify output CRS
    poetry run python apply_worldfile.py plan.jpg --crs EPSG:4326
        """,
    )
    parser.add_argument("image", type=Path, help="Input image file (jpg, png)")
    parser.add_argument(
        "worldfile",
        type=Path,
        nargs="?",
        help="World file (.tfw, .jgw). Auto-detected if not specified.",
    )
    parser.add_argument(
        "--crs",
        default="EPSG:2180",
        help="Coordinate Reference System (default: EPSG:2180 PL-1992)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output GeoTIFF path (default: {image}_georef.tif)",
    )

    args = parser.parse_args()

    # Validate image
    if not args.image.exists():
        print(f"Error: Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    # Find or validate world file
    if args.worldfile:
        worldfile = args.worldfile
        if not worldfile.exists():
            print(f"Error: World file not found: {worldfile}", file=sys.stderr)
            sys.exit(1)
    else:
        worldfile = find_worldfile(args.image)
        if worldfile is None:
            print(
                f"Error: No world file found for {args.image}. "
                "Create a .tfw file or specify it explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Image:      {args.image}")
    print(f"World file: {worldfile}")
    print(f"CRS:        {args.crs}")

    # Parse world file
    try:
        transform = parse_worldfile(worldfile)
        print(f"Transform:  {transform}")
    except Exception as e:
        print(f"Error parsing world file: {e}", file=sys.stderr)
        sys.exit(1)

    # Create GeoTIFF
    try:
        output = create_geotiff(args.image, transform, args.crs, args.output)
        print(f"Output:     {output}")
        print("Done!")
    except Exception as e:
        print(f"Error creating GeoTIFF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
