from django.contrib import admin

from core.models import Gene


@admin.register(Gene)
class GeneAdmin(admin.ModelAdmin):
    list_display = ("gene_symbol", "hgnc_id", "gene_name")
    search_fields = ("gene_symbol", "hgnc_id", "gene_name")
