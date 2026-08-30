"""HTTP routes.

The upload is parsed straight from the request stream. At no point does the
uploaded file touch the filesystem.
"""

from __future__ import annotations

import logging
import secrets

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from mydna.core.chart import render_classification_chart
from mydna.core.parser import ParseError, parse_raw_dna
from mydna.core.pdf import render_report_pdf
from mydna.core.report import build_report
from mydna.core.repository import IndexUnavailableError

logger = logging.getLogger(__name__)

bp = Blueprint("dna", __name__)

_REPORT_TOKEN_KEY = "report_token"


def _extensions():
    return current_app.extensions["mydna"]


@bp.get("/")
def index():
    extensions = _extensions()
    metadata = extensions["index_metadata"]
    try:
        index_rows = int(metadata.get("row_count") or 0)
    except ValueError:
        index_rows = 0
    return render_template(
        "index.html",
        index_ready=extensions["repository"].is_ready(),
        index_metadata=metadata,
        index_rows=index_rows,
        max_upload_mb=current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
    )


@bp.post("/analyze")
def analyze():
    extensions = _extensions()

    upload = request.files.get("dna_file")
    if upload is None or not upload.filename:
        raise ParseError("Please choose a raw DNA data file to analyse.")

    # `upload.stream` is read directly; there is no `save()` call anywhere in
    # this application.
    result = parse_raw_dna(upload.stream, upload.filename)
    logger.info(
        "Parsed upload: format=%s rows=%d rsids=%d skipped_internal=%d",
        result.detected_format,
        result.total_rows,
        result.unique_rsids,
        result.skipped_internal,
    )

    records = extensions["repository"].find_variants(result.rsids)
    report = build_report(records, result, extensions["index_metadata"])
    report.chart_data_uri = render_classification_chart(report)

    token = secrets.token_urlsafe(16)
    session[_REPORT_TOKEN_KEY] = token
    extensions["store"].put(token, report)

    return render_template("report.html", report=report)


@bp.get("/report.pdf")
def report_pdf():
    report = _extensions()["store"].get(session.get(_REPORT_TOKEN_KEY))
    if report is None:
        abort(404, description="That report is no longer available. Please run the analysis again.")

    return send_file(
        render_report_pdf(report),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="mydna-variant-report.pdf",
    )


@bp.post("/clear")
def clear():
    extensions = _extensions()
    extensions["store"].discard(session.pop(_REPORT_TOKEN_KEY, None))
    return redirect(url_for("dna.index"))


@bp.get("/healthz")
def healthz():
    ready = _extensions()["repository"].is_ready()
    return {"status": "ok" if ready else "index-missing"}, (200 if ready else 503)


@bp.app_errorhandler(ParseError)
def handle_parse_error(error: ParseError):
    return render_template(
        "error.html", title="We could not read that file", message=str(error)
    ), 400


@bp.app_errorhandler(IndexUnavailableError)
def handle_index_unavailable(error: IndexUnavailableError):
    return (
        render_template(
            "error.html",
            title="The ClinVar index is not ready",
            message=str(error),
            hint="Run `mydna index build` to download and build it.",
        ),
        503,
    )
