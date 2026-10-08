from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("", views.gene_search, name="gene_search"),
]
