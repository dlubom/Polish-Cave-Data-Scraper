# Polish-Cave-Data-Scraper

## Overview

**Polish-Cave-Data-Scraper** is a robust Python-based tool designed to scrape and collect comprehensive data on Polish caves from the **Central Geological Database of Polish Caves (CBDG)** managed by the **Polish Society for Friends of Earth Sciences (PTPNoZ)**. The scraper gathers standardized information, including geolocation, morphology, environmental data, historical descriptions, and graphic attachments such as plans, sections, and photographs. This dataset serves as a valuable resource for researchers, conservationists, and speleologists interested in the geological and environmental aspects of Polish caves.

## Requirements

- Python 3.9 or higher
- uv (Python package and environment manager)

## Installation

1. First, ensure you have uv installed on your system. For example:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/polish-cave-data-scraper.git
   cd polish-cave-data-scraper
   ```

3. Install project dependencies using uv:

   ```bash
   uv sync
   ```

## Creating a Clean Environment

To ensure a clean environment for the project:

1. Reinstall the locked environment:
   ```bash
   uv sync --reinstall
   ```

## Usage

The scraper consists of three main scripts that should be run in sequence:

1. First, run the data fetching script:
   ```bash
   uv run python fetch.py
   ```
   This script collects raw data from the CBDG database.

2. Then, run the parsing script:
   ```bash
   uv run python parse.py
   ```
   This script processes the collected data into a structured format.

3. Finally, run the cleaning script:
   ```bash
   uv run python clean.py
   ```
   This script transforms and cleans the data using PySpark.

## Bibliography Download

The project includes a separate script for downloading bibliography data from the CBDG database:

```bash
uv run python download_bibliography.py
```

This script fetches all bibliography records from the Polish Geological Institute's cave database using the JSON endpoint. The bibliography includes citations for publications related to Polish caves, organized by region.

Features:
- Downloads complete bibliography dataset via paginated API
- Filters by author, year, title, or cave region
- Saves data to `bibliography.jsonl` in JSON Lines format (matching project conventions)
- Automatically trims whitespace from all string fields
- Handles session cookies and request headers automatically

The script can be customized by editing configuration variables in the `main()` function for specific search criteria.

## Image Upscaling

Cave images (plans, sections, and diagrams) can be upscaled and denoised using waifu2x-ncnn-vulkan:

1. Download waifu2x-ncnn-vulkan from [releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases) and extract to project directory

2. Run the upscaling script:
   ```bash
   uv run python upscale_images.py
   ```

This processes all images in `caves/` directory, applying 2x upscaling and level-2 denoising. Upscaled images are saved to `caves_upscaled/` with the same directory structure.

## Development

### Code Quality Tools

The project uses modern Python code quality tools to maintain high standards:

- **ruff** - Fast linting, import sorting, code modernization, and formatting
- **ty** - Fast static type checking
- **pytest** - Test runner
- **pre-commit** - Git hooks for automated quality checks

### Running Quality Checks

```bash
# Run linter and auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Check types
uv run ty check

# Run tests
uv run pytest

# Run all checks at once
uv run pre-commit run --all-files
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run quality checks before each commit:

```bash
# One-time setup
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

The hooks are local and run through `uv run`, so they use the same locked project environment as normal development commands.

### Running Tests

```bash
uv run pytest
```
