import os
import json
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration
LOG_LEVEL = logging.INFO
LOG_DIR = 'logs'
CAVES_DIR = 'caves'
OUTPUT_FILE = 'caves.jsonl'

def setup_logging():
    """Configure logging with both file and console handlers."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(LOG_DIR, f"parse_{timestamp}.log")

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filename, encoding="utf-8"), logging.StreamHandler()],
    )

    logging.info("Logging setup complete.")

def parse_cave_directory(cave_path):
    data = {}
    # Try to parse page_web_archive.html first
    page_html_path = os.path.join(cave_path, 'page_web_archive.html')
    if not os.path.exists(page_html_path):
        page_html_path = os.path.join(cave_path, 'page.html')
        if not os.path.exists(page_html_path):
            logging.warning(f"Neither 'page_web_archive.html' nor 'page.html' found in {cave_path}")
            return None

    try:
        with open(page_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        logging.error(f"Error reading HTML file in {cave_path}: {e}")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='tableDetails1')
    if not table:
        logging.warning(f"Table with id 'tableDetails1' not found in {page_html_path}")
        return None

    # Extract key information from the table
    for tr in table.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) == 2:
            field_name = tds[0].get_text(strip=True)
            field_value = tds[1].get_text(strip=True)
            # Handle special case for 'Długość [m]' and 'w tym szacowane [m]'
            if field_name == 'Długość [m]w tym szacowane [m]':
                # Extract values from the nested divs
                divs = tds[1].find_all('div')
                if len(divs) >= 2:
                    data['Długość [m]'] = divs[0].get_text(strip=True)
                    data['w tym szacowane [m]'] = divs[1].get_text(strip=True)
                else:
                    data['Długość [m]'] = field_value
            else:
                # Remove colons from the field name
                field_name = field_name.rstrip(':')
                data[field_name] = field_value

    # Add images information
    images = []
    image_links = soup.find_all('a', onclick=re.compile(r'showImageInfo\(\d+\)'))
    for a_tag in image_links:
        onclick_attr = a_tag['onclick']
        match = re.search(r'showImageInfo\((\d+)\)', onclick_attr)
        if match:
            image_id = match.group(1)
            image_data = {}
            metadata_file = os.path.join(cave_path, f'metadata_{image_id}.json')
            image_file = os.path.join(cave_path, f'image_{image_id}_zoom_10.jpg')

            # Load metadata file if it exists
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as mf:
                        metadata = json.load(mf)
                    image_data['metadata'] = metadata
                except Exception as e:
                    logging.error(f"Error reading metadata file {metadata_file}: {e}")
                    image_data['metadata'] = None
            else:
                logging.warning(f"Metadata file {metadata_file} not found")
                image_data['metadata'] = None

            # Add relative path to image if it exists
            if os.path.exists(image_file):
                image_data['image_path'] = os.path.relpath(image_file)
            else:
                logging.warning(f"Image file {image_file} not found")
                image_data['image_path'] = None

            # Description of the image from the link text
            image_description = a_tag.get_text(strip=True)
            image_data['description'] = image_description

            images.append(image_data)
    data['images'] = images

    # Add cave ID (directory name)
    cave_id = os.path.basename(cave_path)
    data['cave_id'] = cave_id

    return data

def main():
    setup_logging()
    logging.info("Starting parsing of caves data.")

    output_path = OUTPUT_FILE
    with open(output_path, 'w', encoding='utf-8') as out_f:
        caves_processed = 0
        caves_skipped = 0
        for cave_dir in sorted(os.listdir(CAVES_DIR)):
            cave_path = os.path.join(CAVES_DIR, cave_dir)
            if os.path.isdir(cave_path):
                logging.info(f"Processing cave {cave_dir}")
                cave_data = parse_cave_directory(cave_path)
                if cave_data:
                    out_f.write(json.dumps(cave_data, ensure_ascii=False) + '\n')
                    caves_processed += 1
                else:
                    logging.warning(f"Skipping cave {cave_dir} due to missing or invalid data.")
                    caves_skipped += 1
        logging.info(f"Processing complete. Caves processed: {caves_processed}, Caves skipped: {caves_skipped}")

if __name__ == '__main__':
    main()
