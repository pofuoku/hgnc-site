from django.db import models, transaction


class GeneManager(models.Manager):
    def replace_all(self, genes, batch_size=2000):
        """
        Replace every stored gene with ``genes`` in one
        transaction, so the table always matches a single HGNC release.

        Returns a (deleted, created) tuple of counts.
        """
        records = [self.model(**gene) for gene in genes]
        with transaction.atomic():
            deleted, _ = self.all().delete()
            self.bulk_create(records, batch_size=batch_size)
        return deleted, len(records)


class Gene(models.Model):
    """
    Lightweight record of an HGNC gene.

    Multi-valued HGNC fields are stored as JSON lists; an empty list means the
    value is not available in the source data.
    """

    hgnc_id = models.CharField("HGNC ID", max_length=20, unique=True)
    gene_symbol = models.CharField("Approved symbol", max_length=50, db_index=True)
    gene_name = models.CharField("Approved name", max_length=255, blank=True)
    previous_symbols = models.JSONField(default=list, blank=True)
    previous_names = models.JSONField(default=list, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    # HGNC gives the MANE Select transcript as Ensembl + RefSeq IDs,
    # e.g. ["ENST00000380152.8", "NM_000059.4"].
    mane_select = models.JSONField(default=list, blank=True)
    mane_plus_clinical = models.JSONField(default=list, blank=True)

    objects = GeneManager()

    class Meta:
        ordering = ["gene_symbol"]

    def __str__(self):
        return f"{self.gene_symbol} ({self.hgnc_id})"

    def to_dict(self):
        """Return the gene as a lightweight-dataset dictionary."""
        return {
            "hgnc_id": self.hgnc_id,
            "gene_symbol": self.gene_symbol,
            "gene_name": self.gene_name,
            "previous_symbols": list(self.previous_symbols),
            "previous_names": list(self.previous_names),
            "aliases": list(self.aliases),
            "mane_select": list(self.mane_select),
            "mane_plus_clinical": list(self.mane_plus_clinical),
        }
