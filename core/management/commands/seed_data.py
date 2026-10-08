from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.hgnc import HGNCFormatError, download_hgnc_file, load_genes
from core.models import Gene


class Command(BaseCommand):
    help = (
        "Build the lightweight gene dataset from the HGNC complete set and load it "
        "into the database. Downloads the HGNC file first if it is not already "
        "present at settings.HGNC_DATA_FILE."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            help="Path to a local hgnc_complete_set.txt to use instead of settings.HGNC_DATA_FILE.",
        )
        parser.add_argument(
            "--download",
            action="store_true",
            help="Download a fresh copy of the HGNC file even if one already exists.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of genes inserted per database batch (default: 1000).",
        )

    def handle(self, *args, **options):
        source = self.resolve_source(options["source"], options["download"])

        self.stdout.write(f"Reading HGNC data from {source} ...")
        try:
            genes = load_genes(source)
        except (OSError, HGNCFormatError) as exc:
            raise CommandError(f"Could not read HGNC data: {exc}") from exc

        if not genes:
            raise CommandError("No genes were found in the source file; database left unchanged.")

        deleted, created = Gene.objects.replace_all(genes, batch_size=options["batch_size"])

        with_mane_plus = sum(1 for gene in genes if gene["mane_plus_clinical"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {created} genes (replaced {deleted} existing). "
                f"{with_mane_plus} have MANE Plus Clinical transcripts."
            )
        )

    def resolve_source(self, source, force_download):
        """Return the path of the HGNC file to read, downloading it if needed."""
        if source:
            return Path(source)

        data_file = Path(settings.HGNC_DATA_FILE)
        if force_download or not data_file.exists():
            self.stdout.write(f"Downloading {settings.HGNC_SOURCE_URL} ...")
            try:
                download_hgnc_file(settings.HGNC_SOURCE_URL, data_file)
            except OSError as exc:  # includes urllib.error.URLError
                raise CommandError(f"Could not download HGNC data: {exc}") from exc
            self.stdout.write(f"Saved to {data_file}")
        return data_file
