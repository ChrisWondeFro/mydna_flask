"""Parser tests.

The parser sees the widest variety of real-world input, and its failures in the
original code were the ones that broke genuine uploads.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from mydna.core.parser import ParseError, parse_raw_dna, validate_filename


def parse(data: bytes, filename: str = "AncestryDNA.txt"):
    return parse_raw_dna(io.BytesIO(data), filename)


def test_parses_ancestry_export(ancestry_file: bytes):
    result = parse(ancestry_file)

    assert result.detected_format == "AncestryDNA"
    assert 334 in result.rsids
    assert 1800562 in result.rsids
    assert result.unique_rsids == 6


def test_parses_23andme_header_hidden_in_comments(twenty_three_file: bytes):
    """23andMe puts its header on a comment line.

    Passing `comment='#'` to pandas, as the original did, discarded that line
    and shifted every column by one.
    """
    result = parse(twenty_three_file, "genome_23andme.txt")

    assert result.detected_format == "23andMe"
    assert sorted(result.rsids) == [334, 6025, 429358, 1800562, 1801133]
    assert result.skipped_internal == 1


def test_internal_probe_ids_are_skipped_not_fatal(ancestry_file: bytes):
    """`i`-prefixed AncestryDNA IDs used to crash the whole upload."""
    result = parse(ancestry_file)

    assert result.skipped_internal == 3
    assert all(isinstance(rsid, int) for rsid in result.rsids)


def test_rs_prefix_is_stripped_only_at_the_start():
    """`str.replace('rs', '')` also mangled 'rs' occurring later in a value."""
    data = b"rsid\tchromosome\tposition\nrs1234rs5\t1\t100\nrs42\t1\t200\n"
    result = parse(data)

    assert result.rsids == [42]
    assert result.skipped_unreadable == 1


def test_comma_separated_file_is_detected():
    data = b"rsid,chromosome,position\nrs334,11,5248232\nrs6025,1,169519049\n"
    result = parse(data, "export.csv")

    assert sorted(result.rsids) == [334, 6025]


def test_duplicate_rsids_are_collapsed():
    data = b"rsid\tchromosome\nrs334\t11\nrs334\t11\nrs6025\t1\n"
    result = parse(data)

    assert sorted(result.rsids) == [334, 6025]
    assert result.total_rows == 3


def test_missing_rsid_column_is_reported_clearly():
    data = b"marker\tchromosome\nfoo\t1\n"

    with pytest.raises(ParseError, match="rsid"):
        parse(data)


def test_file_with_no_usable_rsids_is_rejected():
    data = b"rsid\tchromosome\ni3000001\t1\ni3000002\t1\n"

    with pytest.raises(ParseError, match="No dbSNP rsIDs"):
        parse(data)


def test_empty_file_is_rejected():
    with pytest.raises(ParseError, match="empty"):
        parse(b"")


def test_file_with_only_comments_is_rejected():
    with pytest.raises(ParseError):
        parse(b"# just a header\n# and another\n")


@pytest.mark.parametrize("filename", ["data.exe", "genome.zip", "noextension", ""])
def test_extension_allowlist_rejects_other_types(filename: str):
    """The form's `accept` attribute is advisory; the server must enforce."""
    with pytest.raises(ParseError):
        validate_filename(filename)


@pytest.mark.parametrize("filename", ["a.txt", "a.CSV", "a.tsv", "a.xlsx"])
def test_extension_allowlist_accepts_expected_types(filename: str):
    assert validate_filename(filename)


def test_genotypes_are_not_retained(ancestry_file: bytes):
    """Only identifiers survive parsing; allele calls are dropped."""
    result = parse(ancestry_file)

    assert not hasattr(result, "genotypes")
    assert all(isinstance(value, int) for value in result.rsids)


def test_ancestry_legal_preamble_is_not_treated_as_a_header():
    """Real AncestryDNA exports discuss 'the SNP identifier (rsID where
    possible)' in the comment block. Those words used to match the 'snp' and
    'identifier' column aliases and steal the header."""
    data = (
        b"#AncestryDNA raw data download\n"
        b"#corresponds to a SNP.  Column one provides the SNP identifier (rsID where \n"
        b"#possible).  Columns two and three contain the chromosome and basepair position\n"
        b"rsid\tchromosome\tposition\tallele1\tallele2\n"
        b"rs41293455\t17\t41234451\tG\tG\n"
        b"rs80356935\t17\t41246489\tC\tC\n"
        b"rs3131972\t1\t752721\tA\tA\n"
    )
    result = parse(data)

    assert result.detected_format == "AncestryDNA"
    assert result.rsids == [41293455, 80356935, 3131972]


def test_xlsx_is_parsed_without_the_old_comment_kwarg(tmp_path):
    """`read_excel(..., comment='#')` used to TypeError on every .xlsx upload."""
    pytest.importorskip("openpyxl")
    path = tmp_path / "export.xlsx"
    frame = pd.DataFrame({"rsid": ["rs334", "i3000001", "rs6025"], "chromosome": [11, 1, 1]})
    frame.to_excel(path, index=False)

    result = parse(path.read_bytes(), "export.xlsx")

    assert result.detected_format == "spreadsheet"
    assert sorted(result.rsids) == [334, 6025]
    assert result.skipped_internal == 1
