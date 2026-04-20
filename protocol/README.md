# Protocol Companion Files

This folder contains the OSF-ready companion files for the scoping review:

- `extraction_codebook_v1.csv`: 75-field standardised data-charting codebook.
- `derived_variables.py`: deterministic derivation script for row-level indices and aggregate summaries.
- `CHANGELOG.md`: versioned amendment log for codebook and derivation changes.

Run the derivation script after freezing the human-charted CSV:

```bash
python protocol/derived_variables.py path/to/frozen_extracted_dataset.csv \
  --output-prefix reports/derived_variables/review_protocol_v1
```

The script writes:

- `*.derived.csv`
- `*.summary.json`
- `*.derived.xlsx`

No imputation is performed. Missing values are excluded pairwise from aggregate statistics.
