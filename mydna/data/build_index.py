"""Build the local ClinVar index.

Replaces the previous ``create_table.py`` + ``process_upload.py`` pair. That
pipeline loaded the whole 440 MB download into memory, used a pandas API
removed in 2.0, and let its first chunk silently replace the typed table the
other script had just created.

This version streams the gzip straight into chunked parsing, so peak memory
stays flat regardless of the file size.
"""

from __future__ import annotations

import gzip
import io
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO
from urllib.parse import urlparse

import pandas as pd
import requests
from sqlalchemy import Engine, create_engine, delete, func, insert, select

from mydna.data.schema import (
    ASSEMBLY,
    COLUMN_MAP,
    SCHEMA_VERSION,
    SOURCE_COLUMNS,
    SOURCE_URL,
    index_metadata,
    metadata,
    variants,
)

CHUNK_ROWS = 200_000
DOWNLOAD_CHUNK_BYTES = 1024 * 1024


@dataclass
class BuildStats:
    rows_read: int = 0
    rows_kept: int = 0

    @property
    def rows_dropped(self) -> int:
        return self.rows_read - self.rows_kept


class _ProgressReader:
    """Wrap a byte stream to report progress as it is consumed.

    ``gzip`` reads from this incrementally, so the counter reflects real
    download progress rather than a single up-front fetch.
    """

    def __init__(self, stream: IO[bytes], total: int | None, label: str) -> None:
        self._stream = stream
        self._total = total
        self._label = label
        self._read = 0
        self._last_report = 0

    def read(self, size: int = -1) -> bytes:
        block = self._stream.read(size)
        self._read += len(block)
        if self._read - self._last_report >= 8 * 1024 * 1024:
            self._last_report = self._read
            self._report()
        return block

    def _report(self) -> None:
        mib = self._read / (1024 * 1024)
        if self._total:
            pct = 100 * self._read / self._total
            total_mib = self._total / (1024 * 1024)
            msg = f"\r  {self._label}: {mib:,.0f} / {total_mib:,.0f} MiB ({pct:.0f}%)"
        else:
            msg = f"\r  {self._label}: {mib:,.0f} MiB"
        print(msg, end="", file=sys.stderr, flush=True)

    def close(self) -> None:
        print(file=sys.stderr)
        self._stream.close()


def _open_source(source: str | Path) -> tuple[IO[bytes], _ProgressReader | None]:
    """Open a local or remote ``variant_summary`` file as a byte stream."""
    if isinstance(source, Path) or not urlparse(str(source)).scheme:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"No such file: {path}")
        return path.open("rb"), None

    response = requests.get(str(source), stream=True, timeout=60)
    response.raise_for_status()
    length = response.headers.get("Content-Length")
    progress = _ProgressReader(response.raw, int(length) if length else None, "downloading")
    return progress, progress


def _source_last_modified(source: str | Path) -> str | None:
    if isinstance(source, Path) or not urlparse(str(source)).scheme:
        path = Path(source)
        if path.exists():
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
        return None
    try:
        head = requests.head(str(source), timeout=30)
        return head.headers.get("Last-Modified")
    except requests.RequestException:
        return None


