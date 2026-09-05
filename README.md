# Polish-Cave-Data-Scraper

Python scripts for collecting and processing Polish cave records, together with a browser tool for georeferencing cave plans.

The data comes from [Jaskinie Polski](https://jaskiniepolski.pgi.gov.pl/), the caves subsystem of the Central Geological Database (CBDG), managed by the Polish Geological Institute – National Research Institute (PIG-PIB). Records include location, morphology, environmental information, exploration history, bibliography, plans, sections, and photographs. PTPNoZ contributes the substantive cave documentation; see the [official CBDG subsystem description](https://baza.pgi.gov.pl/podsystemy/jaskinie) for source responsibilities and context.

## Requirements and installation

- Python 3.9 or higher, as declared in `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python environments and dependencies.
- JDK 17 for the PySpark transformation step (`clean.py`), with `JAVA_HOME` pointing to the JDK. The project pins PySpark 3.5.3; see the [Spark 3.5 installation requirements](https://spark.apache.org/docs/3.5.7/api/python/getting_started/install.html#dependencies).

```bash
git clone https://github.com/dlubom/Polish-Cave-Data-Scraper.git
cd Polish-Cave-Data-Scraper
uv sync --locked
```

This is a script-based project, not an installable Python package. `uv.lock` defines the reproducible dependency versions, including development tools. Run the commands below from the repository root. To reinstall the locked environment, use `uv sync --locked --reinstall`.

## Data pipeline

| Stage | Command | Input | Output |
| --- | --- | --- | --- |
| Fetch | `uv run python fetch.py` | CBDG website | `caves/{six-digit-id}/page.html`, image JPEGs, and image metadata JSON |
| Parse | `uv run python parse.py` | Local `caves/` directories | `caves.jsonl` with Polish field names and linked image metadata |
| Transform | `uv run python clean.py` | `caves.jsonl` | `caves_transformed.jsonl` and `caves_transformed.parquet` |

Run these stages in order when collecting a new dataset. If the raw cave files are already available, begin with parsing. The scripts write to these paths in the working directory and can replace existing data, so use a separate working directory for experiments. Fetch and parse logs are written under `logs/`.

### Fetch configuration and blocked requests

`fetch.py` is configured through constants at the top of the script; it has no command-line flags for selecting cave IDs. The defaults cover IDs 380–13000, inclusive. Set `START_ID` and `END_ID` to the intended range before a live run.

The scraper keeps one HTTP session and one User-Agent per run. `SLEEP_TIME` (3 seconds) and `SLEEP_JITTER` (up to 2 additional seconds) control its delays. It rejects recognized Incapsula/Imperva challenge pages, checks the JPEG signature before saving image responses, and stops after `MAX_CONSECUTIVE_CHALLENGES` (3) consecutive cave-page challenges.

An HTTP 200 response can still be a challenge page. Use a temporary directory for a live smoke test, and pause live testing if the server blocks the request. A completed run does not guarantee complete coverage; inspect its logs for skipped or failed records.

### Parsing and restored descriptions

`parse.py` reads the `tableDetails1` HTML table, preserves spaces around inline formatting, and associates images with their local metadata files. Its input and output paths are configured by `CAVES_DIR` and `OUTPUT_FILE`.

For each cave, the parser uses `page_web_archive.html` when that file exists; otherwise it uses `page.html`. Some descriptions were restored from archived material while preserving the original downloaded page. Restored HTML must retain the CBDG table structure. Historical descriptions reflect their source date, rather than a current confirmation of the cave's condition.

### Transformation

`clean.py` uses PySpark to rename fields into English, convert DMS coordinates into decimal latitude and longitude, normalize numeric values with Polish decimal commas, clean text, and rename nested image metadata fields. It excludes the two test IDs `010569` and `011054`.

Spark settings can be supplied through `SparkConfig` in `clean.py`. Spark also needs permission to open local ports for its Java processes. If startup fails, check the Java installation, `JAVA_HOME`, and the environment's local networking permissions.

## Additional tools

### Bibliography

```bash
uv run python download_bibliography.py
```

This downloads paginated bibliography records from `/Search/SearchBibliography` to `bibliography.jsonl`. It trims string fields and adds readable region names when the region lookup succeeds. Edit `name_filter`, `region_filter`, `rows_per_page`, and `output_file` in `main()` to change the request or output. The default requests all bibliography records, separately from the cave pipeline.

### Image upscaling

Download a suitable [waifu2x-ncnn-vulkan release](https://github.com/nihui/waifu2x-ncnn-vulkan/releases), then set `WAIFU2X_EXECUTABLE` and `MODELS_DIR` in `upscale_images.py` to its executable and models directory. The current paths target the `20250915` macOS release.

```bash
uv run python upscale_images.py
```

The defaults process `caves/*/image_*_zoom_10.jpg` with 2× scaling, denoise level 2, the `cunet` model, and four workers. Results go to `caves_upscaled/`, preserving cave directories. Existing output images are skipped.

### Monochrome TIFF conversion

Install ImageMagick 7 or higher so the `magick` command is available, then run:

```bash
# Convert upscaled images into caves_mono/
uv run python convert_to_mono.py

# Or convert the original images with explicit paths and worker count
uv run python convert_to_mono.py --input caves --output caves_mono --workers 4
```

The script produces 1-bit TIFF images using Floyd–Steinberg dithering and Group4 compression, for use with WMSA overlays. Existing TIFF outputs are skipped. Both image tools write progress logs under `logs/`.

### Location exports and coordinate comparison

The `locations/` directory contains a dated PIG-PIB shapefile export and scripts that convert it to WGS84 CSV and GPX waypoints. See [location data and conversion commands](locations/README.md).

```bash
uv run python compare_coordinates.py
```

This compares `caves_transformed.jsonl` with `locations/jaskinie_wspolrzedne_wgs84.csv`, joining on inventory number and calculating Haversine distances. It prints a report and replaces `locations/coordinate_comparison.csv`. Coordinate agreement between these two CBDG representations measures consistency; it does not establish their accuracy against surveyed positions.

### Cave Plan Georeferencer

The static web application in `index.html` lets you calibrate a cave plan using the entrance coordinates, a scale bar, and an optional north arrow. It generates a world file and GDAL commands for producing a GeoTIFF. GDAL is required to run those commands locally; ImageMagick is also needed for the monochrome variant.

Use the [hosted georeferencer](https://dlubom.github.io/Polish-Cave-Data-Scraper/) and follow the [georeferencing guide](GEOREFERENCER.md) (in Polish). The application loads the published cave data and images from this repository's `main` branch and also accepts local plan images.

## Development

The project uses Ruff for linting and formatting, ty for type checking, pytest for tests, and local pre-commit hooks. After `uv sync --locked`, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```

To apply lint and formatting fixes, use `uv run ruff check . --fix` and `uv run ruff format .`.

```bash
# Install the hooks once
uv run pre-commit install

# Run the complete hook set; some hooks apply fixes
uv run pre-commit run --all-files
```

The hooks run through `uv run`. Tool scopes and exclusions are defined in `pyproject.toml` and `.pre-commit-config.yaml` so large data directories are not treated as application source code. Tests do not require running the full scraper or regenerating datasets.

## Working with Codex

Development guidance is maintained in [AGENTS.md](AGENTS.md). See [Codex setup and workflow](docs/codex.md) for the Astra/OpenAI model setup and repository skills.
