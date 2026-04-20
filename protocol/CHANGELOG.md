# Changelog

All notable changes to the extraction codebook and derived-variable rules are documented here. This file is intended to mirror the OSF amendment log.

## [1.0.0] - 2026-04-19

### Added

- Created `extraction_codebook_v1.csv` with 75 standardised charting fields for the metadata-only scoping review.
- Created `derived_variables.py` to compute:
  - gap coverage and per-study `gap_score`
  - Methodological Rigour Index (`mri`) and normalised MRI
  - Fairness Reporting Index (`fri`)
  - Privacy and Governance Index (`pgi`)
  - Modality-Diversity Index (`mdi`) and `is_multimodal`
  - non-exclusive task category flags
  - task-by-gap matrix
  - temporal task-share summaries
  - model-family concentration (`mfc`)
  - processing-stage deduplication keys
  - automated-triage sensitivity, specificity, and Cohen's kappa when validation columns are present

### Reproducibility Notes

- Missing values are not imputed.
- Binary fields accept `0/1`, `yes/no`, `true/false`, and common include/exclude encodings.
- Aggregate statistics report effective denominators where applicable.
- Input CSV SHA-256 checksums are written to the summary JSON output.

### Compatibility

- Companion specification: `Supplementary Specification S1: Derived Variables and Indices`.
- Codebook version: `extraction_codebook_v1.csv`.
- Derivation script version: `derived_variables.py` v1.0.0.
