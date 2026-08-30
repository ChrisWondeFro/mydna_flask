"""Short-lived in-memory store for generated reports.

The PDF download needs the report a second time, after the upload request has
finished. Re-uploading the file would be poor UX, so the *derived* report is
held in process memory, briefly and with a hard cap.

It is never written to disk, never shared between sessions, and does not
survive a restart. The raw uploaded file is not kept at all.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from mydna.core.report import Report

DEFAULT_TTL_SECONDS = 30 * 60
DEFAULT_MAX_ENTRIES = 4


@dataclass
class _Entry:
    report: Report
    expires_at: float


class ReportStore:
    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def put(self, token: str, report: Report) -> None:
        with self._lock:
            self._purge_expired()
            if len(self._entries) >= self._max_entries:
                oldest = min(self._entries, key=lambda key: self._entries[key].expires_at)
                del self._entries[oldest]
            self._entries[token] = _Entry(report, time.monotonic() + self._ttl)

    def get(self, token: str | None) -> Report | None:
        if not token:
            return None
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(token)
            return entry.report if entry else None

    def discard(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._entries.pop(token, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _purge_expired(self) -> None:
        now = time.monotonic()
        for key in [key for key, entry in self._entries.items() if entry.expires_at <= now]:
            del self._entries[key]
