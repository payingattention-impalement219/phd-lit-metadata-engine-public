# Public Release Checklist

Use this checklist before publishing or mirroring the repository publicly.

## Keep Public

- source code in `backend/`, `frontend/`, `scripts/`, and `tests/`
- example configuration in `.env.example`
- query templates in `configs/`
- empty placeholders such as `data/.gitkeep` and `reports/.gitkeep`
- protocol templates and derivation scripts in `protocol/`
- notebooks with cleared outputs and project-relative paths only

## Keep Private

- `.env` and any `.env.*` files
- API keys and tokens
- `data/*.sqlite` and other local databases
- generated Excel, CSV, JSONL, RIS, BibTeX, TXT, PDF, or PNG report outputs
- manual citation exports from PubMed, ACM, IEEE, Scopus, Web of Science, or other databases
- screening decisions and reviewer notes unless intentionally anonymized for publication

## Recommended Public Publishing Route

For the safest public release, publish a fresh public repository from the sanitized current tree rather than changing an older private working repository to public. A fresh repository avoids carrying old commits that may contain local paths, draft notebook text, or other working artifacts.

Suggested flow:

```bash
git clone --depth 1 <private-repo-url> phd-lit-metadata-engine-public
cd phd-lit-metadata-engine-public
rm -rf .git
git init
git add .
git commit -m "Initial public release"
gh repo create phd-lit-metadata-engine --public --source=. --remote=origin --push
```

Before running the final `gh repo create`, rotate any API key that was ever pasted into chat, issues, commits, logs, or screenshots.

## Final Checks

```bash
git status --short
rg -n -i "(api[_ -]?key|secret|token|password|authorization|x-api-key)" .
rg -n "/Users/|Downloads|Desktop" .
```

These checks are not perfect secret scanners, but they catch the common mistakes. GitHub secret scanning should also be enabled on the public repository.
