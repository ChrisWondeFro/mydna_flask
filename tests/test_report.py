"""Report construction: classification, phenotype parsing, and grouping."""

from __future__ import annotations

import pytest

from mydna.core.parser import ParseResult
from mydna.core.report import (
    build_report,
    classify,
    parse_phenotype_ids,
    review_stars,
)
from mydna.core.repository import VariantRecord


def make_record(**overrides) -> VariantRecord:
    defaults = {
        "rs_dbsnp": 334,
        "gene_symbol": "HBB",
        "hgnc_id": "HGNC:4827",
        "clinical_significance": "Pathogenic",
        "variant_type": "single nucleotide variant",
        "last_evaluated": "Nov 12, 2023",
        "review_status": "criteria provided, multiple submitters, no conflicts",
        "number_submitters": 12,
        "phenotype_list": "Sickle cell disease",
        "phenotype_ids": "MedGen:C0002895,OMIM:603903",
    }
    defaults.update(overrides)
    return VariantRecord(**defaults)


@pytest.mark.parametrize(
    ("raw", "bucket"),
    [
        ("Pathogenic", "pathogenic"),
        ("Likely pathogenic", "likely-pathogenic"),
        ("Pathogenic/Likely pathogenic", "pathogenic"),
        ("Benign", "benign"),
        ("Likely benign", "likely-benign"),
        ("Benign/Likely benign", "benign"),
        ("Uncertain significance", "uncertain"),
        ("Conflicting classifications of pathogenicity", "conflicting"),
        ("risk factor", "risk-factor"),
        ("drug response", "drug-response"),
        ("not provided", "other"),
        (None, "other"),
        ("", "other"),
        ("something nobody has seen", "other"),
    ],
)
def test_classification_buckets(raw, bucket):
    assert classify(raw).bucket == bucket


def test_conflicting_wins_over_the_word_pathogenic():
    """'Conflicting classifications of pathogenicity' contains 'pathogenic'."""
    assert classify("Conflicting classifications of pathogenicity").bucket == "conflicting"


@pytest.mark.parametrize(
    ("status", "stars"),
    [
        ("practice guideline", 4),
        ("reviewed by expert panel", 3),
        ("criteria provided, multiple submitters, no conflicts", 2),
        ("criteria provided, single submitter", 1),
        ("no assertion criteria provided", 0),
        (None, 0),
    ],
)
def test_review_stars(status, stars):
    assert review_stars(status) == stars


def test_phenotype_ids_are_parsed_into_links():
    links = parse_phenotype_ids("MedGen:C0002895,OMIM:603903|Orphanet:232")

    assert [link.source for link in links] == ["MedGen", "OMIM", "Orphanet"]
    assert links[1].url == "https://www.omim.org/entry/603903"


def test_phenotype_ids_handle_doubled_source_prefix():
    """MONDO entries are written `MONDO:MONDO:0011382`."""
    links = parse_phenotype_ids("MONDO:MONDO:0011382")

    assert links[0].source == "MONDO"
    assert links[0].identifier == "MONDO:0011382"


@pytest.mark.parametrize("raw", [None, "", "na", "  ", "-"])
def test_missing_phenotype_ids_do_not_raise(raw):
    """The original raised AttributeError on the NULLs present in real data."""
    assert parse_phenotype_ids(raw) == []


def test_phenotype_ids_skip_unparseable_tokens():
    assert parse_phenotype_ids("no_colon_here,MedGen:C1") == list(parse_phenotype_ids("MedGen:C1"))


def test_duplicate_phenotype_ids_are_collapsed():
    links = parse_phenotype_ids("MedGen:C1,MedGen:C1|MedGen:C1")
    assert len(links) == 1


def _parse_result(unique: int = 2) -> ParseResult:
    return ParseResult(
        rsids=list(range(unique)),
        total_rows=10,
        skipped_internal=1,
        skipped_unreadable=0,
        detected_format="AncestryDNA",
    )


def test_groups_are_ordered_by_clinical_notability():
    records = [
        make_record(rs_dbsnp=1, clinical_significance="Benign"),
        make_record(rs_dbsnp=2, clinical_significance="Pathogenic"),
        make_record(rs_dbsnp=3, clinical_significance="Uncertain significance"),
    ]

    report = build_report(records, _parse_result(3))

    assert [group.bucket for group in report.groups] == [
        "pathogenic",
        "uncertain",
        "benign",
    ]


def test_dom_ids_are_unique_across_groups():
    """The same variant type appears under several classifications; a bare
    type slug produced colliding element ids."""
    records = [
        make_record(rs_dbsnp=1, clinical_significance="Pathogenic"),
        make_record(rs_dbsnp=2, clinical_significance="Benign"),
    ]

    report = build_report(records, _parse_result(2))
    slugs = [type_group.slug for group in report.groups for type_group in group.types]

    assert len(slugs) == len(set(slugs))


def test_notable_count_covers_pathogenic_buckets_only():
    records = [
        make_record(rs_dbsnp=1, clinical_significance="Pathogenic"),
        make_record(rs_dbsnp=2, clinical_significance="Likely pathogenic"),
        make_record(rs_dbsnp=3, clinical_significance="Benign"),
    ]

    assert build_report(records, _parse_result(3)).notable_count == 2


def test_matched_rsids_counts_variants_not_records():
    """One variant can hold several ClinVar records."""
    records = [
        make_record(rs_dbsnp=1801133, clinical_significance="Benign"),
        make_record(rs_dbsnp=1801133, clinical_significance="Conflicting classifications"),
    ]

    report = build_report(records, _parse_result(1))

    assert report.matched_records == 2
    assert report.matched_rsids == 1


def test_empty_result_builds_an_empty_report():
    report = build_report([], _parse_result(0))

    assert report.groups == []
    assert report.notable_count == 0
