# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

Polish-Cave-Data-Scraper is a Python-based data scraping and processing pipeline for collecting comprehensive information about Polish caves from the Central Geological Database of Polish Caves (CBDG). The project consists of three main processing stages implemented as separate Python scripts.

## Package Management

This project uses **uv** for dependency management. All Python commands should be run through uv:

```bash
# Install dependencies
uv sync

# Run any Python script
uv run python <script_name>.py
```

### uv Configuration Notes

- **Python version**: Requires Python >=3.9 (due to geopandas dependency)
- **Package mode**: `[tool.uv] package = false` because this is a script-based project, not a distributable package
- **Lockfile**: `uv.lock` is the source of reproducible dependency versions
- **Dev dependencies**: Uses `[dependency-groups].dev` for `ruff`, `ty`, `pytest`, `pre-commit`, and hook helpers
- **Required domains for sandbox**: When running inside Codex or sandboxed environments, ensure `pypi.org` and `files.pythonhosted.org` are allowlisted

## Data Pipeline Architecture

The pipeline follows a three-stage ETL process that must be executed in sequence:

### 1. Data Fetching (`fetch.py`)
- Scrapes cave data from https://jaskiniepolski.pgi.gov.pl
- Creates a `caves/` directory with subdirectories named by zero-padded cave IDs (6 digits)
- For each cave, downloads:
  - `page.html`: Main cave information page
  - `image_{id}_zoom_10.jpg`: Cave images at zoom level 10
  - `metadata_{id}.json`: Image metadata
- Uses one persistent `requests.Session()` per run with a stable User-Agent, cookies, and rate limiting (`SLEEP_TIME` + `SLEEP_JITTER`)
- Stops early after repeated Incapsula/Imperva anti-bot challenges (`MAX_CONSECUTIVE_CHALLENGES`)
- Cave ID range configurable via `START_ID` and `END_ID` constants (default: 380-13000)
- Implements robust error handling with detailed logging to `logs/cave_scraper_{timestamp}.log`

