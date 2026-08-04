#!/usr/bin/env python3
"""
Batch convert cave images to monochrome TIFF for WMSA.

The conversion method is chosen per image from the CBDG graphic type recorded
in each image's ``metadata_{id}.json`` file (field ``typ_grafiki_id`` /
``typ_grafiki_nazwa``):

  - PHOTOGRAPHS (``zdjęcie``, type id 1) are continuous-tone, so they are
    converted with **Floyd-Steinberg dithering** (the only way a photo survives
    a 1-bit reduction at all).
  - MAPS / SKETCHES (``plan``, ``przekrój``, ``plan i przekrój``, ``szkic``,
    ``lokalizacja``) are line art, so they are converted with a plain luminance
    **threshold**. Thresholding keeps lines and text crisp; dithering used to
    amplify faint JPEG halos around lines into scattered black speckle
    ("artifacts").

Both paths use Group4 compression. Images whose graphic type cannot be
determined (metadata missing/unreadable, or an unrecognised type) fall back to
the threshold and are written to a review report so they can be checked by hand.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import subprocess
import sys

# Default configuration
DEFAULT_INPUT_DIR = Path("caves_upscaled")
DEFAULT_OUTPUT_DIR = Path("caves_mono")
DEFAULT_METADATA_DIR = Path("caves")  # where the metadata_{id}.json files live
MAX_WORKERS = 4

# Conversion tuning
DEFAULT_THRESHOLD = 50  # luminance threshold (%) below which a pixel becomes black

# CBDG graphic types (typ_grafiki_id -> typ_grafiki_nazwa), from the dataset:
#   1 zdjęcie          (photograph)      -> dithering
#   2 plan             (plan)            -> threshold
#   3 szkic            (sketch)          -> threshold
#   4 przekrój         (cross-section)   -> threshold
#   5 lokalizacja      (location)        -> threshold
#   6 plan i przekrój  (plan + section)  -> threshold
PHOTO_TYPE_IDS = frozenset({1})  # graphic types converted with dithering
LINEART_TYPE_IDS = frozenset({2, 3, 4, 5, 6})  # graphic types converted with a threshold

# grafika_id embedded in the image filename, e.g. "image_1000_zoom_10.jpg" -> 1000
_GRAFIKA_ID_RE = re.compile(r"image_(\d+)_zoom_10")

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"convert_mono_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def check_imagemagick() -> bool:
    """Check if ImageMagick is installed and accessible."""
    try:
        result = subprocess.run(
            ["magick", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split("\n")[0]
            logger.info(f"Found ImageMagick: {version_line}")
            return True
        return False
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        return False


def find_all_images(input_dir: Path) -> list[Path]:
    """Find all JPG images in the input directory."""
    images = list(input_dir.glob("*/image_*_zoom_10.jpg"))
    logger.info(f"Found {len(images)} images to process in {input_dir}")
    return images


def read_graphic_type(image_path: Path, metadata_dir: Path) -> tuple[int | None, str]:
    """
    Look up the CBDG graphic type for an image from its metadata JSON.

    The image ``caves_upscaled/<cave>/image_<gid>_zoom_10.jpg`` maps to the
    metadata file ``<metadata_dir>/<cave>/metadata_<gid>.json``.

    Returns ``(typ_grafiki_id, label)`` where ``label`` is the human-readable
    ``typ_grafiki_nazwa`` on success, or a short reason string
    ("filename-unparseable", "metadata-missing", "metadata-unreadable") when the
    type could not be determined (in which case the id is ``None``).
    """
    match = _GRAFIKA_ID_RE.search(image_path.name)
    if not match:
        return (None, "filename-unparseable")

    meta_path = metadata_dir / image_path.parent.name / f"metadata_{match.group(1)}.json"
    if not meta_path.exists():
        return (None, "metadata-missing")

    try:
        data = json.loads(meta_path.read_text())
    except (OSError, ValueError):
        return (None, "metadata-unreadable")

    type_id = data.get("typ_grafiki_id")
    label = data.get("typ_grafiki_nazwa") or (f"type-{type_id}" if type_id is not None else "?")
    return (type_id, label)


def process_single_image(
    args: tuple[Path, Path, Path, int, bool],
) -> tuple[str, bool, str | None, list[str], str, str]:
    """
    Convert a single image to monochrome TIFF, choosing the method from metadata.

    Args:
        args: Tuple of (image_path, output_dir, metadata_dir, threshold, force_dither)

    Returns:
        tuple: (image_path, success, error_message, review_flags, type_label, method)
    """
    image_path, output_dir, metadata_dir, threshold, force_dither = args

    # Decide the conversion method from the recorded graphic type. Photographs
    # are dithered; maps/sketches are thresholded. Unknown types fall back to the
    # threshold and are flagged for manual review.
    type_id, type_label = read_graphic_type(image_path, metadata_dir)
    flags: list[str] = []
    if force_dither or type_id in PHOTO_TYPE_IDS:
        use_dither = True
    elif type_id in LINEART_TYPE_IDS:
        use_dither = False
    else:
        # metadata missing/unreadable, or an unrecognised type id
        use_dither = False
        flags.append(f"unknown-type ({type_label}) -> thresholded, please verify")
    method = "dither" if use_dither else "threshold"

    try:
        # Create output directory structure
        cave_id = image_path.parent.name
        output_cave_dir = output_dir / cave_id
        output_cave_dir.mkdir(parents=True, exist_ok=True)

        # Define output path (change extension to .tif)
        output_filename = image_path.stem + ".tif"
        output_path = output_cave_dir / output_filename

        # Skip if already processed
        if output_path.exists():
            return (str(image_path), True, "Already processed", flags, type_label, method)

        # Build ImageMagick command: grayscale -> bilevel -> Group4 compression.
        # Threshold keeps line art crisp; Floyd-Steinberg dithering is used for
        # continuous-tone photographs.
        cmd = ["magick", str(image_path), "-colorspace", "Gray"]
        if use_dither:
            cmd += ["-dither", "FloydSteinberg", "-monochrome"]
        else:
            cmd += ["-threshold", f"{threshold}%"]
        cmd += ["-compress", "Group4", str(output_path)]

        # Run ImageMagick
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout per image
        )

        if result.returncode != 0:
            error_msg = f"Process failed with code {result.returncode}: {result.stderr}"
            return (str(image_path), False, error_msg, flags, type_label, method)

        return (str(image_path), True, None, flags, type_label, method)

    except subprocess.TimeoutExpired:
        return (str(image_path), False, "Process timeout (>2 minutes)", flags, type_label, method)
    except Exception as e:
        return (str(image_path), False, str(e), flags, type_label, method)


def main() -> int:
    """Main processing function."""
    parser = argparse.ArgumentParser(description="Convert cave images to monochrome TIFF for WMSA.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Input directory (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=DEFAULT_METADATA_DIR,
        help=f"Directory with metadata_<id>.json files (default: {DEFAULT_METADATA_DIR})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Number of parallel workers (default: {MAX_WORKERS})",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=(
            "Luminance threshold %% below which a pixel becomes black "
            f"(default: {DEFAULT_THRESHOLD}). Higher = more black."
        ),
    )
    parser.add_argument(
        "--dither",
        action="store_true",
        help="Force Floyd-Steinberg dithering for ALL images, overriding the "
        "per-image choice made from metadata (dithering speckles line art).",
    )
    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output
    metadata_dir = args.metadata_dir
    workers = args.workers
    threshold = args.threshold
    force_dither = args.dither

    logger.info("Starting batch mono TIFF conversion")
    logger.info(f"Input: {input_dir}, Output: {output_dir}, Workers: {workers}")
    logger.info(f"Metadata: {metadata_dir}")
    if force_dither:
        logger.info("Method: Floyd-Steinberg dithering (forced for all images via --dither)")
    else:
        logger.info(
            f"Method: per-image from metadata "
            f"(photographs -> dithering, maps/sketches -> threshold {threshold}%)"
        )

    # Check if ImageMagick is installed
    if not check_imagemagick():
        logger.error(
            "ImageMagick not found. Install it with: brew install imagemagick (macOS) "
            "or apt-get install imagemagick (Linux)"
        )
        return 1

    # Check if input directory exists
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Find all images
    images = find_all_images(input_dir)
    if not images:
        logger.warning("No images found to process")
        return 0

    # Process images
    total = len(images)
    successful = 0
    failed = 0
    skipped = 0
    flagged: list[tuple[str, list[str]]] = []
    # Count how each graphic type was handled: type_label -> {method: count}
    type_methods: dict[str, Counter[str]] = defaultdict(Counter)

    logger.info(f"Processing {total} images with {workers} workers...")

    # Prepare arguments for parallel processing
    task_args = [(img, output_dir, metadata_dir, threshold, force_dither) for img in images]

    # Use ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_single_image, arg): arg[0] for arg in task_args}

        # Process results as they complete
        for i, future in enumerate(as_completed(futures), 1):
            image_path, success, error, flags, type_label, method = future.result()

            type_methods[type_label][method] += 1

            if success:
                if error == "Already processed":
                    skipped += 1
                else:
                    successful += 1
            else:
                failed += 1
                logger.error(f"Failed: {image_path} - {error}")

            if flags:
                flagged.append((image_path, flags))

            # Progress update
            if i % 10 == 0 or i == total:
                logger.info(
                    f"Progress: {i}/{total} ({i * 100 // total}%) - "
                    f"Success: {successful}, Failed: {failed}, Skipped: {skipped}, "
                    f"Flagged: {len(flagged)}"
                )

    # Write the manual-review report: images whose graphic type could not be
    # determined and were thresholded as a fallback.
    review_file = LOG_DIR / f"mono_review_{timestamp}.txt"
    flagged.sort()
    with review_file.open("w") as fh:
        fh.write("# Images flagged for manual review\n")
        fh.write("# The graphic type could not be read from metadata, so these were\n")
        fh.write("# thresholded as a fallback. If any is actually a photograph, re-run\n")
        fh.write("# it with --dither (or fix its metadata_<id>.json).\n\n")
        for image_path, flags in flagged:
            fh.write(f"{image_path}\t{', '.join(flags)}\n")

    # Final summary
    logger.info("=" * 60)
    logger.info("Processing complete!")
    logger.info(f"Total images: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Skipped (already processed): {skipped}")
    logger.info(f"Flagged for manual review: {len(flagged)}")
    logger.info("Graphic type -> conversion method:")
    for type_label in sorted(type_methods):
        breakdown = ", ".join(f"{m}={n}" for m, n in sorted(type_methods[type_label].items()))
        logger.info(f"  {type_label}: {breakdown}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Review report: {review_file}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
