from contextlib import contextmanager
import json
from unittest.mock import patch

import pytest

import parse


@pytest.fixture
def parser_workspace(tmp_path, monkeypatch):
    caves_dir = tmp_path / "caves"
    caves_dir.mkdir()
    output_path = tmp_path / "result.jsonl"
    output_path.write_text('{"previous": true}\n', encoding="utf-8")
    monkeypatch.setattr(parse, "CAVES_DIR", str(caves_dir))
    monkeypatch.setattr(parse, "OUTPUT_FILE", str(output_path))
    monkeypatch.setattr(parse, "setup_logging", lambda: None)
    return caves_dir, output_path


def write_cave(cave_path, name, filename="page.html"):
    cave_path.mkdir(exist_ok=True)
    (cave_path / filename).write_text(
        f'<table id="tableDetails1"><tr><td>Nazwa:</td><td>{name}</td></tr></table>',
        encoding="utf-8",
    )


def test_main_preserves_output_when_input_directory_is_missing(parser_workspace) -> None:
    caves_dir, output_path = parser_workspace
    caves_dir.rmdir()
    previous_data = output_path.read_bytes()

    with pytest.raises(FileNotFoundError):
        parse.main()

    assert output_path.read_bytes() == previous_data
    assert list(output_path.parent.glob(".result.jsonl.*.tmp")) == []


def test_main_preserves_output_and_removes_temporary_file_after_write_error(
    parser_workspace, monkeypatch
) -> None:
    caves_dir, output_path = parser_workspace
    write_cave(caves_dir / "000001", "First cave")
    write_cave(caves_dir / "000002", "Second cave")
    previous_data = output_path.read_bytes()
    named_temporary_file = parse.tempfile.NamedTemporaryFile
    written_records = []

    @contextmanager
    def failing_output(*args, **kwargs):
        with named_temporary_file(*args, **kwargs) as out_f:
            original_write = out_f.write

            def write_then_fail(data):
                if written_records:
                    raise OSError("simulated disk failure")
                written_records.append(data)
                return original_write(data)

            with patch.object(out_f, "write", side_effect=write_then_fail):
                yield out_f

    monkeypatch.setattr(parse.tempfile, "NamedTemporaryFile", failing_output)

    with pytest.raises(OSError, match="simulated disk failure"):
        parse.main()

    assert len(written_records) == 1
    assert output_path.read_bytes() == previous_data
    assert list(output_path.parent.glob(".result.jsonl.*.tmp")) == []


def test_main_replaces_output_after_success_and_skips_invalid_pages(parser_workspace) -> None:
    caves_dir, output_path = parser_workspace
    write_cave(caves_dir / "000002", "Second cave")
    write_cave(caves_dir / "000001", "Jaskinia Żółta")
    invalid_cave = caves_dir / "000003"
    invalid_cave.mkdir()
    (invalid_cave / "page.html").write_text("<p>No cave table</p>", encoding="utf-8")

    parse.main()

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [(record["cave_id"], record["Nazwa"]) for record in records] == [
        ("000001", "Jaskinia Żółta"),
        ("000002", "Second cave"),
    ]
    assert list(output_path.parent.glob(".result.jsonl.*.tmp")) == []


def test_archive_takes_priority_and_preserves_inline_spacing(tmp_path) -> None:
    cave_path = tmp_path / "000001"
    write_cave(cave_path, "Original cave")
    write_cave(cave_path, "Jaskinia <em>Żółta</em> Wielka", filename="page_web_archive.html")

    record = parse.parse_cave_directory(str(cave_path))

    assert record is not None
    assert record["Nazwa"] == "Jaskinia Żółta Wielka"
    assert record["cave_id"] == "000001"
