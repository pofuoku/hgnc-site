"""
Tests for creating the dataset used by the application: the Gene model,
its manager, and the seed_data management command.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core.models import Gene

pytestmark = pytest.mark.django_db


def run_seed_data(*args):
    out = StringIO()
    call_command("seed_data", *args, stdout=out)
    return out.getvalue()


# --- Gene model ---------------------------------------------------------------


def test_gene_to_dict_round_trips_lightweight_dict(sample_genes):
    brca2 = next(g for g in sample_genes if g["gene_symbol"] == "BRCA2")
    gene = Gene.objects.create(**brca2)
    assert gene.to_dict() == brca2


def test_gene_defaults_to_empty_lists_for_optional_fields():
    gene = Gene.objects.create(hgnc_id="HGNC:5", gene_symbol="A1BG")
    data = gene.to_dict()
    assert data["gene_name"] == ""
    assert data["aliases"] == [] and data["mane_plus_clinical"] == []


def test_gene_str():
    assert str(Gene(hgnc_id="HGNC:1101", gene_symbol="BRCA2")) == "BRCA2 (HGNC:1101)"


def test_replace_all_replaces_existing_genes(sample_genes):
    Gene.objects.create(hgnc_id="HGNC:999999", gene_symbol="OLDGENE")

    deleted, created = Gene.objects.replace_all(sample_genes)

    assert (deleted, created) == (1, 3)
    assert not Gene.objects.filter(gene_symbol="OLDGENE").exists()
    assert set(Gene.objects.values_list("gene_symbol", flat=True)) == {"A1BG", "A1BG-AS1", "BRCA2"}


# --- seed_data command --------------------------------------------------------


def test_seed_data_loads_genes_from_source_file(sample_hgnc_file):
    output = run_seed_data("--source", str(sample_hgnc_file))

    assert "Loaded 3 genes" in output
    brca2 = Gene.objects.get(hgnc_id="HGNC:1101")
    assert brca2.gene_symbol == "BRCA2"
    assert brca2.aliases == ["FAD", "FAD1", "BRCC2", "XRCC11"]
    assert brca2.mane_select == ["ENST00000380152.8", "NM_000059.4"]


def test_seed_data_is_repeatable(sample_hgnc_file):
    run_seed_data("--source", str(sample_hgnc_file))
    output = run_seed_data("--source", str(sample_hgnc_file))

    assert "replaced 3 existing" in output
    assert Gene.objects.count() == 3


def test_seed_data_uses_configured_file_without_downloading(settings, sample_hgnc_file, monkeypatch):
    settings.HGNC_DATA_FILE = sample_hgnc_file

    def unexpected_download(*args, **kwargs):
        pytest.fail("seed_data should not download when the data file exists")

    monkeypatch.setattr(
        "core.management.commands.seed_data.download_hgnc_file", unexpected_download
    )
    run_seed_data()
    assert Gene.objects.count() == 3


@pytest.mark.parametrize("extra_args, file_exists", [([], False), (["--download"], True)])
def test_seed_data_downloads_when_missing_or_requested(
    settings, tmp_path, sample_hgnc_file, monkeypatch, extra_args, file_exists
):
    data_file = tmp_path / "data" / "hgnc_complete_set.txt"
    if file_exists:
        data_file.parent.mkdir()
        data_file.write_text("stale contents", encoding="utf-8")
    settings.HGNC_DATA_FILE = data_file
    settings.HGNC_SOURCE_URL = "https://example.org/hgnc.txt"
    calls = []

    def fake_download(url, destination):
        calls.append((url, destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(sample_hgnc_file.read_bytes())
        return destination

    monkeypatch.setattr("core.management.commands.seed_data.download_hgnc_file", fake_download)

    output = run_seed_data(*extra_args)

    assert calls == [("https://example.org/hgnc.txt", data_file)]
    assert "Downloading https://example.org/hgnc.txt" in output
    assert Gene.objects.count() == 3


def test_seed_data_reports_download_failure(settings, tmp_path, monkeypatch):
    settings.HGNC_DATA_FILE = tmp_path / "hgnc.txt"

    def failing_download(url, destination):
        raise OSError("network unreachable")

    monkeypatch.setattr("core.management.commands.seed_data.download_hgnc_file", failing_download)

    with pytest.raises(CommandError, match="Could not download HGNC data"):
        run_seed_data()


def test_seed_data_missing_source_file(tmp_path):
    with pytest.raises(CommandError, match="Could not read HGNC data"):
        run_seed_data("--source", str(tmp_path / "missing.txt"))


def test_seed_data_rejects_file_that_is_not_hgnc_data(write_tsv):
    path = write_tsv("name\tvalue", "foo\tbar")
    with pytest.raises(CommandError, match="missing required column"):
        run_seed_data("--source", str(path))


def test_seed_data_with_no_genes_keeps_existing_data(write_tsv):
    Gene.objects.create(hgnc_id="HGNC:5", gene_symbol="A1BG")
    path = write_tsv("hgnc_id\tsymbol\tname")

    with pytest.raises(CommandError, match="No genes were found"):
        run_seed_data("--source", str(path))

    assert Gene.objects.filter(gene_symbol="A1BG").exists()


def test_no_missing_migrations():
    """The committed migrations match the current models."""
    call_command("makemigrations", "core", "--check", "--dry-run", stdout=StringIO())
