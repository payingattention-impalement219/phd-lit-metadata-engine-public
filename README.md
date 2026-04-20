# PhD Literature Metadata Engine

A local scholarly metadata harvesting app for PhD literature searches. It collects paper metadata only: titles, abstracts, keywords, authors, journals, years, DOIs, identifiers, citation counts, and source links.

It does not download PDFs or scrape full papers.

## What It Covers

Open/API-first sources:

- PubMed / MEDLINE via NCBI E-utilities
- Europe PMC
- OpenAlex
- Crossref
- Semantic Scholar, free public metadata endpoints with optional API key for steadier rate limits
- DOAJ
- CORE, when an API key is configured
- IEEE Xplore, when an API key is configured
- arXiv
- medRxiv
- bioRxiv

Optional licensed connectors:

- Scopus via Elsevier APIs, when credentials are configured
- Web of Science placeholder/status support, with import fallback recommended unless API access is available
- ACM Digital Library is import/manual for now; export RIS/BibTeX/CSV from ACM DL and keep those files with your review materials

Import/export workflows are included for `.xlsx`, `.csv`, `.txt`, `.jsonl`, `.bib`, and `.ris`.

Rate limits vary by source. The dashboard shows source-specific rate-limit notes, and the backend uses conservative delays plus retry/backoff for `429 Too Many Requests` responses. See [Source Rate-Limit Notes](docs/rate_limits.md).

## Custom Search Strings

The web app accepts one main search string plus any number of custom strings. Use this for:

- alternative Boolean formulations
- database-specific wording
- synonyms and spelling variants
- narrower subtopic searches

Each selected source runs the main string and each custom string. The app then merges and deduplicates the combined metadata.

Example strings:

```text
("your condition or topic" OR "your synonym") AND ("your method" OR "your second concept")
("your broader topic" OR "related term") AND ("your method" OR "related method")
("your narrower topic" OR "specific subtopic") AND ("your outcome" OR "your task")
```

The editable YAML query pack also supports `custom_search_strings` for repeatable searches.

Placeholder strings that contain phrases such as `your topic`, `your method`, or `related term` are ignored by the backend. Replace them with real search terms before running a search.

For database-specific syntax, use **Database-specific strings** in the web app:

- PubMed/MEDLINE: paste `[TIAB]` strings and MeSH strings into the PubMed box.
- Scopus: paste `TITLE-ABS-KEY(...)` into the Scopus box.
- Web of Science: paste `TS=...` into the Web of Science box.
- IEEE Xplore: paste the IEEE Boolean string into the IEEE Xplore box after adding `IEEE_API_KEY`.
- arXiv, medRxiv, and bioRxiv: paste simplified portal-style strings such as `concept A method term`.
- Europe PMC: use broad quoted terms with `AND` / `OR`.
- OpenAlex and Crossref: use simpler keyword-rich strings; their APIs search bibliographic metadata rather than accepting database field tags.
- Semantic Scholar: use a concise Boolean string. The app uses Semantic Scholar's bulk metadata endpoint with token pagination, so results fall directly into the same dedupe/export pipeline. Most metadata searches work without a key; add `SEMANTIC_SCHOLAR_API_KEY` only for heavier or repeated runs.
- DOAJ and CORE: use a compact Boolean string focused on title/abstract/keyword style terms.

These strings are sent only to their matching database. This prevents PubMed syntax from being sent to Scopus, or Scopus syntax from being sent to OpenAlex/Crossref.

If the database-specific boxes already contain strings, you do not need to copy and paste them again. They run automatically when that source is selected and you click **Run metadata search**. Edit or clear any box if you want different behavior.

The YAML query pack supports the same idea with `source_specific_search_strings`.

IEEE Xplore is available when `IEEE_API_KEY` is configured. arXiv, medRxiv, and bioRxiv are available without keys. ACM Digital Library is import/manual for now: run those strings on the ACM portal, export RIS/BibTeX/CSV, and keep the exported files with your review materials.

For the quietest first run, select only open sources:

- PubMed / MEDLINE
- Europe PMC
- OpenAlex
- Crossref
- Semantic Scholar
- DOAJ
- arXiv
- medRxiv / bioRxiv if preprints are in scope

Semantic Scholar is included in the open-source preset. It is free for most metadata searches, and the connector uses the `/graph/v1/paper/search/bulk` endpoint with token-based pagination. The shared unauthenticated pool can still return `429` during busy or multi-string runs, so the optional API key improves reliability rather than unlocking basic access.

Restricted or entitlement-based sources:

