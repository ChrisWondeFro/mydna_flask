"""CSRF protection and response hardening.

Implemented directly rather than via Flask-WTF: the app has exactly one form,
and this keeps the dependency surface of a health-data tool small.
"""

from __future__ import annotations

import secrets

from flask import Flask, Response, abort, request, session

_CSRF_SESSION_KEY = "_csrf_token"
_CSRF_FIELD = "csrf_token"

# Everything is self-hosted, so the policy can be strict. `data:` is needed for
# the chart, which is inlined rather than written to a file. No CDN is
# permitted: a third-party request from a page showing genetic results would
# leak that the page was viewed.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' data:",
        "style-src 'self'",
        "script-src 'self'",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # The report links out to NCBI. Without this, those requests would carry
    # this app's URL as the referrer.
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), interest-cohort=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    # Genetic results should never be retained by an intermediary or the
    # browser's back/forward cache.
    "Cache-Control": "no-store, max-age=0",
}


def csrf_token() -> str:
    """Return the session's CSRF token, creating one if needed."""
    token = session.get(_CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_CSRF_SESSION_KEY] = token
    return token


def validate_csrf() -> None:
    expected = session.get(_CSRF_SESSION_KEY)
    supplied = request.form.get(_CSRF_FIELD, "")
    if not expected or not secrets.compare_digest(str(expected), str(supplied)):
        abort(400, description="Your session expired. Please try the upload again.")


def register_security(app: Flask) -> None:
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _enforce_csrf() -> None:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            validate_csrf()

    @app.after_request
    def _apply_headers(response: Response) -> Response:
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
