from unittest.mock import Mock

import pytest

import download_bibliography
from download_bibliography import BibliographyRecord, _to_bool, _trim_str


def test_trim_str_normalizes_none_and_whitespace() -> None:
    assert _trim_str(None) == ""
    assert _trim_str("  Cave bibliography  ") == "Cave bibliography"
    assert _trim_str(2026) == "2026"


def test_to_bool_normalizes_known_values() -> None:
    assert _to_bool(True) is True
    assert _to_bool(" on ") is True
    assert _to_bool("YES") is True
    assert _to_bool("0") is False
    assert _to_bool("false") is False
    assert _to_bool("unknown") is None


def test_bibliography_record_from_cell_row_trims_values() -> None:
    row = {
        "id": " 42 ",
        "cell": [
            "  Kowalski 2020 ",
            " 7 ",
            "on",
            "  Description ",
            " Tatry ",
            "no",
        ],
    }

    record = BibliographyRecord.from_row(row)

    assert record == BibliographyRecord(
        id="42",
        author_year="Kowalski 2020",
        cave_region_id="7",
        is_archival=True,
        description="Description",
        region="Tatry",
        archival_flag=False,
    )


@pytest.mark.parametrize("total_pages", [0, "0"])
def test_fetch_bibliography_stops_after_empty_result(monkeypatch, total_pages) -> None:
    response = Mock()
    response.json.return_value = {"total": total_pages, "records": 0, "rows": []}
    session = Mock()
    # A second request fails immediately instead of hanging a regression test.
    session.post.side_effect = [response]
    monkeypatch.setattr(download_bibliography.requests, "Session", lambda: session)

    records = download_bibliography.fetch_bibliography(name_filter="no-match", verbose=False)

    assert records == []
    assert session.post.call_count == 1
    assert session.post.call_args.kwargs["data"]["page"] == 1


@pytest.mark.parametrize("total_pages", [1, 2])
def test_fetch_bibliography_stops_after_last_page(monkeypatch, total_pages) -> None:
    responses = []
    for page in range(1, total_pages + 1):
        response = Mock()
        response.json.return_value = {
            "total": total_pages,
            "records": total_pages,
            "rows": [{"id": str(page), "skrot": f"Author {page}"}],
        }
        responses.append(response)
    session = Mock()
    session.post.side_effect = responses
    monkeypatch.setattr(download_bibliography.requests, "Session", lambda: session)

    records = download_bibliography.fetch_bibliography(verbose=False)

    assert [record.id for record in records] == [str(page) for page in range(1, total_pages + 1)]
    assert [call.kwargs["data"]["page"] for call in session.post.call_args_list] == list(
        range(1, total_pages + 1)
    )
