"""
Tests for processing the HGNC source data (core.hgnc).

The sample file in fixtures/ is hand-made in the same shape as
hgnc_complete_set.txt; its values are illustrative and are not kept in sync
with the live HGNC release.
"""

import io
import urllib.request

import pytest

from core.hgnc import (
    LIGHTWEIGHT_KEYS,
    HGNCFormatError,
    download_hgnc_file,
    find_mane_plus_clinical_column,
    iter_genes,
    load_genes,
    parse_row,
    split_multi,
)


def tsv_stream(*lines):
    return io.StringIO("".join(line + "\n" for line in lines))


# --- split_multi -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("A|B|C", ["A", "B", "C"]),
        ("FLJ23569", ["FLJ23569"]),
        (" A | |B| ", ["A", "B"]),
        ("", []),
        ("   ", []),
        (None, []),
        # Commas appear inside previous names; only "|" separates values.
        ("Fanconi anemia, complementation group D1", ["Fanconi anemia, complementation group D1"]),
    ],
)
def test_split_multi(raw, expected):
    assert split_multi(raw) == expected


# --- parse_row ---------------------------------------------------------------


@pytest.fixture
def brca2_row():
    return {
        "hgnc_id": "HGNC:1101",
        "symbol": "BRCA2",
        "name": "BRCA2 DNA repair associated",
        "prev_symbol": "FANCD1",
        "prev_name": "Fanconi anemia, complementation group D1",
        "alias_symbol": "FAD|FAD1|BRCC2|XRCC11",
        "mane_select": "ENST00000380152.8|NM_000059.4",
        "locus_group": "protein-coding gene",
        "entrez_id": "675",
    }


def test_parse_row_builds_lightweight_dict(brca2_row):
    assert parse_row(brca2_row) == {
        "hgnc_id": "HGNC:1101",
        "gene_symbol": "BRCA2",
        "gene_name": "BRCA2 DNA repair associated",
        "previous_symbols": ["FANCD1"],
        "previous_names": ["Fanconi anemia, complementation group D1"],
        "aliases": ["FAD", "FAD1", "BRCC2", "XRCC11"],
        "mane_select": ["ENST00000380152.8", "NM_000059.4"],
        "mane_plus_clinical": [],
    }


def test_parse_row_drops_columns_not_in_lightweight_dataset(brca2_row):
    gene = parse_row(brca2_row)
    assert set(gene) == set(LIGHTWEIGHT_KEYS)
    assert "locus_group" not in gene and "entrez_id" not in gene


def test_parse_row_missing_optional_values_become_empty():
    gene = parse_row({"hgnc_id": "HGNC:5", "symbol": "A1BG"})
    assert gene["gene_name"] == ""
    for key in ("previous_symbols", "previous_names", "aliases", "mane_select", "mane_plus_clinical"):
        assert gene[key] == [], key


def test_parse_row_strips_whitespace(brca2_row):
    brca2_row.update(hgnc_id=" HGNC:1101 ", symbol=" BRCA2\t")
    gene = parse_row(brca2_row)
    assert (gene["hgnc_id"], gene["gene_symbol"]) == ("HGNC:1101", "BRCA2")


@pytest.mark.parametrize("missing", ["hgnc_id", "symbol"])
def test_parse_row_skips_rows_without_identifier(brca2_row, missing):
    brca2_row[missing] = "  "
    assert parse_row(brca2_row) is None


def test_parse_row_reads_mane_plus_clinical_column_when_given(brca2_row):
    brca2_row["mane_plus_clinical"] = "ENST00000530893.6|NM_001406716.1"
    gene = parse_row(brca2_row, mane_plus_clinical_column="mane_plus_clinical")
    assert gene["mane_plus_clinical"] == ["ENST00000530893.6", "NM_001406716.1"]


# --- find_mane_plus_clinical_column -------------------------------------------


