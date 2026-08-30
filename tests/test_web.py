"""Route, error-handling, and hardening tests."""

from __future__ import annotations

import io

from tests.conftest import csrf_token_for


def post_upload(client, data: bytes, filename: str = "AncestryDNA.txt"):
    client.get("/")
    token = csrf_token_for(client)
    return client.post(
        "/analyze",
        data={
            "csrf_token": token,
            "dna_file": (io.BytesIO(data), filename),
        },
        content_type="multipart/form-data",
    )


def test_index_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Look up your DNA variants" in response.data


def test_index_page_warns_when_the_index_is_a_stub(client):
    """A leftover 7-row demo index used to look 'ready' and match nothing."""
    body = client.get("/").data.decode()

    assert "test fixture" in body
    assert "7" in body


def test_healthz_reports_ready(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_analyze_produces_a_report(client, ancestry_file: bytes):
    response = post_upload(client, ancestry_file)

    assert response.status_code == 200
    body = response.data.decode()
    assert "Your variant report" in body
    assert "rs334" in body
    assert "HBB" in body


def test_findings_are_a_three_level_tree(client, ancestry_file: bytes):
    """Classification → type → record, each a disclosure, so a 1,600-row
    Pathogenic group does not dump every record onto the page at once."""
    body = post_upload(client, ancestry_file).data.decode()

    assert 'data-group' in body
    assert 'data-type-block' in body
    assert 'data-variant-details' in body
    assert "Expand classifications" in body
    assert "First" in body and "Last" in body


def test_report_counts_variants_not_categories(client, ancestry_file: bytes):
    """The old template reported the number of significance categories as if
    it were the number of variants analysed."""
    body = post_upload(client, ancestry_file).data.decode()

    # Six real rsIDs in the fixture, three of which are in the sample index.
    assert "6</span>" in body or "6 " in body
    assert "Unique dbSNP identifiers" in body


def test_report_mentions_skipped_internal_ids(client, ancestry_file: bytes):
    body = post_upload(client, ancestry_file).data.decode()

    assert "internal probe" in body


def test_23andme_upload_works(client, twenty_three_file: bytes):
    response = post_upload(client, twenty_three_file, "genome_23andme.txt")

    assert response.status_code == 200
    assert b"Your variant report" in response.data


def test_unsupported_extension_is_rejected_with_a_readable_error(client):
    response = post_upload(client, b"whatever", "payload.exe")

    assert response.status_code == 400
    assert b"Unsupported file type" in response.data


def test_missing_file_is_rejected(client):
    client.get("/")
    token = csrf_token_for(client)
    response = client.post(
        "/analyze",
        data={"csrf_token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_post_without_csrf_token_is_rejected(client, ancestry_file: bytes):
    response = client.post(
        "/analyze",
        data={"dna_file": (io.BytesIO(ancestry_file), "AncestryDNA.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_oversized_upload_is_refused(app, client):
    app.config["MAX_CONTENT_LENGTH"] = 1024

    response = post_upload(client, b"x" * 4096)

    assert response.status_code == 413


def test_pdf_download_after_analysis(client, ancestry_file: bytes):
    post_upload(client, ancestry_file)

    response = client.get("/report.pdf")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_pdf_download_without_a_report_is_a_404(client):
    assert client.get("/report.pdf").status_code == 404


def test_clear_discards_the_report(client, ancestry_file: bytes):
    post_upload(client, ancestry_file)
    token = csrf_token_for(client)

    client.post("/clear", data={"csrf_token": token})

    assert client.get("/report.pdf").status_code == 404


def test_one_session_cannot_read_another_sessions_report(app, ancestry_file: bytes):
    """The original cached the last report filename on a class attribute, so
    any visitor could download the previous visitor's report."""
    first = app.test_client()
    second = app.test_client()

    post_upload(first, ancestry_file)

    assert first.get("/report.pdf").status_code == 200
    assert second.get("/report.pdf").status_code == 404


def test_security_headers_are_applied(client):
    headers = client.get("/").headers

    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "no-store" in headers["Cache-Control"]


def test_no_third_party_resources_are_referenced(client, ancestry_file: bytes):
    """A CDN request from a page showing genetic results would leak that the
    page was viewed."""
    for body in (client.get("/").data, post_upload(client, ancestry_file).data):
        text = body.decode()
        assert "cdn.jsdelivr.net" not in text
        assert "gstatic.com" not in text
        assert "googleapis.com" not in text


def test_unknown_route_renders_the_error_page(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_error_page_reassures_that_nothing_was_saved(client):
    response = client.get("/does-not-exist")

    assert b"Nothing from your file was saved" in response.data
