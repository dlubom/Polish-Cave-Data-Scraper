#!/usr/bin/env python3
"""
Batch convert cave images to monochrome TIFF for WMSA.

Uses ImageMagick with Floyd-Steinberg dithering and Group4 compression.
This produces 1-bit TIFF files optimized for WMSA overlay systems.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import logging
from pathlib import Path
import subprocess
import sys

# Default configuration
DEFAULT_INPUT_DIR = Path("caves_upscaled")
DEFAULT_OUTPUT_DIR = Path("caves_mono")
MAX_WORKERS = 4

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


def process_single_image(args: tuple[Path, Path]) -> tuple[str, bool, str | None]:
    """
    Convert a single image to monochrome TIFF.

    Args:
        args: Tuple of (image_path, output_dir)

    Returns:
        tuple: (image_path, success, error_message)
    """
    image_path, output_dir = args

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
            return (str(image_path), True, "Already processed")

        # Build ImageMagick command
        # Same as in index.html: grayscale + Floyd-Steinberg dithering + mono + Group4 compression
        cmd = [
            "magick",
            str(image_path),
            "-colorspace",
            "Gray",
            "-dither",
            "FloydSteinberg",
            "-monochrome",
            "-compress",
            "Group4",
            str(output_path),
        ]

        # Run ImageMagick
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout per image
        )

        if result.returncode != 0:
            error_msg = f"Process failed with code {result.returncode}: {result.stderr}"
            return (str(image_path), False, error_msg)

        return (str(image_path), True, None)

    except subprocess.TimeoutExpired:
        error_msg = "Process timeout (>2 minutes)"
        return (str(image_path), False, error_msg)
    except Exception as e:
        error_msg = str(e)
        return (str(image_path), False, error_msg)


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
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Number of parallel workers (default: {MAX_WORKERS})",
    )
    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output
    workers = args.workers

    logger.info("Starting batch mono TIFF conversion")
    logger.info(f"Input: {input_dir}, Output: {output_dir}, Workers: {workers}")

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

    logger.info(f"Processing {total} images with {workers} workers...")

    # Prepare arguments for parallel processing
    task_args = [(img, output_dir) for img in images]

    # Use ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_single_image, arg): arg[0] for arg in task_args}

        # Process results as they complete
        for i, future in enumerate(as_completed(futures), 1):
            image_path, success, error = future.result()

            if success:
                if error == "Already processed":
                    skipped += 1
                else:
                    successful += 1
            else:
                failed += 1
                logger.error(f"Failed: {image_path} - {error}")

            # Progress update
            if i % 10 == 0 or i == total:
                logger.info(
                    f"Progress: {i}/{total} ({i * 100 // total}%) - "
                    f"Success: {successful}, Failed: {failed}, Skipped: {skipped}"
                )

    # Final summary
    logger.info("=" * 60)
    logger.info("Processing complete!")
    logger.info(f"Total images: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Skipped (already processed): {skipped}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
