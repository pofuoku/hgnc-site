"""
Django settings for the HGNC gene search project.

Values that differ between machines (secret key, debug flag, data locations)
can be overridden with environment variables so nothing needs to be edited in
the code to run the project elsewhere.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    """Read a true/false environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Development-only fallback key; set DJANGO_SECRET_KEY for any real deployment.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-key-change-me-for-deployment",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hgnc_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hgnc_site.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3")),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True



STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# Where the HGNC complete set is downloaded from.
HGNC_SOURCE_URL = os.environ.get(
    "HGNC_SOURCE_URL",
    "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt",
)

# Where the downloaded HGNC file is kept locally. The seed_data command reads
# this file and downloads it first if it is missing.
HGNC_DATA_FILE = Path(
    os.environ.get("HGNC_DATA_FILE", BASE_DIR / "data" / "hgnc_complete_set.txt")
)

# Link to the HGNC gene report shown on result pages ({hgnc_id} is filled in).
HGNC_GENE_REPORT_URL = "https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/{hgnc_id}"
