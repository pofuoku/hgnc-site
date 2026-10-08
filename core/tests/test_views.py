"""Tests for the gene search view, form and templates."""

import pytest
from django.urls import reverse

from core.forms import GeneSearchForm
from core.models import Gene
from core.search_terms import SYMBOL

SEARCH_URL = reverse("core:gene_search")

pytestmark = pytest.mark.django_db


def search(client, q):
    return client.get(SEARCH_URL, {"q": q})


# --- Landing page -------------------------------------------------------------


def test_search_page_without_query_shows_empty_form(client):
    response = client.get(SEARCH_URL)

    assert response.status_code == 200
    assert "core/search.html" in [t.name for t in response.templates]
    assert response.context["form"].is_bound is False
    assert "gene" not in response.context
    assert b"Gene symbol or HGNC ID" in response.content


def test_static_stylesheet_is_linked(client):
    response = client.get(SEARCH_URL)
    assert b"/static/core/css/style.css" in response.content


# --- Successful searches ------------------------------------------------------


def test_search_by_symbol_shows_all_gene_details(client, seeded_db):
    response = search(client, "BRCA2")
    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["gene"]["hgnc_id"] == "HGNC:1101"
    for expected in (
        "BRCA2",
        "HGNC:1101",
        "BRCA2 DNA repair associated",
        "FANCD1",  # previous symbol
        "Fanconi anemia, complementation group D1",  # previous name
        "XRCC11",  # alias
        "ENST00000380152.8",  # MANE Select (Ensembl)
        "NM_000059.4",  # MANE Select (RefSeq)
        "MANE Plus Clinical transcript(s)",
    ):
        assert expected in content, expected


def test_search_by_lowercase_symbol(client, seeded_db):
    response = search(client, "brca2")
    assert response.status_code == 200
    assert response.context["gene"]["gene_symbol"] == "BRCA2"


def test_search_by_hgnc_id(client, seeded_db):
    response = search(client, "HGNC:37133")
    assert response.status_code == 200
    assert response.context["gene"]["gene_symbol"] == "A1BG-AS1"
    assert "A1BG antisense RNA 1" in response.content.decode()


def test_result_links_to_hgnc_report(client, seeded_db):
    response = search(client, "BRCA2")
    assert response.context["hgnc_report_url"].endswith("HGNC:1101")
    assert response.context["hgnc_report_url"] in response.content.decode()


def test_missing_optional_information_shows_not_available(client, seeded_db):
    # A1BG has no previous symbols/names, aliases or MANE Plus Clinical.
    response = search(client, "A1BG")
    content = response.content.decode()

    assert response.status_code == 200
    assert content.count("Not available") == 4
    assert "ENST00000263100.8" in content


def test_gene_with_no_name_or_lists(client, db):
    Gene.objects.create(hgnc_id="HGNC:42", gene_symbol="BARE")
    response = search(client, "BARE")
    content = response.content.decode()

    assert response.status_code == 200
    assert "Gene name not available" in content
    assert content.count("Not available") == 6


# --- Not found ----------------------------------------------------------------


@pytest.mark.parametrize("q, label", [("NOTAGENE", "gene symbol"), ("HGNC:999999", "HGNC ID")])
def test_gene_not_found(client, seeded_db, q, label):
    response = search(client, q)
    content = response.content.decode()

    assert response.status_code == 404
    assert response.context["gene"] is None
    assert "No gene found" in content
    assert f"No gene has the {label}" in content


def test_not_found_suggests_gene_with_previous_symbol(client, seeded_db):
    response = search(client, "FANCD1")
    content = response.content.decode()

    assert response.status_code == 404
    assert "previous symbol" in content
    assert "?q=HGNC%3A1101" in content


# --- Empty, invalid and unexpected input --------------------------------------


@pytest.mark.parametrize("q", ["", "   "])
def test_empty_search_shows_message(client, seeded_db, q):
    response = search(client, q)

    assert response.status_code == 400
    assert "Please enter a gene symbol" in response.content.decode()
    assert "gene" not in response.context


@pytest.mark.parametrize(
    "q, message",
    [
        ("HGNC:abc", "HGNC IDs are written as HGNC:"),
        ("1101", "Did you mean the HGNC ID HGNC:1101"),
        ("BRCA2 TP53", "Gene symbols contain only"),
        ("X" * 51, "at most 50 characters"),
    ],
)
def test_invalid_input_shows_message(client, seeded_db, q, message):
    response = search(client, q)

    assert response.status_code == 400
    assert message in response.content.decode()


def test_user_input_is_escaped_in_page(client, seeded_db):
    response = search(client, "<script>alert(1)</script>")
    content = response.content.decode()

    assert response.status_code == 400
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content  # value is redisplayed safely in the search box


def test_post_is_not_allowed(client):
    response = client.post(SEARCH_URL, {"q": "BRCA2"})
    assert response.status_code == 405


def test_unknown_url_returns_404(client):
    response = client.get("/no-such-page/")
    assert response.status_code == 404


def test_custom_404_page_when_debug_is_off(client, settings):
    settings.DEBUG = False
    response = client.get("/no-such-page/")
    assert response.status_code == 404
    assert b"Page not found" in response.content


# --- Form ---------------------------------------------------------------------


def test_form_cleans_to_search_term():
    form = GeneSearchForm({"q": " brca2 "})
    assert form.is_valid()
    term = form.cleaned_data["q"]
    assert (term.kind, term.value) == (SYMBOL, "brca2")


def test_form_reports_invalid_input():
    form = GeneSearchForm({"q": "HGNC:abc"})
    assert not form.is_valid()
    assert form.errors["q"][0].startswith("HGNC IDs are written")
