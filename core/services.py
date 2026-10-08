"""
Gene lookups used by the web application.

Views pass a validated SearchTerm here and get back plain Python dictionaries
from the lightweight dataset, so the views never deal with database queries.
"""

from core.models import Gene
from core.search_terms import SearchTerm

MAX_RELATED_GENES = 10


def find_gene(term: SearchTerm):
    """
    Return the lightweight dict for the gene matching ``term``, or None.

    HGNC IDs must match exactly (they are normalised by parse_search_term);
    gene symbols are matched case-insensitively, so "brca2" finds BRCA2.
    """
    if term.is_hgnc_id:
        gene = Gene.objects.filter(hgnc_id=term.value).first()
    else:
        gene = Gene.objects.filter(gene_symbol__iexact=term.value).first()
    return gene.to_dict() if gene else None


def find_related_genes(term: SearchTerm):
    """
    For a symbol that is not an approved symbol, find genes that list it as a
    previous symbol or an alias.

    Returns a list of dicts: {"hgnc_id", "gene_symbol", "gene_name", "matched_as"}.
    """
    if term.is_hgnc_id:
        return []

    wanted = term.value.upper()
    # The database filter narrows the candidates using a text match on the
    # JSON lists; the exact, case-insensitive check is then done in Python.
    candidates = Gene.objects.filter(previous_symbols__icontains=term.value) | Gene.objects.filter(
        aliases__icontains=term.value
    )

    related = []
    for gene in candidates.order_by("gene_symbol")[: MAX_RELATED_GENES * 5]:
        if wanted in (symbol.upper() for symbol in gene.previous_symbols):
            matched_as = "previous symbol"
        elif wanted in (alias.upper() for alias in gene.aliases):
            matched_as = "alias"
        else:
            continue
        related.append(
            {
                "hgnc_id": gene.hgnc_id,
                "gene_symbol": gene.gene_symbol,
                "gene_name": gene.gene_name,
                "matched_as": matched_as,
            }
        )
        if len(related) == MAX_RELATED_GENES:
            break
    return related
