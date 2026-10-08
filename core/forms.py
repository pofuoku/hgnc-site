from django import forms

from core.search_terms import MAX_TERM_LENGTH, InvalidSearchTerm, parse_search_term


class GeneSearchForm(forms.Form):
    """
    Search box accepting a gene symbol or an HGNC ID.

    After validation, cleaned_data["q"] is a core.search_terms.SearchTerm.
    """

    q = forms.CharField(
        label="Gene symbol or HGNC ID",
        required=False,  # empty input gets a friendlier message from parse_search_term
        strip=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. BRCA2 or HGNC:1101",
                "maxlength": MAX_TERM_LENGTH,
                "autocomplete": "off",
                "spellcheck": "false",
                "autofocus": True,
            }
        ),
    )

    def clean_q(self):
        try:
            return parse_search_term(self.cleaned_data.get("q"))
        except InvalidSearchTerm as exc:
            raise forms.ValidationError(str(exc), code="invalid_search") from exc
