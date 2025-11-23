"""
Script to download bibliography records from the Polish Geological Institute's cave database.

The `Jaskinie Polski` website (https://jaskiniepolski.pgi.gov.pl) exposes a JSON
endpoint used by its search page to populate the bibliography grid.  Under the
hood the grid is implemented using the jQuery **jqGrid** plugin.  When you
interact with the search form the browser sends a POST request to the
`/Search/SearchBibliography` endpoint.  The request body contains a handful of
parameters that drive the query:

* ``page`` - the number of the page to return (1-based).
* ``rows`` - the number of rows per page (the grid defaults to 20 but the server
  happily accepts larger values).
* ``sidx`` - the name of the column to sort by.  It can be left empty when
  downloading everything.
* ``sord`` - the sort direction, ``"asc"`` or ``"desc"``.
* ``name`` - the value from the "Autor, rok, tytuł" search field.  An empty
  string returns all entries.
* ``region`` - the identifier of a cave region.  An empty string returns all
  regions.

The response is a JSON document with the following keys:

* ``page`` - the current page number.
* ``records`` - total number of records returned by the query.
* ``total`` - total number of pages available.
* ``rows`` - a list of row objects.  Each object contains a
  unique identifier (``id``) and a dictionary of fields.

Using the information above we can iterate over all pages and accumulate
results into a list of ``BibliographyRecord`` objects.  The script below
demonstrates this process.  By default it fetches all bibliography entries and
writes them out to a JSONL file with one JSON object per line.  You can adjust
the ``name_filter`` and ``region_filter`` variables to narrow the query, and you
can change the ``rows_per_page`` variable to control how many records are
requested per request (larger values will reduce the number of round trips but
could increase server load).

The script also fetches human-readable region names from the ``/Search/GetRegions``
endpoint and adds them to the output as ``region_name`` field. All string fields
are automatically trimmed of leading and trailing whitespace.

Note: the server sets a session cookie on the first request to
``/Search/Bibliography``.  You must perform this initial GET to obtain the
cookie before posting to ``SearchBibliography``; otherwise the server will
respond with a 403 status code.  Using a persistent ``requests.Session``
handles this automatically.
"""

from collections.abc import Iterable
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Optional

import requests


def _trim_str(value: Any) -> str:
    """Trim whitespace from string values, return empty string for None."""
    if value is None:
        return ""
    return str(value).strip()