### 2. Data Parsing (`parse.py`)
- Parses HTML files from the `caves/` directory
- **File priority**: Tries `page_web_archive.html` first, falls back to `page.html` (see [Web Archive Restore](#web-archive-restore) below)
- Extracts structured data from the `tableDetails1` table using BeautifulSoup
- Uses `get_text(' ', strip=True)` to preserve spacing between inline HTML elements (e.g., `<em>`, `<strong>`)
  - This ensures proper spacing in Latin species names and formatted text
  - Affects ~5,400+ caves with inline HTML formatting
- Handles special cases like nested div structures for "Długość [m]" (length) fields
- Links images to their metadata by matching image IDs from HTML onclick attributes
- Outputs to `caves.jsonl` (JSON Lines format)
- Generates parse logs in `logs/parse_{timestamp}.log`

### 3. Data Transformation (`clean.py`)
- Uses PySpark for distributed data processing
- Reads `caves.jsonl` and applies comprehensive transformations:
  - **Column renaming**: Polish field names → English field names (defined in `get_column_mappings()`)
  - **Coordinate conversion**: DMS (degrees, minutes, seconds) → decimal degrees (latitude/longitude)
  - **Numeric conversion**: String measurements → float values (handles comma decimal separators)
  - **Text cleaning**: Removes HTML tags, decodes HTML entities, normalizes whitespace
  - **Nested structure processing**: Transforms image metadata column names within array structures
- Filters out test data (cave IDs: "010569", "011054")
- Outputs:
  - `caves_transformed.jsonl`: Cleaned JSON Lines format
  - `caves_transformed.parquet`: Parquet format for analytics

## Running the Complete Pipeline

Execute scripts in this exact order:

```bash
# 1. Fetch raw data from the website
uv run python fetch.py

# 2. Parse HTML and extract structured data
uv run python parse.py

# 3. Transform and clean the data
uv run python clean.py

# 4. (Optional) Upscale and denoise cave images
uv run python upscale_images.py

# 5. (Optional) Convert to mono TIFF for WMSA
uv run python convert_to_mono.py

# 6. (Optional) Download bibliography data
uv run python download_bibliography.py
```

## Bibliography Download

The `download_bibliography.py` script downloads bibliography records from the CBDG database using the JSON endpoint at `/Search/SearchBibliography`.

### Features
- Fetches all bibliography records via paginated API requests
- Uses `requests.Session` to handle authentication cookies automatically
- Converts raw JSON responses to structured `BibliographyRecord` dataclass objects
- Exports data to `bibliography.jsonl` in JSON Lines format (matching project conventions)
- Automatically trims whitespace from all string fields using `_trim_str()` helper

### Configuration
The script can be customized via variables in the `main()` function:
- `name_filter`: Search term for author, year, or title (default: "" for all records)
- `region_filter`: Cave region identifier (default: "" for all regions)
- `rows_per_page`: Number of records per API request (default: 100)
- `output_file`: Output file path (default: "bibliography.jsonl")

### Implementation Details
- Uses dataclasses for type-safe data structures
- Implements proper type hints with modern Python conventions (e.g., `dict[str, Any]` instead of `Dict[str, Any]`)
- Handles both "cell" array format and named field format from jqGrid responses
- Converts boolean representations ("on", "Yes", "1") to proper Python booleans
- Trims all string fields to avoid whitespace issues (empty strings after trimming become None for optional fields)
- Uses `asdict()` and `json.dump()` to write JSONL format (one JSON object per line)
- Includes verbose logging of download progress and page counts

## Key Implementation Details

### Schema Definition
The PySpark schema in `create_cave_schema()` defines the complete data structure including:
- Main cave properties (35+ fields covering location, morphology, history, documentation)
- Nested image array with metadata structure
- Several commented-out fields in image metadata that were removed because they're empty or redundant

### Data Processing Functions
- `process_numeric_columns()`: Converts Polish comma decimals to float
- `extract_coordinates()`: Regex-based DMS parsing with decimal degree calculation
- `clean_text_fields()`: UDF for HTML tag removal and entity decoding
- `rename_image_metadata_columns()`: Uses PySpark's `transform()` to rename nested struct fields

### Configuration Constants
**fetch.py**:
- `START_ID`, `END_ID`: Cave ID range to scrape
- `SLEEP_TIME`: Base delay between requests (default: 3.0s)
- `SLEEP_JITTER`: Random extra delay added to the base delay (default: 2.0s)
- `MAX_CONSECUTIVE_CHALLENGES`: Stop threshold for repeated Incapsula challenge pages
- `USER_AGENTS`: List of browser user agents; one is selected per persistent session

**parse.py**:
- `CAVES_DIR`: Source directory (default: "caves")
- `OUTPUT_FILE`: Output filename (default: "caves.jsonl")

**clean.py**:
- `SparkConfig`: Spark session configuration
- Numeric/text column lists for processing

## Output Files and Directories

```
caves/                          # Raw scraped data (one subdirectory per cave)
  ├── 000390/
  │   ├── page.html
  │   ├── image_19_zoom_10.jpg
  │   └── metadata_19.json
  ├── 001473/
  │   ├── page.html                    # Original (TPN-blocked)
  │   ├── page_web_archive.html        # Restored from Web Archive (parser uses this)
  │   └── _page_web_archive_files/     # Web Archive assets
  └── ...
caves_upscaled/                 # Upscaled and denoised images (2x scale, denoise level 2)
  ├── 000390/
  │   └── image_19_zoom_10.jpg
  └── ...
caves_mono/                     # Monochrome TIFF images for WMSA (1-bit, Group4 compression)
  ├── 000390/
  │   └── image_19_zoom_10.tif
  └── ...
caves.jsonl                     # Parsed data from HTML
caves_transformed.jsonl         # Cleaned, transformed data
caves_transformed.parquet       # Parquet format for analytics
logs/                           # Timestamped log files
  ├── cave_scraper_{timestamp}.log
  ├── parse_{timestamp}.log
  ├── upscale_{timestamp}.log
  └── convert_mono_{timestamp}.log
waifu2x-ncnn-vulkan-20250915-macos/  # Image upscaling tool
  ├── waifu2x-ncnn-vulkan
  └── models-cunet/
```

## Testing

The project includes pytest as a dev dependency. Run tests with:

```bash
uv run pytest
```

## Code Quality Tools

The project uses modern Python code quality tools to maintain high standards:

### Available Tools

- **ruff**: Fast linting, import sorting, code modernization, and formatting
- **ty**: Fast static type checking
- **pytest**: Test runner
- **pre-commit**: Automated hooks that run before each commit

### Running Code Quality Checks

```bash
# Format code
uv run ruff format .

# Run linter and auto-fix issues
uv run ruff check . --fix

# Check types
uv run ty check

# Run tests
uv run pytest

# Run all checks at once
uv run pre-commit run --all-files
```

### Pre-commit Hooks

Pre-commit hooks are configured to automatically run all quality checks before each commit:

```bash
# Install hooks (one-time setup)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

The pre-commit configuration includes:
- **ruff**: Linting, import sorting, and formatting
- **ty**: Type checking
- **pytest**: Tests
- **Standard hooks**: trailing whitespace, end-of-file fixer, YAML/JSON/TOML validation
- **Note**: Data directories (`caves/`, `caves_upscaled/`, `caves_mono/`, `logs/`) and large generated files are excluded from hooks to allow large commits

### Configuration Details

All tools are configured in `pyproject.toml`:

- **Line length**: 100 characters (consistent across all tools)
- **Target Python version**: 3.9+
- **Excluded directories**: `caves/`, `caves_upscaled/`, `caves_mono/`, `logs/`, `waifu2x-ncnn-vulkan-*`, `*.ipynb`
- **Ruff rules enabled**: pycodestyle, Pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-comprehensions, flake8-simplify
- **ty scope**: Root scripts, `locations/*.py`, and `tests/`

### Code Style Notes

- PySpark convention: Import aliases `F` and `T` for `pyspark.sql.functions` and `pyspark.sql.types` are allowed (marked with `# noqa: N812`)
- Geographic data: Unicode characters (°, ′, ″) in coordinate regex patterns are intentional (marked with `# noqa: RUF001`)
- Modern Python: Using built-in `dict`, `list` for type hints instead of `typing.Dict`, `typing.List`

## Development Dependencies

- **pytest**: Testing framework
- **ruff**: Linting, import sorting, and formatting
- **ty**: Type checking
- **pre-commit**: Git hooks for automated quality checks

## Location Data Processing

The `locations/` directory contains alternative coordinate data from the Polish Geological Institute (https://dm.pgi.gov.pl/). This data is in shapefile format and requires conversion to usable formats.

### Processing Location Data

```bash
# Convert shapefile to CSV with WGS84 coordinates
uv run python locations/caves_to_csv.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wspolrzedne_wgs84.csv

# Convert shapefile to GPX for GPS devices
uv run python locations/caves_to_gpx.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wgs84.gpx
```

### Location Data Scripts

- **`locations/caves_to_csv.py`**: Extracts shapefile from ZIP, reprojects from EPSG:2180 (Poland CS92) to EPSG:4326 (WGS84), exports to CSV
- **`locations/caves_to_gpx.py`**: Same as above but exports to GPX 1.1 format with waypoints

**Important Note**: Coordinate comparison shows that the PGI shapefile data and scraped HTML data contain essentially identical coordinates (mean difference: 2cm, max: 18cm, 82% within 1cm). This confirms both are derived from the same source database. Both sources have accuracy issues - for popular caves, external sources like mapy.cz often have better coordinates.

## Coordinate Comparison Tool

The `compare_coordinates.py` script compares coordinates between scraped data and PGI shapefile data:

```bash
uv run python compare_coordinates.py
```

This generates:
- Console report with statistics and top differences
- `locations/coordinate_comparison.csv` with detailed comparison of all matching caves

The comparison matches caves by inventory number and calculates:
- Geographic distance using Haversine formula
- Coordinate differences in decimal degrees
- Distribution of differences across distance ranges

## Image Upscaling and Denoising

The `upscale_images.py` script uses **waifu2x-ncnn-vulkan** to upscale and denoise cave images (plans, sections, diagrams).

### Setup
1. Download waifu2x-ncnn-vulkan from https://github.com/nihui/waifu2x-ncnn-vulkan/releases
2. Extract the `waifu2x-ncnn-vulkan-20250915-macos.zip` to the project root

### Running
```bash
uv run python upscale_images.py
```

### Configuration
- **Scale**: 2x upscaling
- **Denoise**: Level 2 (moderate denoising)
- **Model**: cunet (optimized for photos and technical drawings)
- **Parallelization**: 4 workers
- **Input**: `caves/*/image_*_zoom_10.jpg` (~7,752 images)
- **Output**: `caves_upscaled/` (same directory structure)
- **Logs**: `logs/upscale_{timestamp}.log`

### Features
- Parallel processing with 4 workers
- Automatically skips already processed images
- Detailed progress logging every 10 images
- 5-minute timeout per image
- Preserves directory structure

## Mono TIFF Conversion

The `convert_to_mono.py` script converts cave images to monochrome (1-bit) TIFF format, optimized for WMSA overlay systems.

### Requirements
- **ImageMagick 7+**: Install with `brew install imagemagick` (macOS) or `apt-get install imagemagick` (Linux)

### Running
```bash
# Default: converts caves_upscaled/ → caves_mono/
uv run python convert_to_mono.py

# Custom directories
uv run python convert_to_mono.py --input caves --output caves_mono
```

### Configuration
- **Conversion method**: Grayscale + Floyd-Steinberg dithering → monochrome
- **Compression**: CCITTFAX4 (Group4) - optimal for 1-bit images
- **Parallelization**: 4 workers (configurable via `--workers`)
- **Input**: `caves_upscaled/*/image_*_zoom_10.jpg`
- **Output**: `caves_mono/` (same directory structure, `.tif` extension)
- **Logs**: `logs/convert_mono_{timestamp}.log`

### Features
- Parallel processing with configurable workers
- Automatically skips already processed images
- 2-minute timeout per image
- Preserves directory structure

## Web Archive Restore

### Background

Since July 30, 2021, the CBDG website blocked access to descriptive data and graphics for 7 Tatra caves (all part of the Ptasia Studnia system) due to reasons independent of the Institute and TPN (Tatra National Park). When `fetch.py` scraped these caves, it downloaded `page.html` files containing only a TPN restriction notice instead of actual cave descriptions.

### Affected Caves

| Cave ID | Name | Inventory Nr | Restored from |
|---------|------|-------------|---------------|
| 001473 | Ptasia Studnia | T.E-11.06 | Web Archive (Wayback Machine) |
| 001474 | Jaskinia nad Dachem | T.E-11.09 | Offline archive (`japo/Tatry/misc/`) |
| 001475 | Jaskinia Lodowa Litworowa | T.E-11.10 | Offline archive (`japo/Tatry/misc/`) |
| 001495 | Jaskinia Mała w Mułowej | T.E-12.01 | Web Archive (Wayback Machine) |
| 001511 | Jaskinia Lejbusiowa | T.E-14.01 | Web Archive (Wayback Machine) |
| 001522 | Jaskinia Turoniowa | T.E-15.03 | Web Archive (Wayback Machine) |
| 001539 | Jaskinia nad Lodową Litworową | T.E-16.01 | Web Archive (Wayback Machine) |

### How the Restore Works

1. **Original `page.html` files are preserved** — they remain untouched with the TPN restriction notice
2. **Restored data is saved as `page_web_archive.html`** in the same cave directory
3. **The parser (`parse.py`) checks for `page_web_archive.html` first** (line 36), falling back to `page.html` only if the archive version doesn't exist
4. After re-running `parse.py` and `clean.py`, the restored descriptions appear in `caves.jsonl` and `caves_transformed.jsonl`

### HTML Format Differences

The `page_web_archive.html` files come from two different sources with different HTML formats:

**Source 1: Wayback Machine saves** (caves 001473, 001495, 001511, 001522, 001539)
- Full CBDG page wrapped in Web Archive scripts (`wombat.js`, `athena.js`, banner CSS)
- Same `tableDetails1` table structure as the original — parser reads them natively
- Accompanying files stored in `_page_web_archive_files/` subdirectory

**Source 2: Offline archive copies** (caves 001474, 001475)
- Simplified HTML format with `<h2>` section headers and `<div class="info/par">` content
- **Not compatible with the parser** — no `tableDetails1` table
- These were **converted** to CBDG format: the original `page.html` was used as a template, and the TPN-blocked fields (`Opis jaskini`, `Opis drogi dojścia do otworu`, `Grafika, zdjęcia`) were replaced with data extracted from the offline archive

### Adding New Restored Caves

If more cave data becomes available (e.g., from Web Archive or other sources):

1. If the source is a **Wayback Machine save** with full CBDG structure — save directly as `caves/{id}/page_web_archive.html`
2. If the source is a **different HTML format** — convert it by:
   - Using the existing `page.html` as a template (preserves all metadata fields)
   - Replacing the TPN-blocked fields with actual content from the source
   - Saving as `page_web_archive.html`
3. Ensure image metadata files (`metadata_{id}.json`) and image files (`image_{id}_zoom_10.jpg`) are present
4. Re-run `uv run python parse.py` then `uv run python clean.py`

## Troubleshooting

### uv Installation Issues

If `uv sync` fails with network errors:
1. Ensure `pypi.org` and `files.pythonhosted.org` are accessible
2. If behind a proxy or in a sandboxed environment, add these domains to allowlist
3. Check Python version compatibility (requires Python 3.9+)

### PySpark/Java Port Binding Issues

When running `clean.py`, PySpark needs to bind to local ports for the Java gateway. If you encounter "Operation not permitted (Bind failed)" errors:

1. **In sandboxed environments (e.g., Codex)**:
   - Add Java to the tools allowlist in the security dashboard
   - Or run the script with `dangerouslyDisableSandbox: true`
   - Or run directly from your terminal outside the sandbox

2. **macOS Firewall**:
   - Check System Preferences → Security & Privacy → Firewall
   - Allow Java/Python network connections if prompted

3. **Alternative**: Run from a regular terminal:
   ```bash
   cd /path/to/Polish-Cave-Data-Scraper
   uv run python clean.py
   ```

### HTML Parsing Issues

The parser uses `get_text(' ', strip=True)` to preserve spacing between inline HTML elements. If you see concatenated text (e.g., scientific names without spaces), verify this setting in `parse.py:60`.

### Scraper Anti-Bot / Incapsula Issues

The CBDG site may return an Incapsula/Imperva anti-bot challenge with HTTP 200 instead of a real cave page. Treat this as a blocked request, not a successful scrape.

Symptoms:
- HTML contains `/_Incapsula_Resource`
- Cookies/headers include values like `visid_incap_*` or `incap_ses_*`
- The page is missing the normal `tableDetails1` table
- Image endpoints may return HTML challenge content instead of JPEG bytes

Current `fetch.py` protections:
- Uses one `requests.Session()` for the whole run to keep cookies and headers stable
- Uses one stable User-Agent per session instead of rotating per request
- Sleeps for `SLEEP_TIME + random jitter` between requests
- Does not save Incapsula challenge HTML as `page.html`
- Does not save image responses unless the response bytes look like a JPEG
- Stops the run after `MAX_CONSECUTIVE_CHALLENGES` consecutive Incapsula pages

For a single-cave smoke test, cave ID `395` (`000395`) is a good known-working example. A successful run should produce:
- `caves/000395/page.html` containing `tableDetails1`
- `caves/000395/metadata_40.json`
- `caves/000395/image_40_zoom_10.jpg` as a real JPEG

When testing from Codex or any sandbox, run single-cave checks in a temporary directory (for example under `/private/tmp`) so blocked responses cannot overwrite the repository's existing `caves/` data. If a single request is blocked, stop testing for a while instead of repeatedly retrying, because repeated challenges may extend the WAF block.
