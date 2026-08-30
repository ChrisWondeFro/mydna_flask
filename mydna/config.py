"""Application settings, resolved from the environment."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_INDEX_PATH = Path("data") / "clinvar.sqlite"

# AncestryDNA exports run to roughly 15-25 MB; 23andMe is smaller. 64 MB leaves
# generous headroom while still bounding what an upload can cost us.
DEFAULT_MAX_UPLOAD_BYTES = 64 * 1024 * 1024


def resolve_database_url() -> str:
    """Pick the index backend.

    SQLite unless ``MYDNA_DATABASE_URL`` names something else. Postgres is
    opt-in via that one variable rather than being inferred from a scatter of
    POSTGRES_* settings, so the backend in use is always obvious.
    """
    explicit = os.getenv("MYDNA_DATABASE_URL")
    if explicit:
        return explicit

    index_path = Path(os.getenv("MYDNA_INDEX_PATH", DEFAULT_INDEX_PATH))
    return f"sqlite:///{index_path}"


@dataclass(frozen=True)
class Config:
    """Runtime configuration.

    MyDNA is a local single-user tool, so there is deliberately no auth,
    session, or user-storage configuration here.
    """

    database_url: str = field(default_factory=resolve_database_url)
    secret_key: str = field(
        default_factory=lambda: os.getenv("MYDNA_SECRET_KEY") or secrets.token_hex(32)
    )
    max_upload_bytes: int = field(
        default_factory=lambda: int(os.getenv("MYDNA_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES))
    )
    host: str = field(default_factory=lambda: os.getenv("MYDNA_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("MYDNA_PORT", "8000")))

    @property
    def secret_key_is_ephemeral(self) -> bool:
        """True when no MYDNA_SECRET_KEY was supplied and we generated one.

        Fine for a local single-user run: it just means CSRF tokens do not
        survive a restart.
        """
        return not os.getenv("MYDNA_SECRET_KEY")

    def as_flask_mapping(self) -> dict[str, object]:
        return {
            "SECRET_KEY": self.secret_key,
            "MAX_CONTENT_LENGTH": self.max_upload_bytes,
            "DATABASE_URL": self.database_url,
            # Uploads are parsed from memory and never persisted, so refuse to
            # let Werkzeug spool a large upload to a temporary file on disk.
            "MAX_FORM_MEMORY_SIZE": self.max_upload_bytes,
        }
