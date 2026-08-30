"""Parse consumer raw-DNA exports into a list of rsIDs.

Everything here works on an in-memory stream. The uploaded file is never
written to disk, and genotype calls are dropped as soon as the file is parsed:
the report only ever needs the rsIDs.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import IO

import pandas as pd

ALLOWED_EXTENSIONS = frozenset({".txt", ".csv", ".tsv", ".xlsx"})

# A real dbSNP identifier. Anchored, unlike the previous
# `str.replace('rs', '')`, which also mangled any 'rs' occurring mid-string.
RSID_PATTERN = re.compile(r"^rs(\d+)$", re.IGNORECASE)

# AncestryDNA emits internal probe identifiers alongside real rsIDs. These are
# not dbSNP IDs, cannot match ClinVar, and previously crashed the whole upload
# on `.astype(int)`.
INTERNAL_ID_PATTERN = re.compile(r"^i\d+$", re.IGNORECASE)

_RSID_COLUMN_ALIASES = ("rsid", "rs_id", "snp", "snpid", "snp_id", "identifier")

# AncestryDNA's legal preamble talks about "the SNP identifier (rsID where
# possible)". Those words must not be mistaken for a column header.
_MAX_HEADER_COLUMNS = 12


class ParseError(ValueError):
    """The uploaded file could not be understood."""


@dataclass
class ParseResult:
    """Outcome of parsing an upload.

    Holds rsIDs only. No genotypes, no positions, nothing identifying beyond
    the set of variant identifiers needed for the ClinVar lookup.
    """

    rsids: list[int] = field(default_factory=list)
    total_rows: int = 0
    skipped_internal: int = 0
    skipped_unreadable: int = 0
    detected_format: str = "unknown"

    @property
    def unique_rsids(self) -> int:
        return len(self.rsids)


def validate_filename(filename: str) -> str:
    """Check the extension against the allowlist.

    The upload form's ``accept`` attribute is advisory only; browsers do not
    enforce it and a direct POST bypasses it entirely.
    """
    if not filename:
        raise ParseError("No file was selected.")

    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ParseError(
            f"Unsupported file type '{suffix or filename}'. Expected one of: {allowed}"
        )
    return suffix


def _detect_separator(line: str) -> str:
    counts = {"\t": line.count("\t"), ",": line.count(","), ";": line.count(";")}
    best = max(counts, key=lambda key: counts[key])
    return best if counts[best] else r"\s+"


def _normalise_columns(columns: list[str]) -> list[str]:
    return [str(column).strip().lstrip("#").strip().lower().replace(" ", "_") for column in columns]


def _find_rsid_column(columns: list[str]) -> str | None:
    for alias in _RSID_COLUMN_ALIASES:
        if alias in columns:
            return alias
    return None


def _looks_like_header(columns: list[str]) -> bool:
    """True when a tokenised line is a real column header, not comment prose."""
    if not _find_rsid_column(columns):
        return False
    if not (2 <= len(columns) <= _MAX_HEADER_COLUMNS):
        return False
    return all(len(column) <= 24 for column in columns)


def _split_header_and_data(text: str) -> tuple[list[str] | None, str, str]:
    """Locate the header row, which may be inside the comment block.

    AncestryDNA puts its header on the first non-comment line. 23andMe puts it
    on the last *comment* line (``# rsid chromosome position genotype``), so
    simply passing ``comment='#'`` to pandas silently discards it and shifts
    every column by one.
    """
    lines = text.splitlines()
    header: list[str] | None = None
    detected = "unknown"
    data_start = 0
    last_comment_header: list[str] | None = None

    for position, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            body = stripped.lstrip("#").strip()
            if body and "rsid" in body.lower():
                separator = _detect_separator(body)
                candidate = _normalise_columns(re.split(separator, body))
                if _looks_like_header(candidate):
                    last_comment_header = candidate
                    detected = "23andMe"
            continue

        separator = _detect_separator(line)
        candidate = _normalise_columns(re.split(separator, stripped))
        if _looks_like_header(candidate):
            header = candidate
            detected = "AncestryDNA"
            data_start = position + 1
        else:
            header = last_comment_header
            data_start = position
        break

    if header is None:
        header = last_comment_header

    data = "\n".join(
        line for line in lines[data_start:] if line.strip() and not line.lstrip().startswith("#")
    )
    return header, data, detected


def _frame_from_text(text: str) -> tuple[pd.DataFrame, str]:
    header, data, detected = _split_header_and_data(text)
    if not data:
        raise ParseError("The file contains no data rows.")

    separator = _detect_separator(data.splitlines()[0])
    frame = pd.read_csv(
        io.StringIO(data),
        sep=separator,
        header=None,
        names=header,
        dtype=str,
        engine="python",
        na_filter=False,
        on_bad_lines="skip",
    )

    if header is None:
        raise ParseError(
            "Could not find an 'rsid' column. Expected an AncestryDNA or 23andMe raw data export."
        )
    return frame, detected


def _frame_from_excel(stream: IO[bytes]) -> tuple[pd.DataFrame, str]:
    # `comment=` is not a valid read_excel argument; passing it (as the previous
    # implementation did) raises TypeError for every .xlsx upload.
    frame = pd.read_excel(stream, dtype=str)
    frame.columns = _normalise_columns(list(frame.columns))
    return frame, "spreadsheet"


def parse_raw_dna(stream: IO[bytes], filename: str) -> ParseResult:
    """Parse an uploaded raw-DNA export into a de-duplicated list of rsIDs."""
    suffix = validate_filename(filename)

    if suffix == ".xlsx":
        frame, detected = _frame_from_excel(stream)
    else:
        raw = stream.read()
        if not raw:
            raise ParseError("The uploaded file is empty.")
        frame, detected = _frame_from_text(raw.decode("utf-8", errors="replace"))

    column = _find_rsid_column(list(frame.columns))
    if column is None:
        raise ParseError(
            "Could not find an 'rsid' column. Expected an AncestryDNA or 23andMe raw data export."
        )

    # Keep the identifiers and drop everything else immediately. Genotype calls
    # are the sensitive part of the file and we have no use for them.
    identifiers = frame[column].astype(str).str.strip()
    del frame

    total_rows = len(identifiers)
    extracted = identifiers.str.extract(RSID_PATTERN, expand=False)
    valid = extracted.notna()

    rsids = (
        pd.to_numeric(extracted[valid], errors="coerce")
        .dropna()
        .astype("int64")
        .drop_duplicates()
        .tolist()
    )

    internal = int(identifiers[~valid].str.match(INTERNAL_ID_PATTERN).sum())

    result = ParseResult(
        rsids=rsids,
        total_rows=total_rows,
        skipped_internal=internal,
        skipped_unreadable=int((~valid).sum()) - internal,
        detected_format=detected,
    )

    if not result.rsids:
        raise ParseError(
            f"No dbSNP rsIDs were found in this file ({total_rows:,} rows read). "
            "Please upload an unmodified AncestryDNA or 23andMe raw data export."
        )
    return result