def _is_gzip(stream: IO[bytes]) -> bool:
    """True when the stream starts with the gzip magic bytes.

    NCBI ships ``variant_summary.txt.gz``, but a locally decompressed
    ``.txt`` must also work. Peeking is more reliable than the suffix.
    """
    peek = stream.read(2)
    if hasattr(stream, "seek"):
        stream.seek(0)
    return peek == b"\x1f\x8b"


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Filter to GRCh38 rows with a real rsID and normalise column types."""
    chunk = chunk[chunk["Assembly"] == ASSEMBLY]
    chunk = chunk.rename(columns=COLUMN_MAP)
    chunk = chunk.drop(columns=["Assembly"])

    # ClinVar writes -1 for "no dbSNP ID". Those rows can never match a
    # consumer raw-data file, so they are dead weight in the index.
    chunk["rs_dbsnp"] = pd.to_numeric(chunk["rs_dbsnp"], errors="coerce")
    chunk = chunk[chunk["rs_dbsnp"].notna() & (chunk["rs_dbsnp"] > 0)]
    chunk["rs_dbsnp"] = chunk["rs_dbsnp"].astype("int64")

    chunk["number_submitters"] = (
        pd.to_numeric(chunk["number_submitters"], errors="coerce").fillna(0).astype("int64")
    )

    return chunk[[column.name for column in variants.columns]]


def _open_text(stream: IO[bytes]) -> IO[str]:
    if _is_gzip(stream):
        return gzip.open(stream, "rt", encoding="utf-8", errors="replace")
    return io.TextIOWrapper(stream, encoding="utf-8", errors="replace")


def _read_chunks(stream: IO[bytes]) -> Iterator[pd.DataFrame]:
    with _open_text(stream) as text:
        reader = pd.read_csv(
            text,
            sep="\t",
            usecols=lambda name: name.strip() in SOURCE_COLUMNS,
            dtype=str,
            chunksize=CHUNK_ROWS,
            na_filter=False,
        )
        for chunk in reader:
            chunk.columns = [name.strip() for name in chunk.columns]
            yield chunk


def _prepare_sqlite(engine: Engine) -> None:
    """Trade durability for speed during a rebuild.

    The index is derived data: if the build is interrupted it gets rebuilt from
    scratch, so there is nothing to protect with a journal.
    """
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=OFF")
        connection.exec_driver_sql("PRAGMA synchronous=OFF")


def build_index(
    database_url: str,
    source: str | Path = SOURCE_URL,
    *,
    echo: bool = True,
) -> BuildStats:
    """Download (or read) ClinVar and populate the index at ``database_url``."""
    if database_url.startswith("sqlite:///"):
        target = Path(database_url.removeprefix("sqlite:///"))
        target.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url)
    stats = BuildStats()
    last_modified = _source_last_modified(source)

    try:
        # Drop and recreate so a rebuild cannot leave stale rows behind. The old
        # pipeline's per-chunk `if_exists='replace'` made this racy and
        # discarded the declared column types.
        metadata.drop_all(engine)
        metadata.create_all(engine)
        _prepare_sqlite(engine)

        stream, progress = _open_source(source)
        try:
            for chunk in _read_chunks(stream):
                stats.rows_read += len(chunk)
                cleaned = _clean_chunk(chunk)
                stats.rows_kept += len(cleaned)
                if not cleaned.empty:
                    cleaned.to_sql(
                        variants.name,
                        engine,
                        if_exists="append",
                        index=False,
                        method="multi",
                        chunksize=5_000,
                    )
        finally:
            if progress is not None:
                progress.close()
            else:
                stream.close()

        if echo:
            print("  building index on rs_dbsnp...", file=sys.stderr)
        with engine.begin() as connection:
            for index in variants.indexes:
                index.create(connection, checkfirst=True)

            connection.execute(delete(index_metadata))
            connection.execute(
                insert(index_metadata),
                [
                    {"key": "schema_version", "value": SCHEMA_VERSION},
                    {"key": "assembly", "value": ASSEMBLY},
                    {"key": "source", "value": str(source)},
                    {"key": "clinvar_last_modified", "value": last_modified or "unknown"},
                    {
                        "key": "built_at",
                        "value": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    },
                    {"key": "row_count", "value": str(stats.rows_kept)},
                ],
            )
    finally:
        engine.dispose()

    return stats


def read_index_metadata(engine: Engine) -> dict[str, str]:
    """Return the index provenance rows, or an empty dict if unavailable."""
    try:
        with engine.connect() as connection:
            rows = connection.execute(select(index_metadata.c.key, index_metadata.c.value)).all()
        return dict(rows)
    except Exception:
        return {}


def index_row_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(variants)).scalar_one()
