import os
import re
import json
import logging
import random
import time
import requests
from datetime import datetime
from requests.exceptions import RequestException, Timeout

# Configuration parameters
START_ID = 380  # 380
END_ID = 13000  # 13000
LOG_LEVEL = logging.INFO
SLEEP_TIME = 0.1

# List of common user agents
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
]


def get_random_headers():
    """Generate random headers with a random user agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def setup_logging():
    """Configure logging with both file and console handlers."""
    if not os.path.exists("logs"):
        os.makedirs("logs")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/cave_scraper_{timestamp}.log"

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filename, encoding="utf-8"), logging.StreamHandler()],
    )

    logging.info(f"Starting cave scraper with IDs range: {START_ID}-{END_ID}")


def get_directory_name(cave_id, padding=6):
    """Create directory name with zero padding."""
    return str(cave_id).zfill(padding)


def get_current_timestamp():
    """Get current Unix timestamp in milliseconds."""
    return int(time.time() * 1000)


def fetch_html(url, cave_dir):
    """Fetch HTML content from the given URL."""
    headers = get_random_headers()
    logging.debug(f"Using headers: {headers}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            logging.info(f"Successfully fetched HTML from {url}")
            html_content = response.text
            html_path = os.path.join(cave_dir, "page.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logging.debug(f"Saved HTML to {html_path}")
            return html_content
        else:
            logging.warning(f"Failed to fetch HTML from {url}. Status: {response.status_code}")
            return None
    except Timeout:
        logging.error(f"Timeout while fetching {url}")
        return None
    except RequestException as e:
        logging.error(f"Error while fetching {url}: {str(e)}", exc_info=True)
        return None


def fetch_images(html_content, cave_dir):
    """Fetch images and their metadata using zoom=10."""
    image_id_matches = re.findall(r"showImageInfo\((\d+)\)", html_content)
    if not image_id_matches:
        logging.warning("No image IDs found in HTML content")
        return

    headers = get_random_headers()

    for image_id in image_id_matches:
        logging.info(f"Processing image ID: {image_id}")

        # Fetch image metadata
        metadata_url = "https://jaskiniepolski.pgi.gov.pl/Details/ImageInformation"
        try:
            response = requests.post(metadata_url, data={"id": image_id}, headers=headers, timeout=10)
            if response.status_code == 200:
                metadata = response.json()
                metadata_path = os.path.join(cave_dir, f"metadata_{image_id}.json")
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
                logging.info(f"Saved metadata for image {image_id}")
            else:
                logging.warning(f"Failed to fetch metadata for image {image_id}. Status: {response.status_code}")
                continue
        except Exception as e:
            logging.error(f"Error fetching metadata for image {image_id}: {str(e)}", exc_info=True)
            continue

        # Fetch image at zoom level 10
        zoom = 10
        timestamp = get_current_timestamp()
        image_url = f"https://jaskiniepolski.pgi.gov.pl/Details/RenderImage?id={image_id}&zoom={zoom}&ifGet=false&date={timestamp}"
        try:
            response = requests.get(image_url, headers=headers, timeout=10)
            if response.status_code == 200:
                image_content = response.content
                image_path = os.path.join(cave_dir, f"image_{image_id}_zoom_{zoom}.jpg")
                with open(image_path, "wb") as f:
                    f.write(image_content)
                logging.info(f"Saved image {image_id} with zoom level {zoom}")
            else:
                logging.warning(f"Failed to fetch image {image_id} at zoom {zoom}. Status: {response.status_code}")
        except Timeout:
            logging.error(f"Timeout while fetching image {image_id} at zoom {zoom}")
        except RequestException as e:
            logging.error(f"Error fetching image {image_id} at zoom {zoom}: {str(e)}", exc_info=True)

        time.sleep(SLEEP_TIME)


def process_cave(url, cave_dir, cave_id):
    """Process a single cave entry."""
    logging.info(f"Processing cave ID: {cave_id}")
    html_content = fetch_html(url, cave_dir)

    if html_content:
        logging.info(f"Successfully processed cave ID {cave_id}")
        fetch_images(html_content, cave_dir)
    else:
        # Remove directory if page doesn't exist
        os.rmdir(cave_dir)
        logging.warning(f"Cave ID {cave_id} does not exist - removed directory")


def main():
    """Main function."""
    setup_logging()
    logging.info("Starting main processing loop")

    for cave_id in range(START_ID, END_ID + 1):
        directory_name = get_directory_name(cave_id)
        cave_dir = os.path.join("caves", directory_name)
        os.makedirs(cave_dir, exist_ok=True)
        url = f"https://jaskiniepolski.pgi.gov.pl/Details/Information/{cave_id}"

        try:
            process_cave(url, cave_dir, cave_id)
        except Exception as e:
            logging.error(f"Error processing cave {cave_id}: {str(e)}", exc_info=True)

        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    # Create main directories if they don't exist
    os.makedirs("caves", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    try:
        main()
        logging.info("Script completed successfully")
    except KeyboardInterrupt:
        logging.info("Script terminated by user")
    except Exception as e:
        logging.error(f"Fatal error in main script: {str(e)}", exc_info=True)
