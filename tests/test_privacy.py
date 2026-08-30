"""Tests for the guarantees in SECURITY.md.

These are the project's central promise, so they are asserted rather than
merely documented.
"""

from __future__ import annotations

import builtins
import io
import logging
from pathlib import Path

import pytest

from tests.conftest import csrf_token_for


def post_upload(client, data: bytes, filename: str = "AncestryDNA.txt"):
    client.get("/")
    return client.post(
        "/analyze",
        data={
            "csrf_token": csrf_token_for(client),
            "dna_file": (io.BytesIO(data), filename),
        },
        content_type="multipart/form-data",
    )


@pytest.fixture
def no_writes(monkeypatch: pytest.MonkeyPatch, index_path: Path):
    """Fail the test if anything opens a file for writing.

    Reads are allowed: the index, templates, and matplotlib's font cache all
    need them. Writes to matplotlib's own cache directory are tolerated because
    they contain no user data.
    """
    real_open = builtins.open
    offenders: list[str] = []

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            path = str(file)
            if "matplotlib" not in path and "fontlist" not in path:
                offenders.append(f"{path} ({mode})")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    yield offenders


def test_upload_is_never_written_to_disk(client, ancestry_file: bytes, no_writes):
    """The original saved every upload to a predictable /tmp path and never
    deleted it."""
    response = post_upload(client, ancestry_file)

    assert response.status_code == 200
    assert no_writes == [], f"Unexpected file writes: {no_writes}"


def test_pdf_generation_writes_nothing_to_disk(client, ancestry_file: bytes, no_writes):
    post_upload(client, ancestry_file)
    no_writes.clear()

    response = client.get("/report.pdf")

    assert response.status_code == 200
    assert no_writes == [], f"Unexpected file writes: {no_writes}"


def test_chart_is_inlined_rather_than_saved(client, ancestry_file: bytes):
    """The chart used to be written to a fixed path inside static/, so
    concurrent users overwrote each other's images."""
    body = post_upload(client, ancestry_file).data.decode()

    assert "data:image/png;base64," in body
    assert "clinical_significance_distribution.png" not in body


def test_no_stray_files_appear_in_tmp(client, ancestry_file: bytes):
    before = set(Path("/tmp").glob("*"))

    post_upload(client, ancestry_file)

    new_files = {path for path in Path("/tmp").glob("*") if path not in before}
    suspicious = [path for path in new_files if "ancestry" in path.name.lower()]
    assert suspicious == [], f"Upload leaked into /tmp: {suspicious}"


def test_genomic_identifiers_are_not_logged(client, ancestry_file: bytes, caplog):
    """The original printed a DataFrame preview of the user's file to stdout."""
    with caplog.at_level(logging.DEBUG):
        post_upload(client, ancestry_file)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "rs334" not in logged
    assert "rs1800562" not in logged


def test_parse_summary_logs_counts_only(client, ancestry_file: bytes, caplog):
    with caplog.at_level(logging.INFO):
        post_upload(client, ancestry_file)

    messages = [record.getMessage() for record in caplog.records]
    assert any("Parsed upload" in message for message in messages)


def test_report_response_is_not_cacheable(client, ancestry_file: bytes):
    response = post_upload(client, ancestry_file)

    assert "no-store" in response.headers["Cache-Control"]
