"""Shared pytest fixtures for the core app tests."""

from pathlib import Path

import pytest

from core.hgnc import load_genes

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_hgnc_file():
    """Path to a small hand-made file in the same format as hgnc_complete_set.txt."""
    return FIXTURES_DIR / "hgnc_sample.txt"


@pytest.fixture
def sample_genes(sample_hgnc_file):
    """The lightweight dataset built from the sample HGNC file."""
    return load_genes(sample_hgnc_file)


@pytest.fixture
def seeded_db(db, sample_genes):
    """A database loaded with the sample genes."""
    from core.models import Gene

    Gene.objects.replace_all(sample_genes)
    return Gene.objects.all()


@pytest.fixture
def write_tsv(tmp_path):
    """Write tab-separated lines to a temporary file and return its path."""

    def _write(*lines, name="hgnc.txt"):
        path = tmp_path / name
        path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        return path

    return _write
