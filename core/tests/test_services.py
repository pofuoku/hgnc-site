"""Tests for gene lookups (core.services)."""

import pytest

from core.models import Gene
from core.search_terms import parse_search_term
from core.services import MAX_RELATED_GENES, find_gene, find_related_genes

pytestmark = pytest.mark.django_db


def test_find_gene_by_symbol_returns_dict(seeded_db):
    gene = find_gene(parse_search_term("BRCA2"))
    assert isinstance(gene, dict)
    assert gene["hgnc_id"] == "HGNC:1101"
    assert gene["gene_name"] == "BRCA2 DNA repair associated"


@pytest.mark.parametrize("raw", ["brca2", "Brca2", "BRCA2"])
def test_find_gene_symbol_is_case_insensitive(seeded_db, raw):
    assert find_gene(parse_search_term(raw))["gene_symbol"] == "BRCA2"


@pytest.mark.parametrize("raw", ["HGNC:1101", "hgnc:1101", "HGNC:01101"])
def test_find_gene_by_hgnc_id(seeded_db, raw):
    assert find_gene(parse_search_term(raw))["gene_symbol"] == "BRCA2"


@pytest.mark.parametrize("raw", ["NOTAGENE", "HGNC:999999"])
def test_find_gene_not_found_returns_none(seeded_db, raw):
    assert find_gene(parse_search_term(raw)) is None


def test_find_gene_with_missing_optional_information(seeded_db):
    gene = find_gene(parse_search_term("A1BG"))
    assert gene["previous_symbols"] == []
    assert gene["aliases"] == []
    assert gene["mane_plus_clinical"] == []


def test_symbol_search_does_not_match_previous_symbol(seeded_db):
    # FANCD1 is a previous symbol of BRCA2, not an approved symbol.
    assert find_gene(parse_search_term("FANCD1")) is None


@pytest.mark.parametrize(
    "raw, matched_as",
    [("FANCD1", "previous symbol"), ("fancd1", "previous symbol"), ("FAD", "alias")],
)
def test_find_related_genes(seeded_db, raw, matched_as):
    related = find_related_genes(parse_search_term(raw))
    assert related == [
        {
            "hgnc_id": "HGNC:1101",
            "gene_symbol": "BRCA2",
            "gene_name": "BRCA2 DNA repair associated",
            "matched_as": matched_as,
        }
    ]


def test_find_related_genes_requires_whole_symbol_match(seeded_db):
    # "FAD" is an alias of BRCA2 but "FA" is only a substring of one.
    assert find_related_genes(parse_search_term("FA")) == []


def test_find_related_genes_ignores_hgnc_ids(seeded_db):
    assert find_related_genes(parse_search_term("HGNC:1101")) == []


def test_find_related_genes_is_limited(db):
    Gene.objects.bulk_create(
        Gene(hgnc_id=f"HGNC:{i}", gene_symbol=f"GENE{i}", aliases=["SHARED"])
        for i in range(MAX_RELATED_GENES + 5)
    )
    assert len(find_related_genes(parse_search_term("SHARED"))) == MAX_RELATED_GENES
