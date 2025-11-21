#!/usr/bin/env python3
"""
Batch upscale and denoise cave images using waifu2x-ncnn-vulkan.

This script processes all JPG images in the caves/ directory,
upscaling them 2x and applying denoising using waifu2x-ncnn-vulkan.
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys

# Configuration
CAVES_DIR = Path("caves")
OUTPUT_DIR = Path("caves_upscaled")
WAIFU2X_EXECUTABLE = Path("waifu2x-ncnn-vulkan-20250915-macos/waifu2x-ncnn-vulkan")
MODELS_DIR = Path("waifu2x-ncnn-vulkan-20250915-macos/models-cunet")

# Waifu2x parameters
SCALE = 2  # Upscale factor (2x)
DENOISE_LEVEL = 2  # Denoise level (0-3, where 3 is maximum denoising)
MAX_WORKERS = 4  # Number of parallel processes

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"upscale_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def find_all_images():
    """Find all JPG images in the caves directory."""
    images = list(CAVES_DIR.glob("*/image_*_zoom_10.jpg"))
    logger.info(f"Found {len(images)} images to process")
    return images


def process_single_image(image_path):
    """
    Process a single image with waifu2x-ncnn-vulkan.

    Args:
        image_path: Path to the input image

    Returns:
        tuple: (image_path, success, error_message)
    """
    try:
        # Create output directory structure
        cave_id = image_path.parent.name
        output_cave_dir = OUTPUT_DIR / cave_id
        output_cave_dir.mkdir(parents=True, exist_ok=True)

        # Define output path
        output_path = output_cave_dir / image_path.name

        # Skip if already processed
        if output_path.exists():
            logger.info(f"Skipping {image_path} - already processed")
            return (str(image_path), True, "Already processed")

        # Build waifu2x command
        cmd = [
            str(WAIFU2X_EXECUTABLE),
            "-i", str(image_path),
            "-o", str(output_path),
            "-n", str(DENOISE_LEVEL),
            "-s", str(SCALE),
            "-m", str(MODELS_DIR),
            "-f", "jpg"  # Output format
        ]

        # Run waifu2x
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per image
        )

        if result.returncode != 0:
            error_msg = f"Process failed with code {result.returncode}: {result.stderr}"
            logger.error(f"Failed to process {image_path}: {error_msg}")
            return (str(image_path), False, error_msg)

        logger.info(f"Successfully processed {image_path}")
        return (str(image_path), True, None)

    except subprocess.TimeoutExpired:
        error_msg = "Process timeout (>5 minutes)"
        logger.error(f"Timeout processing {image_path}")
        return (str(image_path), False, error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing {image_path}: {error_msg}")
        return (str(image_path), False, error_msg)


def main():
    """Main processing function."""
    logger.info("Starting batch image upscaling")
    logger.info(f"Configuration: scale={SCALE}x, denoise={DENOISE_LEVEL}, workers={MAX_WORKERS}")

    # Check if waifu2x executable exists
    if not WAIFU2X_EXECUTABLE.exists():
        logger.error(f"waifu2x executable not found at {WAIFU2X_EXECUTABLE}")
        return 1

    # Check if models directory exists
    if not MODELS_DIR.exists():
        logger.error(f"Models directory not found at {MODELS_DIR}")
        return 1

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Find all images
    images = find_all_images()
    if not images:
        logger.warning("No images found to process")
        return 0

    # Process images
    total = len(images)
    successful = 0
    failed = 0
    skipped = 0

    logger.info(f"Processing {total} images with {MAX_WORKERS} workers...")

    # Use ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        futures = {executor.submit(process_single_image, img): img for img in images}

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

            # Progress update
            if i % 10 == 0 or i == total:
                logger.info(f"Progress: {i}/{total} ({i*100//total}%) - "
                          f"Success: {successful}, Failed: {failed}, Skipped: {skipped}")

    # Final summary
    logger.info("=" * 60)
    logger.info("Processing complete!")
    logger.info(f"Total images: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Skipped (already processed): {skipped}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