@pytest.mark.parametrize(
    "header, expected",
    [
        (["hgnc_id", "symbol", "agr", "mane_select", "gencc"], None),  # current HGNC header
        (["hgnc_id", "symbol", "MANE_Plus_Clinical"], "MANE_Plus_Clinical"),
        (None, None),
    ],
)
def test_find_mane_plus_clinical_column(header, expected):
    assert find_mane_plus_clinical_column(header) == expected


# --- iter_genes / load_genes -------------------------------------------------


def test_load_genes_from_sample_file(sample_hgnc_file):
    genes = load_genes(sample_hgnc_file)
    # The sample has 4 data rows; the row without an HGNC ID is skipped.
    assert [g["hgnc_id"] for g in genes] == ["HGNC:5", "HGNC:37133", "HGNC:1101"]
    assert all(set(g) == set(LIGHTWEIGHT_KEYS) for g in genes)


def test_quoted_multi_value_fields_are_split(sample_genes):
    genes = {g["gene_symbol"]: g for g in sample_genes}
    a1bg_as1 = genes["A1BG-AS1"]
    assert a1bg_as1["previous_symbols"] == ["NCRNA00181", "A1BGAS", "A1BG-AS"]
    assert len(a1bg_as1["previous_names"]) == 3
    assert a1bg_as1["aliases"] == ["FLJ23569"]
    assert a1bg_as1["mane_select"] == []
    # A quoted value containing a comma stays one value.
    assert genes["BRCA2"]["previous_names"] == ["Fanconi anemia, complementation group D1"]


def test_mane_plus_clinical_column_used_when_present():
    stream = tsv_stream(
        "hgnc_id\tsymbol\tname\tmane_select\tmane_plus_clinical",
        "HGNC:1\tGENE1\tgene one\tENST1.1|NM_1.1\tENST2.1|NM_2.1",
    )
    (gene,) = iter_genes(stream)
    assert gene["mane_plus_clinical"] == ["ENST2.1", "NM_2.1"]


def test_missing_optional_columns_and_short_rows_are_tolerated():
    stream = tsv_stream("hgnc_id\tsymbol\tname\talias_symbol", "HGNC:1\tGENE1")
    (gene,) = iter_genes(stream)
    assert gene["gene_name"] == ""
    assert gene["aliases"] == []


def test_missing_required_column_raises():
    with pytest.raises(HGNCFormatError, match="hgnc_id"):
        list(iter_genes(tsv_stream("symbol\tname", "GENE1\tgene one")))


def test_empty_file_raises():
    with pytest.raises(HGNCFormatError):
        list(iter_genes(io.StringIO("")))


def test_header_only_yields_nothing():
    assert list(iter_genes(tsv_stream("hgnc_id\tsymbol\tname"))) == []


def test_load_genes_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        load_genes(tmp_path / "missing.txt")


# --- download_hgnc_file -------------------------------------------------------


class FakeResponse(io.BytesIO):
    """Stands in for the object returned by urllib.request.urlopen."""


def test_download_writes_file(monkeypatch, tmp_path):
    requested = {}

    def fake_urlopen(url, timeout):
        requested["url"] = url
        return FakeResponse(b"hgnc_id\tsymbol\nHGNC:5\tA1BG\n")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    destination = tmp_path / "nested" / "hgnc.txt"

    result = download_hgnc_file("https://example.org/hgnc.txt", destination)

    assert result == destination
    assert requested["url"] == "https://example.org/hgnc.txt"
    assert destination.read_text() == "hgnc_id\tsymbol\nHGNC:5\tA1BG\n"
    assert not (tmp_path / "nested" / "hgnc.txt.part").exists()


def test_failed_download_leaves_no_partial_file(monkeypatch, tmp_path):
    def failing_urlopen(url, timeout):
        raise OSError("network unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", failing_urlopen)
    destination = tmp_path / "hgnc.txt"

    with pytest.raises(OSError):
        download_hgnc_file("https://example.org/hgnc.txt", destination)

    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []
