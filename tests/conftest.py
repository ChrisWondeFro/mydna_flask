"""Shared test fixtures.

Every fixture here is synthetic. No real genetic data is used anywhere in this
suite, and none should ever be added.
"""

from __future__ import annotations

import gzip
import shutil
from pathlib import Path

import pytest

from mydna import create_app
from mydna.config import Config
from mydna.core.repository import VariantRepository, create_index_engine
from mydna.data.build_index import build_index

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def clinvar_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Gzip the sample variant summary, mirroring NCBI's distribution format."""
    target = tmp_path_factory.mktemp("clinvar") / "variant_summary.txt.gz"
    with (
        (FIXTURES / "variant_summary_sample.tsv").open("rb") as source,
        gzip.open(target, "wb") as destination,
    ):
        shutil.copyfileobj(source, destination)
    return target


@pytest.fixture(scope="session")
def index_path(tmp_path_factory: pytest.TempPathFactory, clinvar_source: Path) -> Path:
    """Build a small index once and reuse it across the session."""
    path = tmp_path_factory.mktemp("index") / "clinvar.sqlite"
    build_index(f"sqlite:///{path}", clinvar_source, echo=False)
    return path


@pytest.fixture
def database_url(index_path: Path) -> str:
    return f"sqlite:///{index_path}"


@pytest.fixture
def repository(database_url: str) -> VariantRepository:
    engine = create_index_engine(database_url)
    try:
        yield VariantRepository(engine)
    finally:
        engine.dispose()


@pytest.fixture
def app(database_url: str):
    application = create_app(Config(database_url=database_url, secret_key="test-secret-key"))
    application.config.update(TESTING=True)
    yield application
    application.extensions["mydna"]["engine"].dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_client(client):
    """A client whose session already holds a CSRF token.

    Fetching the index page seeds the token, exactly as a browser would.
    """
    client.get("/")
    return client


def csrf_token_for(client) -> str:

    with client.session_transaction() as flask_session:
        return flask_session["_csrf_token"]


@pytest.fixture
def ancestry_file() -> bytes:
    return (FIXTURES / "ancestry_sample.txt").read_bytes()


@pytest.fixture
def twenty_three_file() -> bytes:
    return (FIXTURES / "23andme_sample.txt").read_bytes()
