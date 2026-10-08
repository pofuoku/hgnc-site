"""Tests for validating and classifying user search input (core.search_terms)."""

import pytest

from core.search_terms import (
    HGNC_ID,
    MAX_TERM_LENGTH,
    SYMBOL,
    InvalidSearchTerm,
    SearchTerm,
    parse_search_term,
)


@pytest.mark.parametrize(
    "raw, expected_value",
    [
        ("HGNC:1101", "HGNC:1101"),
        ("hgnc:1101", "HGNC:1101"),
        ("  HGNC:1101  ", "HGNC:1101"),
        ("HGNC : 1101", "HGNC:1101"),
        ("HGNC:01101", "HGNC:1101"),
    ],
)
def test_hgnc_ids_are_recognised_and_normalised(raw, expected_value):
    assert parse_search_term(raw) == SearchTerm(HGNC_ID, expected_value)


@pytest.mark.parametrize("raw", ["BRCA2", "brca2", "C1orf112", "HLA-A", "MT-ND1", "A1BG-AS1"])
def test_symbols_are_recognised(raw):
    term = parse_search_term(raw)
    assert term.kind == SYMBOL
    assert term.value == raw


def test_symbol_whitespace_is_stripped():
    assert parse_search_term("  TP53 \n").value == "TP53"


@pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
def test_empty_input_is_rejected(raw):
    with pytest.raises(InvalidSearchTerm, match="Please enter"):
        parse_search_term(raw)


def test_overlong_input_is_rejected():
    with pytest.raises(InvalidSearchTerm, match=str(MAX_TERM_LENGTH)):
        parse_search_term("A" * (MAX_TERM_LENGTH + 1))


def test_input_at_maximum_length_is_accepted():
    assert parse_search_term("A" * MAX_TERM_LENGTH).kind == SYMBOL


@pytest.mark.parametrize("raw", ["HGNC:", "HGNC:abc", "HGNC1101", "HGNC:-5", "hgnc:12x"])
def test_malformed_hgnc_ids_are_rejected(raw):
    with pytest.raises(InvalidSearchTerm, match="HGNC:1101"):
        parse_search_term(raw)


def test_bare_number_suggests_hgnc_id():
    with pytest.raises(InvalidSearchTerm, match="Did you mean the HGNC ID HGNC:1101"):
        parse_search_term("1101")


@pytest.mark.parametrize(
    "raw",
    [
        "BRCA2 TP53",  # two terms
        "<script>alert(1)</script>",
        "'; DROP TABLE core_gene; --",
        "BRCA2!",
        "-BRCA2",
        "1ABC",
        "BRCÄ2",
    ],
)
def test_unexpected_characters_are_rejected(raw):
    with pytest.raises(InvalidSearchTerm):
        parse_search_term(raw)


def test_search_term_labels():
    assert SearchTerm(HGNC_ID, "HGNC:1").label == "HGNC ID"
    assert SearchTerm(SYMBOL, "BRCA2").label == "gene symbol"
    assert SearchTerm(HGNC_ID, "HGNC:1").is_hgnc_id
    assert not SearchTerm(SYMBOL, "BRCA2").is_hgnc_id
