# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Polish-Cave-Data-Scraper is a Python-based data scraping and processing pipeline for collecting comprehensive information about Polish caves from the Central Geological Database of Polish Caves (CBDG). The project consists of three main processing stages implemented as separate Python scripts.

## Package Management

This project uses **Poetry** for dependency management. All Python commands should be run through Poetry:

```bash
# Install dependencies
poetry install

# Run any Python script
poetry run python <script_name>.py
```

### Poetry Configuration Notes

- **Python version**: Requires Python ^3.9 (due to geopandas dependency)
- **Package mode**: Set to `false` as this is a script-based project, not a distributable package
- **Dev dependencies**: Uses `[tool.poetry.group.dev.dependencies]` (modern Poetry syntax)
- **Required domains for sandbox**: When running inside Claude Code or sandboxed environments, ensure `pypi.org` and `files.pythonhosted.org` are allowlisted

## Data Pipeline Architecture

The pipeline follows a three-stage ETL process that must be executed in sequence:

### 1. Data Fetching (`fetch.py`)
- Scrapes cave data from https://jaskiniepolski.pgi.gov.pl
- Creates a `caves/` directory with subdirectories named by zero-padded cave IDs (6 digits)
- For each cave, downloads:
  - `page.html`: Main cave information page
  - `image_{id}_zoom_10.jpg`: Cave images at zoom level 10
  - `metadata_{id}.json`: Image metadata
- Uses rotating user agents and implements rate limiting (configurable via `SLEEP_TIME`)
- Cave ID range configurable via `START_ID` and `END_ID` constants (default: 380-13000)
- Implements robust error handling with detailed logging to `logs/cave_scraper_{timestamp}.log`

### 2. Data Parsing (`parse.py`)
- Parses HTML files from the `caves/` directory
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
poetry run python fetch.py

# 2. Parse HTML and extract structured data
poetry run python parse.py

# 3. Transform and clean the data
poetry run python clean.py

# 4. (Optional) Upscale and denoise cave images
poetry run python upscale_images.py
```

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
- `SLEEP_TIME`: Delay between requests (default: 0.1s)
- `USER_AGENTS`: List of browser user agents for rotation

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
  └── ...
caves_upscaled/                 # Upscaled and denoised images (2x scale, denoise level 2)
  ├── 000390/
  │   └── image_19_zoom_10.jpg
  └── ...
caves.jsonl                     # Parsed data from HTML
caves_transformed.jsonl         # Cleaned, transformed data
caves_transformed.parquet       # Parquet format for analytics
logs/                           # Timestamped log files
  ├── cave_scraper_{timestamp}.log
  ├── parse_{timestamp}.log
  └── upscale_{timestamp}.log
waifu2x-ncnn-vulkan-20250915-macos/  # Image upscaling tool
  ├── waifu2x-ncnn-vulkan
  └── models-cunet/
```

## Testing

The project includes pytest as a dev dependency. Run tests with:

```bash
poetry run pytest
```

## Code Quality Tools

The project uses modern Python code quality tools to maintain high standards:

### Available Tools

- **black**: Automatic code formatting (line length: 100)
- **ruff**: Fast linting, import sorting, and code modernization
- **mypy**: Static type checking (gradual typing enabled)
- **pre-commit**: Automated hooks that run before each commit

### Running Code Quality Checks

```bash
# Format code with black
poetry run black .

# Run linter and auto-fix issues
poetry run ruff check --fix .

# Check types with mypy
poetry run mypy .

# Run all checks at once
poetry run black . && poetry run ruff check . && poetry run mypy .
```

### Pre-commit Hooks

Pre-commit hooks are configured to automatically run all quality checks before each commit:

```bash
# Install hooks (one-time setup)
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files

# Note: First run requires internet access to download hook repositories
# In sandboxed environments, you may need to allowlist github.com
```

The pre-commit configuration includes:
- **black**: Code formatting
- **ruff**: Linting and import sorting
- **mypy**: Type checking
- **Standard hooks**: trailing whitespace, end-of-file fixer, YAML/JSON/TOML validation
- **Note**: Data directories (`caves/`, `caves_upscaled/`, `logs/`) are excluded from hooks to allow large commits

### Configuration Details

All tools are configured in `pyproject.toml`:

- **Line length**: 100 characters (consistent across all tools)
- **Target Python version**: 3.9+
- **Excluded directories**: `caves/`, `caves_upscaled/`, `logs/`, `waifu2x-ncnn-vulkan-*`, `*.ipynb`
- **Ruff rules enabled**: pycodestyle, Pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-comprehensions, flake8-simplify
- **Mypy mode**: Gradual typing (doesn't require type hints everywhere)

### Code Style Notes

- PySpark convention: Import aliases `F` and `T` for `pyspark.sql.functions` and `pyspark.sql.types` are allowed (marked with `# noqa: N812`)
- Geographic data: Unicode characters (°, ′, ″) in coordinate regex patterns are intentional (marked with `# noqa: RUF001`)
- Modern Python: Using built-in `dict`, `list` for type hints instead of `typing.Dict`, `typing.List`

## Development Dependencies

- **pytest**: Testing framework
- **black**: Code formatting
- **ruff**: Linting and import sorting
- **mypy**: Type checking
- **pre-commit**: Git hooks for automated quality checks

## Location Data Processing

The `locations/` directory contains alternative coordinate data from the Polish Geological Institute (https://dm.pgi.gov.pl/). This data is in shapefile format and requires conversion to usable formats.

### Processing Location Data

```bash
# Convert shapefile to CSV with WGS84 coordinates
poetry run python locations/caves_to_csv.py \
    --zip locations/cbdg_srodowisko_jaskinie_2025_11_20.zip \
    --output locations/jaskinie_wspolrzedne_wgs84.csv

# Convert shapefile to GPX for GPS devices
poetry run python locations/caves_to_gpx.py \
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
poetry run python compare_coordinates.py
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
poetry run python upscale_images.py
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

## Troubleshooting

### Poetry Installation Issues

If `poetry install` fails with network errors:
1. Ensure `pypi.org` and `files.pythonhosted.org` are accessible
2. If behind a proxy or in a sandboxed environment, add these domains to allowlist
3. Check Python version compatibility (requires Python 3.9+)

### PySpark/Java Port Binding Issues

When running `clean.py`, PySpark needs to bind to local ports for the Java gateway. If you encounter "Operation not permitted (Bind failed)" errors:

1. **In sandboxed environments (e.g., Claude Code)**:
   - Add Java to the tools allowlist in the security dashboard
   - Or run the script with `dangerouslyDisableSandbox: true`
   - Or run directly from your terminal outside the sandbox

2. **macOS Firewall**:
   - Check System Preferences → Security & Privacy → Firewall
   - Allow Java/Python network connections if prompted

3. **Alternative**: Run from a regular terminal:
   ```bash
   cd /path/to/Polish-Cave-Data-Scraper
   poetry run python clean.py
   ```

### HTML Parsing Issues

The parser uses `get_text(' ', strip=True)` to preserve spacing between inline HTML elements. If you see concatenated text (e.g., scientific names without spaces), verify this setting in `parse.py:60`.
