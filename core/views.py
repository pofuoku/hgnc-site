from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

from core.forms import GeneSearchForm
from core.services import find_gene, find_related_genes

SEARCH_TEMPLATE = "core/search.html"


@require_GET
def gene_search(request):
    """
    Search page. With no ``q`` parameter it shows an empty search form;
    otherwise it validates the term, looks the gene up and shows the result.

    Status codes: 200 found (or no search yet), 400 invalid/empty input,
    404 gene not found.
    """
    if "q" not in request.GET:
        return render(request, SEARCH_TEMPLATE, {"form": GeneSearchForm()})

    form = GeneSearchForm(request.GET)
    if not form.is_valid():
        return render(request, SEARCH_TEMPLATE, {"form": form}, status=400)

    term = form.cleaned_data["q"]
    gene = find_gene(term)
    context = {"form": form, "term": term, "gene": gene}

    if gene is None:
        context["related_genes"] = find_related_genes(term)
        return render(request, SEARCH_TEMPLATE, context, status=404)

    context["hgnc_report_url"] = settings.HGNC_GENE_REPORT_URL.format(hgnc_id=gene["hgnc_id"])
    return render(request, SEARCH_TEMPLATE, context)
