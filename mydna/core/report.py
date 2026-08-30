"""Turn matched ClinVar records into a structured report.

Grouping and normalisation live here rather than in the template, so they can
be tested directly and so the templates stay free of logic.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from urllib.parse import quote

from mydna.core.parser import ParseResult
from mydna.core.repository import VariantRecord

_MISSING = {"", "na", "n/a", "none", "-", "not provided", "not specified"}

# ClinVar review status maps to the star rating shown on their own site. This
# is the single best signal of how much confidence to place in a record.
_REVIEW_STARS: dict[str, int] = {
    "practice guideline": 4,
    "reviewed by expert panel": 3,
    "criteria provided, multiple submitters, no conflicts": 2,
    "criteria provided, single submitter": 1,
    "criteria provided, conflicting classifications": 1,
    "criteria provided, conflicting interpretations": 1,
    "no assertion criteria provided": 0,
    "no classification provided": 0,
    "no assertion provided": 0,
    "no classifications from unflagged records": 0,
}

# Ordered most-to-least clinically notable. The first pattern to match wins, so
# the compound values ("Pathogenic/Likely pathogenic") must precede the simple
# ones. Deliberately conservative: anything unrecognised falls through to
# "Other" rather than being guessed at.
_CLASSIFICATION_RULES: list[tuple[str, str, str, int]] = [
    ("conflicting", "Conflicting classifications", "conflicting", 2),
    ("pathogenic/likely pathogenic", "Pathogenic / Likely pathogenic", "pathogenic", 0),
    ("likely pathogenic", "Likely pathogenic", "likely-pathogenic", 1),
    ("pathogenic", "Pathogenic", "pathogenic", 0),
    ("uncertain", "Uncertain significance", "uncertain", 3),
    ("risk factor", "Risk factor", "risk-factor", 4),
    ("drug response", "Drug response", "drug-response", 5),
    ("association", "Association", "other", 6),
    ("protective", "Protective", "benign", 8),
    ("benign/likely benign", "Benign / Likely benign", "benign", 7),
    ("likely benign", "Likely benign", "likely-benign", 8),
    ("benign", "Benign", "benign", 7),
]

_FALLBACK = ("Other or not provided", "other", 9)


@dataclass(frozen=True)
class Classification:
    label: str
    bucket: str
    rank: int


def classify(raw: str | None) -> Classification:
    value = (raw or "").strip().lower()
    if value in _MISSING:
        return Classification(*_FALLBACK)
    for needle, label, bucket, rank in _CLASSIFICATION_RULES:
        if needle in value:
            return Classification(label, bucket, rank)
    return Classification(*_FALLBACK)


def review_stars(review_status: str | None) -> int:
    return _REVIEW_STARS.get((review_status or "").strip().lower(), 0)


@dataclass(frozen=True)
class PhenotypeLink:
    source: str
    identifier: str
    url: str | None


def _phenotype_url(source: str, identifier: str) -> str | None:
    key = source.strip().lower()
    value = quote(identifier.strip(), safe="")
    if key == "medgen":
        return f"https://www.ncbi.nlm.nih.gov/medgen/{value}"
    if key == "omim":
        return f"https://www.omim.org/entry/{value}"
    if key == "orphanet":
        return f"https://www.orpha.net/en/disease/detail/{value}"
    if key == "mondo":
        return f"https://monarchinitiative.org/{value}"
    if key in {"human phenotype ontology", "hp"}:
        return f"https://hpo.jax.org/app/browse/term/{value}"
    return None


def parse_phenotype_ids(raw: str | None) -> list[PhenotypeLink]:
    """Parse ClinVar's ``PhenotypeIDS`` field.

    Conditions are separated by ``|`` and identifiers within a condition by
    ``,``, in ``Source:ID`` form. The previous implementation assumed the field
    was always present and raised AttributeError on the NULLs that are common
    in the real data.
    """
    if not raw or raw.strip().lower() in _MISSING:
        return []

    links: list[PhenotypeLink] = []
    seen: set[tuple[str, str]] = set()

    for condition in raw.split("|"):
        for token in condition.split(","):
            token = token.strip()
            if not token or token.lower() in _MISSING:
                continue
            if ":" not in token:
                continue
            # MONDO entries look like `MONDO:MONDO:0007254`, so split once only.
            source, identifier = token.split(":", 1)
            source, identifier = source.strip(), identifier.strip()
            if not source or not identifier:
                continue
            key = (source.lower(), identifier.lower())
            if key in seen:
                continue
            seen.add(key)
            links.append(PhenotypeLink(source, identifier, _phenotype_url(source, identifier)))
    return links


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return None if stripped.lower() in _MISSING else stripped


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


@dataclass(frozen=True)
class VariantView:
    rsid: int
    rsid_label: str
    gene_symbol: str | None
    clinical_significance: str | None
    variant_type: str | None
    last_evaluated: str | None
    review_status: str | None
    review_stars: int
    number_submitters: int | None
    conditions: list[str]
    phenotypes: list[PhenotypeLink]
    dbsnp_url: str
    clinvar_url: str
    dom_id: str


@dataclass
class TypeGroup:
    label: str
    slug: str
    variants: list[VariantView] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.variants)


@dataclass
class SignificanceGroup:
    label: str
    bucket: str
    rank: int
    types: list[TypeGroup] = field(default_factory=list)

    @property
    def count(self) -> int:
        return sum(group.count for group in self.types)


@dataclass
class Report:
    groups: list[SignificanceGroup]
    counts: dict[str, int]
    parse: ParseResult
    matched_records: int
    matched_rsids: int
    chart_data_uri: str | None = None
    index_metadata: dict[str, str] = field(default_factory=dict)

    @property
    def rsids_submitted(self) -> int:
        return self.parse.unique_rsids

    @property
    def notable_count(self) -> int:
        """Records ClinVar classifies as pathogenic or likely pathogenic."""
        return sum(
            group.count
            for group in self.groups
            if group.bucket in {"pathogenic", "likely-pathogenic"}
        )


def _to_view(record: VariantRecord, dom_id: str) -> VariantView:
    conditions = [
        part.strip()
        for part in (record.phenotype_list or "").split("|")
        if part.strip() and part.strip().lower() not in _MISSING
    ]
    return VariantView(
        rsid=record.rs_dbsnp,
        rsid_label=record.rsid_label,
        gene_symbol=_clean(record.gene_symbol),
        clinical_significance=_clean(record.clinical_significance),
        variant_type=_clean(record.variant_type),
        last_evaluated=_clean(record.last_evaluated),
        review_status=_clean(record.review_status),
        review_stars=review_stars(record.review_status),
        number_submitters=record.number_submitters,
        conditions=conditions,
        phenotypes=parse_phenotype_ids(record.phenotype_ids),
        dbsnp_url=f"https://www.ncbi.nlm.nih.gov/snp/{record.rsid_label}",
        clinvar_url=(
            f"https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(record.rsid_label, safe='')}"
        ),
        dom_id=dom_id,
    )


def build_report(
    records: list[VariantRecord],
    parse: ParseResult,
    index_metadata: dict[str, str] | None = None,
) -> Report:
    """Group matched records by clinical significance, then by variant type."""
    buckets: dict[Classification, dict[str, list[VariantRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in records:
        classification = classify(record.clinical_significance)
        buckets[classification][_clean(record.variant_type) or "Unspecified"].append(record)

    groups: list[SignificanceGroup] = []
    for classification in sorted(buckets, key=lambda item: (item.rank, item.label)):
        group = SignificanceGroup(
            label=classification.label,
            bucket=classification.bucket,
            rank=classification.rank,
        )
        for type_label in sorted(buckets[classification]):
            # Scope the slug to the significance group: the same variant type
            # appears under several classifications, and a bare type slug
            # produced duplicate DOM ids that broke the disclosure widgets.
            slug = f"{_slugify(classification.label)}-{_slugify(type_label)}"
            type_group = TypeGroup(label=type_label, slug=slug)
            for position, record in enumerate(buckets[classification][type_label]):
                type_group.variants.append(_to_view(record, f"{slug}-{position}"))
            group.types.append(type_group)
        groups.append(group)

    counts = Counter(classify(record.clinical_significance).label for record in records)

    return Report(
        groups=groups,
        counts=dict(counts),
        parse=parse,
        matched_records=len(records),
        matched_rsids=len({record.rs_dbsnp for record in records}),
        index_metadata=index_metadata or {},
    )
