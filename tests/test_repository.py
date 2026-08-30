"""Index build and lookup tests."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from mydna.core.repository import VariantRepository, create_index_engine
from mydna.data.build_index import build_index, index_row_count, read_index_metadata


def test_build_accepts_an_uncompressed_tsv(tmp_path: Path):
    """NCBI ships a gzip, but a locally decompressed variant_summary.txt must work."""
    source = Path(__file__).parent / "fixtures" / "variant_summary_sample.tsv"
    target = tmp_path / "index.sqlite"

    stats = build_index(f"sqlite:///{target}", source, echo=False)

    assert stats.rows_kept == 7


def test_build_keeps_only_grch38_rows_with_an_rsid(clinvar_source: Path, tmp_path: Path):
    target = tmp_path / "index.sqlite"
    stats = build_index(f"sqlite:///{target}", clinvar_source, echo=False)

    # The sample has 9 rows: one GRCh37 duplicate and one with RS# of -1.
    assert stats.rows_read == 9
    assert stats.rows_kept == 7
    assert stats.rows_dropped == 2


def test_build_records_provenance(clinvar_source: Path, tmp_path: Path):
    target = tmp_path / "index.sqlite"
    build_index(f"sqlite:///{target}", clinvar_source, echo=False)

    engine = create_index_engine(f"sqlite:///{target}")
    try:
        metadata = read_index_metadata(engine)
        assert metadata["assembly"] == "GRCh38"
        assert metadata["schema_version"] == "1"
        assert metadata["row_count"] == "7"
        assert index_row_count(engine) == 7
    finally:
        engine.dispose()


def test_build_creates_the_lookup_index(database_url: str):
    """Without this index every lookup is a full scan of millions of rows."""
    engine = create_index_engine(database_url)
    try:
        with engine.connect() as connection:
            names = {
                row[0]
                for row in connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='index'")
                )
            }
        assert "ix_variants_rs_dbsnp" in names
    finally:
        engine.dispose()


def test_rebuild_is_idempotent(clinvar_source: Path, tmp_path: Path):
    target = tmp_path / "index.sqlite"
    build_index(f"sqlite:///{target}", clinvar_source, echo=False)
    build_index(f"sqlite:///{target}", clinvar_source, echo=False)

    engine = create_index_engine(f"sqlite:///{target}")
    try:
        assert index_row_count(engine) == 7
    finally:
        engine.dispose()


def test_lookup_returns_matching_records(repository: VariantRepository):
    records = repository.find_variants([334, 1800562])

    assert {record.rs_dbsnp for record in records} == {334, 1800562}
    assert any(record.gene_symbol == "HBB" for record in records)


def test_empty_input_returns_nothing_rather_than_raising(repository: VariantRepository):
    """np.array_split on an empty list raised before reaching the database."""
    assert repository.find_variants([]) == []


def test_lookup_handles_more_ids_than_the_parameter_limit(repository: VariantRepository):
    """A real export has hundreds of thousands of rsIDs."""
    rsids = list(range(1, 7000)) + [1800562]

    records = repository.find_variants(rsids)

    assert {record.rs_dbsnp for record in records} == {334, 6025, 1800562}


def test_repeated_lookups_do_not_leak_the_scratch_table(repository: VariantRepository):
    for _ in range(5):
        assert repository.find_variants([334])


def test_missing_index_is_reported_not_crashed(tmp_path: Path):
    engine = create_index_engine(f"sqlite:///{tmp_path / 'absent.sqlite'}")
    try:
        assert VariantRepository(engine).is_ready() is False
    finally:
        engine.dispose()
