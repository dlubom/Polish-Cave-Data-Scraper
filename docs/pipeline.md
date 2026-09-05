# Pipeline behavior and recovery

Run commands from the repository root with `uv run`. See [README](../README.md) for setup and
commands; this guide records the details that matter when changing or recovering data.

## Fetching

`fetch.py` fetches IDs from `START_ID` through `END_ID`, inclusive (defaults 380–13000). Each
six-digit directory under `caves/` holds `page.html`, `metadata_{image_id}.json`, and
`image_{image_id}_zoom_10.jpg`. Configuration is in Python constants, not command-line flags.

The run uses one `requests.Session` and one chosen User-Agent. `SLEEP_TIME` is 3 seconds plus
up to 2 seconds of `SLEEP_JITTER` at the implemented sleep points; inspect the actual calls before
changing request pacing. `MAX_CONSECUTIVE_CHALLENGES` defaults to 3. Normal cave HTML includes
`tableDetails1`; the challenge detector looks for `_Incapsula_Resource` without that table.
HTTP 200 alone is not proof of valid data. Incapsula script tags can also occur on valid pages
and are removed by `normalize_html` after challenge detection.

The scraper rejects detected challenge HTML and image bodies without a JPEG start marker. These
are basic checks, not a guarantee that every response is complete or valid. An unsuccessful
fetch removes a cave directory only if it is empty. Existing valid responses can be overwritten
by a requested refresh, so keep exploratory live checks in a temporary directory.

ID 395 (`000395`) was a successful historical smoke-test example with image ID 40. Availability
can change. Check for `tableDetails1`, parseable metadata, and an actual decodable JPEG; stop
after the first challenge in a manual smoke check. Do not repeatedly retry or change identities
to work around a block.

`download_bibliography.py` is independent of the cave ETL. It uses a session and paginated POSTs
to `/Search/SearchBibliography`. Edit `main()` for `name_filter`, `region_filter`, `rows_per_page`,
and `output_file`. `BibliographyRecord` accepts jqGrid `cell` arrays and named fields; string
values are trimmed, optional empty strings become `None`, and flags become booleans. Empty
search results must terminate pagination. Verify both empty and multi-page responses with mocks.

## Parsing and cleaning

`parse.py` reads directories in sorted order from `CAVES_DIR` and writes `OUTPUT_FILE` (defaults
`caves/` and `caves.jsonl`). It chooses `page_web_archive.html` when present, otherwise `page.html`.
It returns no record if the selected file cannot be read or lacks `tableDetails1`; it does not
retry the original file when an archive exists but is invalid.

The parser writes to a temporary file beside the output and replaces the previous JSONL only
after the write completes. Missing input or an unexpected write failure preserves the existing
output. Pages that return no record are still skipped, so inspect skip counts after a refresh.

Important extraction details:

- Field values use `get_text(" ", strip=True)` so inline tags do not join words or species names.
- The combined `Długość [m]w tym szacowane [m]` label is split using nested value divs.
- Image links use `showImageInfo(id)` to associate descriptions with metadata and image files.
  Missing assets are represented by nulls. Image paths are relative to the process working directory.
- `cave_id` is the directory name, including leading zeros.

`clean.py` reads `caves.jsonl` using `create_cave_schema()`. Keep the schema and
`get_column_mappings()` together when changing fields. The transformation:

1. Renames Polish fields and nested image metadata to English.
2. Converts comma-decimal measurements to floats, with nulls for empty/invalid numeric values
   under the normal Spark casting behavior.
3. Extracts λ (longitude) and φ (latitude) from DMS strings, normalizing decimal commas.
4. Trims strings, normalizes whitespace, removes HTML tags, and decodes entities.
5. Filters cave IDs `010569` and `011054`.
6. Writes `caves_transformed.jsonl` and `caves_transformed.parquet` as single files via temporary
   Spark output directories. The two output replacements are not a single transaction.

Run parsing before cleaning only when generating a new dataset is in scope. For code tests,
use fixtures and temporary paths. If a full refresh is requested, compare ID sets and record
counts with the previous data, explain new/dropped caves, inspect null/coordinate changes, and
check JSONL/Parquet equivalence independent of row order. Do not use old counts as fixed targets.

PySpark requires a compatible Java installation and local gateway ports. A local bind denial
needs a scoped host permission or execution in an allowed environment; it is not a scraper
failure and cannot be fixed with an HTTP retry.

## Archive restoration

Since 2021-07-30, seven cave entries have had descriptive/graphic fields restricted on the CBDG
site. Their checked-in `page.html` files preserve that notice. Restored descriptions are kept
separately as `page_web_archive.html`; this history is not a claim about current website access.

| Cave ID | Name | Inventory number | Restoration source |
| --- | --- | --- | --- |
| 001473 | Ptasia Studnia | T.E-11.06 | Wayback Machine |
| 001474 | Jaskinia nad Dachem | T.E-11.09 | Offline archive (`japo/Tatry/misc/`) |
| 001475 | Jaskinia Lodowa Litworowa | T.E-11.10 | Offline archive (`japo/Tatry/misc/`) |
| 001495 | Jaskinia Mała w Mułowej | T.E-11.18 | Wayback Machine |
| 001511 | Jaskinia Lejbusiowa | T.E-11.48 | Wayback Machine |
| 001522 | Jaskinia Turoniowa | T.E-11.55 | Wayback Machine |
| 001539 | Jaskinia nad Lodową Litworową | T.E-11.61 | Wayback Machine |

Wayback saves retain the CBDG `tableDetails1` table and can be parsed despite their archive
wrappers. Some have companion `_page_web_archive_files/` assets. The two offline originals use
`h2` headings and `div.info`/`div.par`, so they were converted into the CBDG table structure using
the original page as a metadata template. The offline archive location above is historical and
is not a bundled dependency.

For another restoration, preserve the original page, record the exact source and snapshot date
when available, and replace only the restricted descriptive/graphic fields in a new archive
file. Validate `Opis jaskini`, `Opis drogi dojścia do otworu`, and `Grafika, zdjęcia` against the
source. Keep image IDs consistent across HTML links, `metadata_{id}.json`, and
`image_{id}_zoom_10.jpg`. Do not invent missing descriptions, authors, dates, or coordinates.

Validate a temporary copy with `parse_cave_directory()` before updating project data. Check
archive priority, preserved metadata, text spacing, and asset references. When output regeneration
is part of the requested restoration, run parse then clean and verify the restored records in
both transformed formats. Report missing source material explicitly.
