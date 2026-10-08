"""
Reading and processing the HGNC complete set (hgnc_complete_set.txt).

This module turns the full HGNC TSV file into the *lightweight dataset*: one
Python dictionary per gene holding only the fields the application needs.

It deliberately has no Django dependency, so the data processing is kept
separate from the web application and can be used and tested on its own.
"""

import csv
import shutil
import sys
import urllib.request
from pathlib import Path

# Multi-value fields in the HGNC file are separated by "|".
MULTI_VALUE_SEPARATOR = "|"

# Some HGNC fields can be very long, so raise the csv module's field size limit.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# HGNC column -> lightweight dataset key, for fields holding a single value.
SINGLE_VALUE_COLUMNS = {
    "hgnc_id": "hgnc_id",
    "symbol": "gene_symbol",
    "name": "gene_name",
}

# HGNC column -> lightweight dataset key, for fields that may hold several values.
MULTI_VALUE_COLUMNS = {
    "prev_symbol": "previous_symbols",
    "prev_name": "previous_names",
    "alias_symbol": "aliases",
    "mane_select": "mane_select",
}

# The current HGNC file has no dedicated MANE Plus Clinical column. If HGNC adds
# one under any of these names it is picked up automatically; otherwise the
# field is left empty for every gene.
MANE_PLUS_CLINICAL_CANDIDATES = (
    "mane_plus_clinical",
    "mane_plus_clinical_transcript",
    "mane_clinical",
)

REQUIRED_COLUMNS = ("hgnc_id", "symbol")

LIGHTWEIGHT_KEYS = (
    *SINGLE_VALUE_COLUMNS.values(),
    *MULTI_VALUE_COLUMNS.values(),
    "mane_plus_clinical",
)


class HGNCFormatError(ValueError):
    """Raised when the file does not look like the HGNC complete set."""


def clean(value):
    """Return a stripped string, or '' for a missing value."""
    if value is None:
        return ""
    return value.strip()


def split_multi(value):
    """
    Split a "|"-separated HGNC field into a list of non-empty values.

    'NCRNA00181|A1BGAS|A1BG-AS' -> ['NCRNA00181', 'A1BGAS', 'A1BG-AS']
    ''                           -> []
    """
    value = clean(value)
    if not value:
        return []
    return [part.strip() for part in value.split(MULTI_VALUE_SEPARATOR) if part.strip()]


def find_mane_plus_clinical_column(fieldnames):
    """Return the MANE Plus Clinical column name if the file has one, else None."""
    lowered = {name.lower(): name for name in fieldnames or []}
    for candidate in MANE_PLUS_CLINICAL_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return None


def parse_row(row, mane_plus_clinical_column=None):
    """
    Convert one HGNC row (a dict from csv.DictReader) into a lightweight dict.

    Returns None for rows without an HGNC ID or approved symbol, as these
    cannot be searched for.
    """
    gene = {key: clean(row.get(column)) for column, key in SINGLE_VALUE_COLUMNS.items()}
    if not gene["hgnc_id"] or not gene["gene_symbol"]:
        return None

    for column, key in MULTI_VALUE_COLUMNS.items():
        gene[key] = split_multi(row.get(column))

    gene["mane_plus_clinical"] = (
        split_multi(row.get(mane_plus_clinical_column)) if mane_plus_clinical_column else []
    )
    return gene


def iter_genes(lines):
    """
    Yield lightweight gene dicts from an iterable of HGNC TSV lines.

    Raises HGNCFormatError if the header is missing a required column.
    """
    reader = csv.DictReader(lines, delimiter="\t")
    fieldnames = reader.fieldnames or []
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        raise HGNCFormatError(
            f"HGNC file is missing required column(s): {', '.join(missing)}"
        )

    mane_plus_clinical_column = find_mane_plus_clinical_column(fieldnames)
    for row in reader:
        gene = parse_row(row, mane_plus_clinical_column)
        if gene is not None:
            yield gene


def load_genes(path):
    """Read an HGNC file from disk and return the lightweight dataset as a list."""
    with open(path, encoding="utf-8", newline="") as stream:
        return list(iter_genes(stream))


def download_hgnc_file(url, destination, timeout=120):
    """
    Download the HGNC file from ``url`` to ``destination``.

    The file is written to a temporary ".part" file first and only moved into
    place once complete, so a failed download never leaves a half-written file.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, open(partial, "wb") as out:
            shutil.copyfileobj(response, out)
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)
    return destination
