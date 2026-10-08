"""
Checking and classifying what a user typed into the search box.

A search term is either an HGNC ID (e.g. "HGNC:1101") or an HGNC-approved
gene symbol (e.g. "BRCA2"). Anything else is rejected with a message that
explains what was expected. This module has no Django dependency.
"""

import re
from dataclasses import dataclass

HGNC_ID = "hgnc_id"
SYMBOL = "symbol"

MAX_TERM_LENGTH = 50

# "HGNC:1101", case-insensitive, optional spaces around the colon.
HGNC_ID_PATTERN = re.compile(r"^HGNC\s*:\s*(\d+)$", re.IGNORECASE)

# Approved symbols start with a letter and contain letters, digits and a few
# punctuation characters (e.g. "C1orf112", "HLA-A", "MT-ND1").
SYMBOL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._@-]*$")


class InvalidSearchTerm(ValueError):
    """The search term is empty or cannot be a gene symbol or HGNC ID."""


@dataclass(frozen=True)
class SearchTerm:
    kind: str  # HGNC_ID or SYMBOL
    value: str  # normalised value used for the lookup

    @property
    def is_hgnc_id(self):
        return self.kind == HGNC_ID

    @property
    def label(self):
        """Human-readable description of the search type."""
        return "HGNC ID" if self.is_hgnc_id else "gene symbol"


def parse_search_term(raw):
    """
    Validate a raw search string and return a SearchTerm.

    Raises InvalidSearchTerm with a user-facing message if the input is empty
    or cannot be an HGNC ID or gene symbol.
    """
    term = (raw or "").strip()

    if not term:
        raise InvalidSearchTerm("Please enter a gene symbol (e.g. BRCA2) or an HGNC ID (e.g. HGNC:1101).")

    if len(term) > MAX_TERM_LENGTH:
        raise InvalidSearchTerm(
            f"Search terms can be at most {MAX_TERM_LENGTH} characters long."
        )

    match = HGNC_ID_PATTERN.match(term)
    if match:
        # int() drops leading zeros so "HGNC:01101" finds "HGNC:1101".
        return SearchTerm(HGNC_ID, f"HGNC:{int(match.group(1))}")

    if term.upper().startswith("HGNC"):
        raise InvalidSearchTerm(
            "HGNC IDs are written as HGNC: followed by a number, e.g. HGNC:1101."
        )

    if term.isdigit():
        raise InvalidSearchTerm(
            f"A number on its own is not a gene symbol. Did you mean the HGNC ID HGNC:{int(term)}?"
        )

    if SYMBOL_PATTERN.match(term):
        return SearchTerm(SYMBOL, term)

    raise InvalidSearchTerm(
        "Gene symbols contain only letters, numbers and the characters - . _ @, "
        "and start with a letter (e.g. BRCA2, HLA-A, C1orf112)."
    )
