"""Read access to the local ClinVar index."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import (
    BigInteger,
    Column,
    Engine,
    MetaData,
    Table,
    create_engine,
    insert,
    select,
)
from sqlalchemy.exc import SQLAlchemyError

from mydna.data.schema import variants

# Chunk size for populating the lookup table. Comfortably under SQLite's
# historical 999-parameter ceiling once multiplied out by one column.
_INSERT_CHUNK = 500

# Session-scoped scratch table holding the rsIDs from one upload. Temporary
# tables are per-connection, so concurrent requests cannot see each other's.
_scratch_metadata = MetaData()
query_rsids = Table(
    "query_rsids",
    _scratch_metadata,
    Column("rs_dbsnp", BigInteger, nullable=False),
    prefixes=["TEMPORARY"],
)


class IndexUnavailableError(RuntimeError):
    """The ClinVar index is missing or has not been built."""


@dataclass(frozen=True)
class VariantRecord:
    rs_dbsnp: int
    gene_symbol: str | None
    hgnc_id: str | None
    clinical_significance: str | None
    variant_type: str | None
    last_evaluated: str | None
    review_status: str | None
    number_submitters: int | None
    phenotype_list: str | None
    phenotype_ids: str | None

    @property
    def rsid_label(self) -> str:
        return f"rs{self.rs_dbsnp}"


def create_index_engine(database_url: str) -> Engine:
    """Build the single, long-lived engine used for all lookups.

    The previous DAO called ``create_engine`` and reflected the table on every
    request, which meant a fresh connection and a round trip of schema queries
    per upload.
    """
    connect_args = {}
    if database_url.startswith("sqlite"):
        # Flask may serve a request on a different thread than the one that
        # created the engine's pooled connection.
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, future=True)


class VariantRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(select(variants.c.rs_dbsnp).limit(1))
            return True
        except SQLAlchemyError:
            return False

    def find_variants(self, rsids: Sequence[int]) -> list[VariantRecord]:
        """Return every index entry matching the supplied rsIDs.

        A consumer export carries hundreds of thousands of rsIDs, far past any
        backend's bound-parameter limit, so the IDs go into a temporary table
        and the match is a join.
        """
        # np.array_split on an empty list raised before reaching the database.
        if not rsids:
            return []

        if not self.is_ready():
            raise IndexUnavailableError(
                "The ClinVar index is missing or empty. Run `mydna index build` first."
            )

        columns = [
            variants.c.rs_dbsnp,
            variants.c.gene_symbol,
            variants.c.hgnc_id,
            variants.c.clinical_significance,
            variants.c.variant_type,
            variants.c.last_evaluated,
            variants.c.review_status,
            variants.c.number_submitters,
            variants.c.phenotype_list,
            variants.c.phenotype_ids,
        ]

        with self._engine.connect() as connection:
            # Defensive: a pooled connection could carry a leftover table if a
            # previous request died between create and drop.
            query_rsids.drop(connection, checkfirst=True)
            query_rsids.create(connection)
            try:
                for batch in _chunked(rsids, _INSERT_CHUNK):
                    connection.execute(
                        insert(query_rsids),
                        [{"rs_dbsnp": int(value)} for value in batch],
                    )

                query = select(*columns).select_from(
                    variants.join(
                        query_rsids,
                        variants.c.rs_dbsnp == query_rsids.c.rs_dbsnp,
                    )
                )
                rows = connection.execute(query).mappings().all()
            finally:
                query_rsids.drop(connection, checkfirst=True)

        return [VariantRecord(**row) for row in rows]


def _chunked(values: Sequence[int], size: int) -> Iterable[Sequence[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]
