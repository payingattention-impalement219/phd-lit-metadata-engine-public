# Security Policy

## Supported Use

This project is designed to run locally and collect scholarly metadata only. It should not be used to download full-text papers, PDFs, or copyrighted article bodies.

## Secrets and Private Data

Do not commit:

- `.env` files or API keys
- SQLite databases from `data/`
- generated exports from `reports/`
- manual screening workbooks
- RIS, BibTeX, CSV, or Excel files exported from licensed databases
- notebook context files such as `notebooks/analysis_context.json`

Use `.env.example` as the public template and keep real credentials in a local `.env` file.

## Reporting a Vulnerability

Open a private security advisory or contact the repository owner directly. Do not post API keys, logs with credentials, or private research data in public issues.
