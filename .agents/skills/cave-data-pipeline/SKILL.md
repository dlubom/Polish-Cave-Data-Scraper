---
name: cave-data-pipeline
description: Modify or validate this repository's HTML parsing and PySpark cave transformation, including schemas, text spacing, coordinates, image metadata, and JSONL/Parquet output. Use for parse.py, clean.py, or a requested dataset refresh; not live fetching or georeferencer UI work.
---

# Cave data pipeline

Read `parse.py`, the relevant functions in `clean.py`, and
[parsing and cleaning](../../../docs/pipeline.md#parsing-and-cleaning). Identify the input snapshot
and whether output regeneration is requested before choosing validation. Keep ordinary tests in
temporary directories; do not rewrite the checked-in dataset to verify a code change.

## Changes and verification

- Preserve six-digit string IDs, archive file priority, inline HTML spacing, nested length
  extraction, and image ID/metadata/path associations. An existing invalid archive is skipped;
  do not assume automatic fallback to `page.html`.
- Keep `create_cave_schema()` and `get_column_mappings()` consistent with added/renamed fields.
  Check comma decimals, null/empty input, DMS λ/φ order, and the two excluded test IDs.
- Protect the existing output on failed parsing/writes. Regression tests should exercise
  actual temporary output files and observable records, including failure cases.
- For Spark changes, use a small local fixture when Java and gateway ports are available,
  write outside tracked data, and stop the Spark session after testing. Report an unavailable
  Spark runtime explicitly; passing Python unit tests does not verify Spark transformations.

## Requested data refresh

Run parse before clean using the intended snapshot. Compare old/new IDs and counts, explain
skips and additions, inspect changed coordinates and missing fields, and verify corresponding
JSONL and Parquet records independent of row order. Treat `locations/coordinate_comparison.csv`
as a historical report unless regenerated from the current inputs. The two transformed output
files are replaced separately, so check both before reporting completion.

Deliver the exact code/data scope and commands run, with any unexplained differences or missing
runtime checks. Keep unrelated raw data and image derivatives out of the change.
