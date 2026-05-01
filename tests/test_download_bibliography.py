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
