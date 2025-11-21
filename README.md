# Polish-Cave-Data-Scraper

## Overview

**Polish-Cave-Data-Scraper** is a robust Python-based tool designed to scrape and collect comprehensive data on Polish caves from the **Central Geological Database of Polish Caves (CBDG)** managed by the **Polish Society for Friends of Earth Sciences (PTPNoZ)**. The scraper gathers standardized information, including geolocation, morphology, environmental data, historical descriptions, and graphic attachments such as plans, sections, and photographs. This dataset serves as a valuable resource for researchers, conservationists, and speleologists interested in the geological and environmental aspects of Polish caves.

## Requirements

- Python 3.9 or higher
- Poetry (Python package manager)

## Installation

1. First, ensure you have Poetry installed on your system. If not, install it using:

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/polish-cave-data-scraper.git
   cd polish-cave-data-scraper
   ```

3. Install project dependencies using Poetry:

   ```bash
   poetry install
   ```

## Creating a Clean Environment

To ensure a clean environment for the project:

1. Remove any existing virtual environment (if present):
   ```bash
   poetry env remove python
   ```

2. Clear Poetry's cache (optional):
   ```bash
   poetry cache clear . --all
   ```

3. Create a new virtual environment and install dependencies:
   ```bash
   poetry install
   ```

## Usage

The scraper consists of two main scripts that should be run in sequence:

1. First, run the data fetching script:
   ```bash
   poetry run python fetch.py
   ```
   This script collects raw data from the CBDG database.

2. Then, run the parsing script:
   ```bash
   poetry run python parse.py
   ```
   This script processes the collected data into a structured format.

3. Finally, run the cleaning script:
   ```bash
   poetry run python clean.py
   ```
   This script transforms and cleans the data using PySpark.

## Image Upscaling

Cave images (plans, sections, and diagrams) can be upscaled and denoised using waifu2x-ncnn-vulkan:

1. Download waifu2x-ncnn-vulkan from [releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases) and extract to project directory

2. Run the upscaling script:
   ```bash
   poetry run python upscale_images.py
   ```

This processes all images in `caves/` directory, applying 2x upscaling and level-2 denoising. Upscaled images are saved to `caves_upscaled/` with the same directory structure.

## Development

### Code Quality Tools

The project uses modern Python code quality tools to maintain high standards:

- **black** - Automatic code formatting (line length: 100)
- **ruff** - Fast linting, import sorting, and code modernization
- **mypy** - Static type checking (gradual typing)
- **pre-commit** - Git hooks for automated quality checks

### Running Quality Checks

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

Install pre-commit hooks to automatically run quality checks before each commit:

```bash
# One-time setup
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files
```

**Note**: First run requires internet access to download hook repositories from GitHub.

### Running Tests

```bash
poetry run pytest
```
