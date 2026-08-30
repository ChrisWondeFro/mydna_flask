"""Error handlers, registered on the real application.

The previous code declared handlers against a second, orphaned ``Flask``
object created at import time in the views module, so none of them ever ran.
"""

from __future__ import annotations

import logging

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

_FRIENDLY = {
    400: ("That request could not be processed", None),
    404: ("Page not found", None),
    413: (
        "That file is too large",
        "Raw DNA exports are normally 15-25 MB. Set MYDNA_MAX_UPLOAD_BYTES if you "
        "genuinely need a higher limit.",
    ),
    500: ("Something went wrong", None),
}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        title, hint = _FRIENDLY.get(error.code or 500, (error.name, None))
        return (
            render_template(
                "error.html",
                title=title,
                message=error.description,
                hint=hint,
            ),
            error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        # Log the type and traceback but never the payload: an exception raised
        # mid-parse can otherwise carry genomic data into the log.
        logger.exception("Unhandled %s", type(error).__name__)
        return (
            render_template(
                "error.html",
                title="Something went wrong",
                message="An unexpected error occurred while generating your report.",
                hint="Nothing was saved. You can safely try again.",
            ),
            500,
        )
