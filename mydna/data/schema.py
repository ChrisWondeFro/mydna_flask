"""Schema for the local ClinVar index.

The index stores only what the report actually reads: the eleven fields the
report renders, for GRCh38 rows that carry a real dbSNP rsID. The upstream
``variant_summary.txt`` has 30+ columns and both assemblies, so this filtering
is what makes a SQLite-backed index practical.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

SCHEMA_VERSION = "1"
ASSEMBLY = "GRCh38"
SOURCE_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"

metadata = MetaData()

variants = Table(
    "variants",
    metadata,
    Column("rs_dbsnp", Integer, nullable=False),
    Column("gene_symbol", Text),
    Column("hgnc_id", Text),
    Column("clinical_significance", Text),
    Column("variant_type", Text),
    Column("last_evaluated", Text),
    Column("review_status", Text),
    Column("number_submitters", Integer),
    Column("phenotype_list", Text),
    Column("phenotype_ids", Text),
)

# Every lookup is `WHERE rs_dbsnp IN (...)`. Without this index each request is
# a full table scan over millions of rows.
Index("ix_variants_rs_dbsnp", variants.c.rs_dbsnp)

index_metadata = Table(
    "index_metadata",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("value", Text),
)

# Source column name -> our column name. Selecting by name (rather than the
# previous positional handling) keeps the build working when NCBI appends new
# columns, which it does periodically.
COLUMN_MAP: dict[str, str] = {
    "RS# (dbSNP)": "rs_dbsnp",
    "GeneSymbol": "gene_symbol",
    "HGNC_ID": "hgnc_id",
    "ClinicalSignificance": "clinical_significance",
    "Type": "variant_type",
    "LastEvaluated": "last_evaluated",
    "ReviewStatus": "review_status",
    "NumberSubmitters": "number_submitters",
    "PhenotypeList": "phenotype_list",
    "PhenotypeIDS": "phenotype_ids",
}

# Needed to filter rows but not stored: we keep only one assembly, so recording
# it per row would be a few million redundant strings.
FILTER_COLUMNS = ["Assembly"]

SOURCE_COLUMNS = list(COLUMN_MAP) + FILTER_COLUMNS
