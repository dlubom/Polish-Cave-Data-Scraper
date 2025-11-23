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
results into a single ``pandas.DataFrame``.  The script below demonstrates
this process.  By default it fetches all bibliography entries and writes
them out to a CSV file.  You can adjust the ``name_filter`` and
``region_filter`` variables to narrow the query, and you can change the
``rows_per_page`` variable to control how many records are requested per
request (larger values will reduce the number of round trips but could
increase server load).

Note: the server sets a session cookie on the first request to
``/Search/Bibliography``.  You must perform this initial GET to obtain the
cookie before posting to ``SearchBibliography``; otherwise the server will
respond with a 403 status code.  Using a persistent ``requests.Session``
handles this automatically.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import requests


def _to_bool(value: Any) -> Optional[bool]:
    """Convert various representations of a checkbox into True/False/None."""
    if value in ("on", "Yes", "1", 1, True):
        return True
    if value in ("off", "No", "0", 0, False):
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
        """Create a ``BibliographyRecord`` from a jqGrid row object."""
        # The grid returns a dictionary with a ``cell`` key containing the
        # values in column order.  Alternatively, it may include named fields.
        # For robustness we check both variants.
        if "cell" in row:
            cell = row["cell"]
            # Expected order: skrot, region_id, czyArchiwalny, bibliografia_opis,
            # region, ifMatarchiw
            return cls(
                id=str(row.get("id")),
                author_year=cell[0],
                cave_region_id=cell[1],
                is_archival=_to_bool(cell[2]),
                description=cell[3],
                region=cell[4],
                archival_flag=_to_bool(cell[5]),
            )
        else:
            # Newer jqGrid versions may return named fields directly
            return cls(
                id=str(row.get("id")),
                author_year=row.get("skrot", ""),
                cave_region_id=row.get("region_id"),
                is_archival=_to_bool(row.get("czyArchiwalny")),
                description=row.get("bibliografia_opis", ""),
                region=row.get("region", ""),
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
        calling ``/Search/GetRegions`` (not shown here).
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


def to_dataframe(records: Iterable[BibliographyRecord]) -> pd.DataFrame:
    """Convert a list of ``BibliographyRecord`` objects into a DataFrame."""
    return pd.DataFrame(
        [
            {
                "id": r.id,
                "author_year": r.author_year,
                "cave_region_id": r.cave_region_id,
                "is_archival": r.is_archival,
                "description": r.description,
                "region": r.region,
                "archival_flag": r.archival_flag,
            }
            for r in records
        ]
    )


def save_to_csv(records: Iterable[BibliographyRecord], path: Path) -> None:
    """Save records to a CSV file using UTF-8 encoding."""
    df = to_dataframe(records)
    df.to_csv(path, index=False, encoding="utf-8")


def main() -> None:
    # You can customise these variables to change search criteria or output
    name_filter = ""  # search term for author, year or title
    region_filter = ""  # leave empty to include all regions
    rows_per_page = 100  # number of rows per request; adjust to server limits
    output_file = Path("bibliography.csv")

    records = fetch_bibliography(
        name_filter=name_filter,
        region_filter=region_filter,
        rows_per_page=rows_per_page,
        verbose=True,
    )
    print(f"Downloaded {len(records)} records")
    save_to_csv(records, output_file)
    print(f"Saved to {output_file.resolve()}")


if __name__ == "__main__":
    main()
