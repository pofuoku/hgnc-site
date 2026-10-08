# HGNC-SITE: Gene Search

A **Django** web application for looking up human genes in the
[HGNC](https://www.genenames.org/) complete set.

Enter an HGNC-approved gene symbol (for example `BRCA2`) or an HGNC ID (for
example `HGNC:1101`) and the application shows, where available:

- HGNC gene symbol
- HGNC ID
- Gene name
- Previous gene symbols
- Previous gene names
- Gene aliases / synonyms
- MANE Select transcript
- MANE Plus Clinical transcript(s)

Missing values are shown as *Not available*. Empty, invalid or unexpected
input, and genes that cannot be found, produce a clear message. If a symbol is
not an approved symbol but is listed as a previous symbol or alias of a gene
(for example `FANCD1`), the application points to that gene.

## Requirements

- Python 3.12+ (with `venv`) or any environment/package manager (such as [Conda](https://docs.conda.io/), `uv`, or `mamba`)
- Git
- An internet connection the first time the HGNC data is downloaded

## Setup

### 1. Clone the repository

```bash
git clone [https://github.com/pofuoku/hgnc-site.git](https://github.com/pofuoku/hgnc-site.git)
cd hgnc-site
```

### 2. Create the Conda environment
You can use Python's built-in venv, Conda, or any package/environment manager of your choice.

#### Option A: Python venv

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows
```

#### Option B: Conda

```bash
# Create and activate the environment
conda env create -f environment.yml
conda activate hgnc-site
```

### 3. Install the application

From the project root (the folder containing `pyproject.toml`):

```bash
pip install -e .
```

This installs the application and its pinned Python dependencies into the
active Conda environment.

### 4. Create the database

```bash
python manage.py migrate
```

## Data

### Obtaining the HGNC source dataset

The application uses the HGNC complete set in TSV format:

<https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt>

You do not need to download it by hand: the `seed_data` command in the next
step downloads it to `data/hgnc_complete_set.txt` if it is not already there.

To download it yourself instead, save it to that location:

```bash
curl -L -o data/hgnc_complete_set.txt https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt
```

### Generating the dataset used by the application

```bash
python manage.py seed_data
```

This reads `data/hgnc_complete_set.txt` (downloading it first if needed),
builds the lightweight dataset (one dictionary per gene with only the fields
listed above) and loads it into the SQLite database. Running it again replaces
the stored genes, so the database always matches one HGNC release.

Options:

| Command | What it does |
| --- | --- |
| `python manage.py seed_data --download` | Download a fresh copy of the HGNC file, then load it |
| `python manage.py seed_data --source path/to/hgnc_complete_set.txt` | Load a specific local copy of the file |

HGNC updates the dataset regularly, so values may differ between downloads.

## Running the web application

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a web browser. You can also search directly
with a URL such as <http://127.0.0.1:8000/?q=BRCA2>.

## Running the tests

```bash
pytest
```

The tests use a small sample file (`core/tests/fixtures/hgnc_sample.txt`) and
a temporary test database, so they do not need the real HGNC download or an
internet connection.

## Test coverage report

Run the tests with coverage and generate the HTML report:

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

The coverage summary is printed in the terminal. The HTML report is written to
the `htmlcov` directory; open `htmlcov/index.html` in a web browser to view it,
for example:

```bash
open htmlcov/index.html        # macOS
xdg-open htmlcov/index.html    # Linux
start htmlcov\index.html       # Windows
```

Migrations, tests and Django boilerplate (`manage.py`, `wsgi.py`, `asgi.py`)
are excluded from the coverage measurement (see `[tool.coverage.run]` in
`pyproject.toml`).

## Project structure

```
hgnc-site/
├── environment.yml            Conda environment
├── pyproject.toml             Package definition, pinned dependencies, pytest/coverage settings
├── manage.py
├── data/                      Downloaded HGNC file (not committed)
├── hgnc_site/                 Django project: settings and root URLs
└── core/                      Django app
    ├── hgnc.py                Reads and processes the HGNC file into the lightweight dataset (no Django code)
    ├── search_terms.py        Validates and classifies user input (symbol vs HGNC ID)
    ├── services.py            Gene lookups that return dictionaries to the views
    ├── models.py              Gene model and manager for (re)loading the dataset
    ├── forms.py               Search form
    ├── views.py               Search view
    ├── urls.py
    ├── management/commands/
    │   └── seed_data.py       Builds and loads the dataset
    ├── templates/             Page templates and reusable partials
    ├── static/core/css/       Stylesheet
    └── tests/                 pytest test suite and sample HGNC data
```

How a search flows through the code:

1. `views.gene_search` receives the search term from the form (`forms.GeneSearchForm`).
2. The form uses `search_terms.parse_search_term` to reject empty or invalid
   input and decide whether the term is a symbol or an HGNC ID.
3. `services.find_gene` looks the gene up and returns it as a dictionary.
4. The view passes the dictionary to the `core/search.html` template.

## Configuration

Settings are in `hgnc_site/settings.py`. These can be overridden with
environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `HGNC_SOURCE_URL` | HGNC download URL above | Where `seed_data` downloads the file from |
| `HGNC_DATA_FILE` | `data/hgnc_complete_set.txt` | Where the HGNC file is stored and read |
| `DJANGO_DB_PATH` | `db.sqlite3` | SQLite database location |
| `DJANGO_SECRET_KEY` | development-only key | Secret key (set this for any real deployment) |
| `DJANGO_DEBUG` | `true` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed host names |

## Notes on the data

- **Multiple values.** HGNC separates multiple values in one field with `|`;
  these are stored as lists.
- **MANE Select.** HGNC gives the MANE Select transcript as an Ensembl ID and a
  RefSeq ID (for example `ENST00000380152.8|NM_000059.4`); both are shown.