- Scopus requires a valid `ELSEVIER_API_KEY` with Scopus Search API entitlement; some accounts also need `ELSEVIER_INST_TOKEN`.
- IEEE Xplore requires `IEEE_API_KEY`.
- Web of Science remains import/manual until a concrete Clarivate API endpoint and entitlement are configured.
- ACM Digital Library is import/manual.

## Quick Start

### Homebrew Setup On macOS

If you use Homebrew, install the local app dependencies first:

```bash
brew update
brew install node python@3.12
```

Confirm they are available:

```bash
node --version
npm --version
python3.12 --version
```

Jupyter is installed through the Python development dependencies below, so you do not need a separate Homebrew Jupyter install.

### Project Setup

```bash
git clone https://github.com/<your-org-or-user>/phd-lit-metadata-engine.git
cd phd-lit-metadata-engine
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e './backend[dev]'
cd frontend
npm install
cd ..
python scripts/dev.py
```

If you already created `.venv` with Apple Python 3.9, remove it and recreate it with Homebrew Python:

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
python --version
```

The version printed by `python --version` should be Python 3.12.x.

Then open:

- Web app: `http://127.0.0.1:5173`
- Backend API docs: `http://127.0.0.1:8000/docs`

## One-Command Local App

After dependencies are installed, this starts both the FastAPI backend and React frontend:

```bash
python scripts/dev.py
```

## Troubleshooting Setup

If the app prints `No module named uvicorn`, the backend dependencies are not installed in the active virtual environment. Run:

```bash
source .venv/bin/activate
python --version
python -m pip install --upgrade pip setuptools wheel
pip install -e './backend[dev]'
```

If `python --version` prints Python 3.9.x, the virtual environment was created with Apple Python. Recreate it with Homebrew Python:

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e './backend[dev]'
```

The backend binds to `127.0.0.1` by default. Notebook launcher endpoints are local-only.

## Notebook Buttons

The web interface includes:

- **Open in Jupyter**: starts Jupyter Lab/Notebook locally and opens `notebooks/01_metadata_analysis.ipynb`.
- **Open in VS Code**: opens the same notebook with the `code` CLI when available.
- **Export Then Open Notebook**: exports current results and writes `notebooks/analysis_context.json`, so the notebook can load the latest file.

If Jupyter or VS Code is not installed, the interface shows setup guidance instead of failing silently.

If Jupyter opens as `Internal Server Error` or the app reports that Jupyter is unavailable, install it into the project environment:

```bash
cd phd-lit-metadata-engine
source .venv/bin/activate
pip install jupyterlab
```

If the app says `VS Code 'code' CLI is not on PATH`, open VS Code and run:

1. Press `Cmd+Shift+P`
2. Search for `Shell Command: Install 'code' command in PATH`
3. Run it
4. Restart the local app

You can also open notebooks through Jupyter while the VS Code CLI is unavailable.

## Data And Git

The repo tracks source code, configs, tests, and notebooks. It does not track generated data:

- `data/`
- `reports/`
- local SQLite databases
- API caches
- `.env`

## API Keys

Most open sources work without keys, but keys improve reliability and coverage:

- `CONTACT_EMAIL`: recommended for OpenAlex, Crossref, and NCBI polite access.
- `NCBI_API_KEY`: optional PubMed rate-limit increase.
- `OPENALEX_API_KEY`: optional for low-volume testing, recommended for reliable authenticated OpenAlex access.
- `SEMANTIC_SCHOLAR_API_KEY`: optional; Semantic Scholar works without it for most metadata searches, but the key gives steadier rate limits.
- `CORE_API_KEY`: required for CORE.
- `ELSEVIER_API_KEY`: required for Scopus.
- `WEB_OF_SCIENCE_API_KEY`: optional placeholder for future Web of Science direct API integration.
- `IEEE_API_KEY`: required for IEEE Xplore.

You can update these in either of two ways:

1. Open the local web app and use the **Setup status** panel. Missing values are shown clearly, saved values are masked, and updates are written to `.env`.
2. Edit `.env` directly in the project root.

The app never displays saved API keys in full. It only shows whether a value is configured and a short masked preview.

For public publishing, keep `.env`, local databases, generated reports, manual citation exports, and reviewer screening files private. See `SECURITY.md` and `docs/public_release.md` before making a repository public.

After changing API keys while the app is running, new searches use the updated values. If something still looks stale, restart the local app with:

```bash
python scripts/dev.py
```

If Semantic Scholar returns a rate-limit message, the app retries automatically. If the limit still persists, wait briefly, reduce the number of custom strings, or add the optional `SEMANTIC_SCHOLAR_API_KEY` in the **Setup status** panel.

## Safety Boundaries

- Metadata only.
- No PDFs.
- No full-text redistribution.
- Optional licensed databases are skipped when credentials are missing.
- Search jobs and notebook launcher commands run locally.