def _to_bool(value: Any) -> Optional[bool]:
    """Convert various representations of a checkbox into a boolean.

    The jqGrid endpoint returns checkbox values in a few different
    representations depending on configuration. This helper normalizes
    common patterns like "true"/"false", "1"/"0", "on"/"off", "yes"/"no",
    and boolean literals to Python True/False. Unknown values return None.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    # Normalize to lower-case string for easy comparison
    s = str(value).strip().lower()
    if s in {"on", "yes", "1", "true", "t"}:
        return True
    if s in {"off", "no", "0", "false", "f"}:
        return False
    return None


@dataclass
class BibliographyRecord:
    """Represents a single row in the bibliography grid."""

    id: str
    author_year: str
    cave_region_id: Optional[str]
    is_archival: Optional[bool]
    description: str
    region: str
    archival_flag: Optional[bool]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "BibliographyRecord":
        """Create a ``BibliographyRecord`` from a jqGrid row object.

        All string fields are trimmed of leading/trailing whitespace.
        """
        # The grid returns a dictionary with a ``cell`` key containing the
        # values in column order.  Alternatively, it may include named fields.
        # For robustness we check both variants.
        if "cell" in row:
            cell = row["cell"]
            # Expected order: skrot, region_id, czyArchiwalny, bibliografia_opis,
            # region, ifMatarchiw
            return cls(
                id=_trim_str(row.get("id")),
                author_year=_trim_str(cell[0]),
                cave_region_id=_trim_str(cell[1]) or None,
                is_archival=_to_bool(cell[2]),
                description=_trim_str(cell[3]),
                region=_trim_str(cell[4]),
                archival_flag=_to_bool(cell[5]),
            )
        else:
            # Newer jqGrid versions may return named fields directly
            return cls(
                id=_trim_str(row.get("id")),
                author_year=_trim_str(row.get("skrot", "")),
                cave_region_id=_trim_str(row.get("region_id")) or None,
                is_archival=_to_bool(row.get("czyArchiwalny")),
                description=_trim_str(row.get("bibliografia_opis", "")),
                region=_trim_str(row.get("region", "")),
                archival_flag=_to_bool(row.get("ifMatarchiw")),
            )


def fetch_bibliography(
    name_filter: str = "",
    region_filter: str = "",
    rows_per_page: int = 100,
    verbose: bool = True,
) -> list[BibliographyRecord]:
    """Retrieve all bibliography records matching the supplied filters.

    Parameters
    ----------
    name_filter : str, optional
        String to search in the "Autor, rok, tytuł" field.  Pass an empty string
        to retrieve all records.
    region_filter : str, optional
        Identifier of the cave region to filter by.  Pass an empty string to
        include all regions.  Region identifiers can be discovered by
        inspecting the ``Region`` dropdown on the search page or by
        calling ``fetch_regions()``.
    rows_per_page : int, optional
        Number of records to request per page.  The server accepts 10, 20,
        50 or 100 as used by the web application, but larger values are
        generally honoured as well.  A higher number reduces the number of
        requests but increases response payload size.
    verbose : bool, optional
        If true, print progress information while downloading pages.

    Returns
    -------
    List[BibliographyRecord]
        A list of all retrieved bibliography records.
    """

    session = requests.Session()

    # Step 1: bootstrap the session by loading the bibliography page.  This
    # obtains cookies required for subsequent POST requests.
    bootstrap_url = "https://jaskiniepolski.pgi.gov.pl/Search/Bibliography"
    resp = session.get(bootstrap_url)
    resp.raise_for_status()

    # Step 2: iterate over pages from the JSON endpoint.
    search_url = "https://jaskiniepolski.pgi.gov.pl/Search/SearchBibliography"
    records: list[BibliographyRecord] = []
    page = 1
    total_pages: Optional[int] = None

    while True:
        payload = {
            "page": page,
            "rows": rows_per_page,
            "sidx": "",  # leave blank to use the default sort
            "sord": "asc",
            "name": name_filter,
            "region": region_filter,
        }
        # According to the site's JavaScript the endpoint is called via POST.
        resp = session.post(
            search_url, data=payload, headers={"X-Requested-With": "XMLHttpRequest"}
        )
        resp.raise_for_status()
        data = resp.json()

        if total_pages is None:
            # The first response includes the total number of pages and records.
            total_pages = int(data.get("total", 0))
            total_records = int(data.get("records", 0))
            if verbose:
                print(f"Total records reported by server: {total_records}")
                print(f"Total pages to fetch: {total_pages}")

        # Each row is a dictionary with an id and either a ``cell`` list or
        # individual fields.  Convert them into our dataclass.
        for row in data.get("rows", []):
            try:
                record = BibliographyRecord.from_row(row)
                records.append(record)
            except Exception as exc:
                if verbose:
                    print(f"Failed to parse row {row.get('id')}: {exc}")

        if verbose:
            print(f"Fetched page {page} of {total_pages}")

        # Stop when we've processed all pages.
        if total_pages and page >= total_pages:
            break
        page += 1

    return records


def fetch_regions(verbose: bool = False) -> dict[str, str]:
    """Fetch the list of cave regions from the API.

    Returns
    -------
    dict[str, str]
        A mapping from region identifiers to region names.

    Notes
    -----
    The ``/Search/GetRegions`` endpoint returns JSON containing a list of
    objects with ``region_id`` and ``region_nazwa`` keys. We must first
    request ``/Search/Bibliography`` to obtain a session cookie; otherwise
    the server will reject the request.
    """
    session = requests.Session()
    # Bootstrap to get cookies
    session.get("https://jaskiniepolski.pgi.gov.pl/Search/Bibliography").raise_for_status()
    resp = session.get("https://jaskiniepolski.pgi.gov.pl/Search/GetRegions")
    resp.raise_for_status()
    regions_data = resp.json()
    regions = {}
    for item in regions_data:
        rid = _trim_str(item.get("region_id"))
        name = _trim_str(item.get("region_nazwa", ""))
        if rid:
            regions[rid] = name
    if verbose:
        print(f"Fetched {len(regions)} regions")
    return regions


def save_to_jsonl(
    records: Iterable[BibliographyRecord],
    path: Path,
    region_lookup: Optional[dict[str, str]] = None,
) -> None:
    """Save records to a JSONL (JSON Lines) file using UTF-8 encoding.

    Each record is written as a single line of JSON, matching the format
    used by other scripts in this project (caves.jsonl, caves_transformed.jsonl).

    Parameters
    ----------
    records : Iterable[BibliographyRecord]
        The records to save.
    path : Path
        Output file path.
    region_lookup : Optional[dict[str, str]]
        Optional mapping from cave_region_id to human-readable region names.
        If provided, a "region_name" field will be added to each record.
    """
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            record_dict = asdict(record)
            # Add human-readable region name if lookup provided
            if region_lookup is not None and record.cave_region_id:
                record_dict["region_name"] = region_lookup.get(record.cave_region_id, "")
            json.dump(record_dict, f, ensure_ascii=False)
            f.write("\n")


def main() -> None:
    # You can customise these variables to change search criteria or output
    name_filter = ""  # search term for author, year or title
    region_filter = ""  # leave empty to include all regions
    rows_per_page = 100  # number of rows per request; adjust to server limits
    output_file = Path("bibliography.jsonl")

    records = fetch_bibliography(
        name_filter=name_filter,
        region_filter=region_filter,
        rows_per_page=rows_per_page,
        verbose=True,
    )
    print(f"Downloaded {len(records)} records")

    # Fetch region names to add human-readable region information
    try:
        regions = fetch_regions(verbose=True)
    except Exception as e:
        print(f"Warning: Failed to fetch regions: {e}")
        regions = None

    save_to_jsonl(records, output_file, region_lookup=regions)
    print(f"Saved to {output_file.resolve()}")


if __name__ == "__main__":
    main()
