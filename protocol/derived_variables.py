"""Compute derived variables for a metadata-only scoping or mapping review.

Inputs
------
A frozen charting CSV that follows ``extraction_codebook_v1.csv``.

Outputs
-------
1. Row-level derived variables CSV.
2. Aggregate summary JSON.
3. Optional Excel workbook with row-level and aggregate sheets.

The script is deterministic and performs no imputation. Missing values are
excluded pairwise from aggregate statistics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


GAP_FIELDS = ["gap_prognosis", "gap_generative", "gap_multimodal", "gap_fairness", "gap_federated"]
MRI_FIELDS = [
    "external_validation",
    "kfold_cv",
    "confidence_intervals",
    "comparator_model",
    "human_vs_ai_comparison",
    "error_analysis",
    "code_availability",
    "sample_size_justification",
]
FRI_FIELDS = [
    "skin_tone_subgroup_performance",
    "ethnicity_subgroup_performance",
    "sex_subgroup_performance",
    "age_subgroup_performance",
    "fairness_metric_reported",
]
PGI_FIELDS = ["federated_training", "privacy_technique", "governance_framework", "ethics_approval_reported"]
MODALITY_FIELDS = [
    "modality_domain_specific_imaging",
    "modality_standard_photograph",
    "modality_specialist_imaging",
    "modality_contextual_image",
    "modality_histopathology",
    "modality_lab_biomarker",
    "modality_ehr_text",
    "modality_structured_clinical",
    "modality_genomic",
]

COLUMN_ALIASES = {
    "clinical_task_primary": "task_primary",
    "clinical_task_secondary": "task_secondary",
}
MODEL_FAMILIES = ["cnn", "transformer", "gan", "diffusion", "classical_ml", "ensemble", "hybrid", "other"]
TASK_CATEGORIES = [
    "diagnosis",
    "severity",
    "segmentation",
    "monitoring",
    "optimisation",
    "prognosis",
    "explainability",
    "generative",
    "fairness_eval",
    "federated",
]


TASK_SYNONYMS = {
    "diagnosis": {"diagnosis", "diagnostic", "classification", "detection", "identification"},
    "severity": {"severity", "grading", "scale", "score", "assessment", "severity_grading", "severity assessment"},
    "segmentation": {"segmentation", "segment"},
    "monitoring": {"monitoring", "follow-up", "follow up", "tracking"},
    "optimisation": {"optimisation", "optimization", "treatment optimisation", "treatment optimization"},
    "prognosis": {"prognosis", "trajectory", "progression", "prediction"},
    "explainability": {"explainability", "explainable", "interpretability", "grad-cam", "lime", "shap"},
    "generative": {"generative", "gan", "diffusion", "synthetic", "vae"},
    "fairness_eval": {"fairness", "bias", "subgroup", "equity"},
    "federated": {"federated", "privacy-preserving", "privacy preserving"},
}


def read_charting_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_binary(series: pd.Series) -> pd.Series:
    """Coerce common binary encodings to nullable 0/1 floats."""
    true_values = {"1", "true", "yes", "y", "included", "include"}
    false_values = {"0", "false", "no", "n", "excluded", "exclude"}

    def convert(value: object) -> float:
        if pd.isna(value):
            return math.nan
        if isinstance(value, bool):
            return float(value)
        text = str(value).strip().lower()
        if text in true_values:
            return 1.0
        if text in false_values:
            return 0.0
        try:
            number = float(text)
        except ValueError:
            return math.nan
        return 1.0 if number >= 1 else 0.0

    return series.map(convert)


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output


def apply_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    for old_name, new_name in COLUMN_ALIASES.items():
        if old_name in output.columns and new_name not in output.columns:
            output[new_name] = output[old_name]
    return output


def sum_binary_fields(df: pd.DataFrame, columns: list[str], output_name: str) -> pd.Series:
    available = ensure_columns(df, columns)
    coerced = pd.DataFrame({column: as_binary(available[column]) for column in columns})
    return coerced.fillna(0).sum(axis=1).rename(output_name)


def split_tasks(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    return {item.strip().lower() for item in re.split(r"[;,|]", str(value)) if item.strip()}


def assign_task_categories(row: pd.Series) -> list[str]:
    raw_tasks = split_tasks(row.get("task_primary")) | split_tasks(row.get("task_secondary"))
    text = " ".join(str(item) for item in raw_tasks).lower()
    assigned: set[str] = set()
    for category, synonyms in TASK_SYNONYMS.items():
        if category in raw_tasks or any(term in text for term in synonyms):
            assigned.add(category)

    if as_binary(pd.Series([row.get("prognosis_or_trajectory_outcome")])).iloc[0] == 1:
        assigned.add("prognosis")
    if as_binary(pd.Series([row.get("treatment_response_outcome")])).iloc[0] == 1:
        assigned.add("monitoring")
    if as_binary(pd.Series([row.get("gap_generative")])).iloc[0] == 1:
        assigned.add("generative")
    if as_binary(pd.Series([row.get("gap_fairness")])).iloc[0] == 1:
        assigned.add("fairness_eval")
    if as_binary(pd.Series([row.get("gap_federated")])).iloc[0] == 1:
        assigned.add("federated")

    return sorted(assigned)


def compute_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    output = apply_column_aliases(df)
    output = ensure_columns(output, GAP_FIELDS + MRI_FIELDS + FRI_FIELDS + PGI_FIELDS + MODALITY_FIELDS)

    output["gap_score"] = sum_binary_fields(output, GAP_FIELDS, "gap_score")
    output["mri"] = sum_binary_fields(output, MRI_FIELDS, "mri")
    output["mri_normalised"] = output["mri"] / len(MRI_FIELDS)
    output["fri"] = sum_binary_fields(output, FRI_FIELDS, "fri")
    output["pgi"] = sum_binary_fields(output, PGI_FIELDS, "pgi")
    output["mdi"] = sum_binary_fields(output, MODALITY_FIELDS, "mdi")
    output["is_multimodal"] = (output["mdi"] >= 2).astype(int)

    output["task_categories"] = output.apply(assign_task_categories, axis=1).map(lambda items: "; ".join(items))
    for task in TASK_CATEGORIES:
        output[f"task_{task}"] = output["task_categories"].map(lambda value, t=task: int(t in split_tasks(value)))

    output["dedupe_key_processing"] = output.apply(deduplication_key, axis=1)
    return output


def deduplication_key(row: pd.Series) -> str:
    doi = str(row.get("doi", "") or "").strip().lower()
    doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if doi and doi != "nan":
        return f"doi:{doi}"
    title = re.sub(r"[^a-z0-9]+", " ", str(row.get("title", "") or "").lower()).strip()
    year = str(row.get("publication_year", "") or "").strip()
    return f"title_year:{title}:{year}"


def coverage_by_gap(derived: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for field in GAP_FIELDS:
        values = as_binary(derived[field]) if field in derived.columns else pd.Series(dtype=float)
        rows.append(
            {
                "gap": field.removeprefix("gap_"),
                "coverage": values.mean(skipna=True),
                "n_effective": int(values.notna().sum()),
                "n_addressing_gap": int(values.fillna(0).sum()),
            }
        )
    return pd.DataFrame(rows)


def task_gap_matrix(derived: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for task in TASK_CATEGORIES:
        task_mask = derived.get(f"task_{task}", pd.Series(0, index=derived.index)).fillna(0).astype(bool)
        for gap in GAP_FIELDS:
            gap_values = as_binary(derived[gap]) if gap in derived.columns else pd.Series(0, index=derived.index)
            rows.append(
                {
                    "task": task,
                    "gap": gap.removeprefix("gap_"),
                    "cell_count": int(gap_values[task_mask].fillna(0).sum()),
                    "task_n": int(task_mask.sum()),
                }
            )
    return pd.DataFrame(rows)


def temporal_task_share(derived: pd.DataFrame) -> pd.DataFrame:
    if "publication_year" not in derived.columns:
        return pd.DataFrame(columns=["publication_year", "task", "n_year", "task_n", "share"])
    years = pd.to_numeric(derived["publication_year"], errors="coerce")
    rows = []
    for year in sorted(years.dropna().astype(int).unique()):
        year_mask = years.eq(year)
        n_year = int(year_mask.sum())
        for task in TASK_CATEGORIES:
            task_n = int(derived.loc[year_mask, f"task_{task}"].fillna(0).sum()) if f"task_{task}" in derived else 0
            rows.append({"publication_year": year, "task": task, "n_year": n_year, "task_n": task_n, "share": task_n / n_year if n_year else math.nan})
    return pd.DataFrame(rows)


def model_family_concentration(derived: pd.DataFrame) -> dict[str, float | int]:
    if "model_family" not in derived.columns:
        return {"mfc": math.nan, "n_effective": 0}
    families = derived["model_family"].dropna().astype(str).str.lower().replace({"": pd.NA, "nan": pd.NA}).dropna()
    n = len(families)
    if not n:
        return {"mfc": math.nan, "n_effective": 0}
    shares = families.value_counts(normalize=True)
    return {"mfc": float((shares**2).sum()), "n_effective": int(n)}


def automated_triage_agreement(df: pd.DataFrame) -> dict[str, float | int]:
    required = {"automated_triage_flag", "human_screening_flag"}
    if not required.issubset(df.columns):
        return {"n_effective": 0, "sensitivity": math.nan, "specificity": math.nan, "kappa": math.nan}
    auto = as_binary(df["automated_triage_flag"])
    human = as_binary(df["human_screening_flag"])
    valid = auto.notna() & human.notna()
    auto = auto[valid].astype(int)
    human = human[valid].astype(int)
    n = int(valid.sum())
    if n == 0:
        return {"n_effective": 0, "sensitivity": math.nan, "specificity": math.nan, "kappa": math.nan}
    tp = int(((auto == 1) & (human == 1)).sum())
    tn = int(((auto == 0) & (human == 0)).sum())
    human_pos = int((human == 1).sum())
    human_neg = int((human == 0).sum())
    sensitivity = tp / human_pos if human_pos else math.nan
    specificity = tn / human_neg if human_neg else math.nan
    po = float((auto == human).mean())
    pe = float(((auto == 1).mean() * (human == 1).mean()) + ((auto == 0).mean() * (human == 0).mean()))
    kappa = (po - pe) / (1 - pe) if pe != 1 else math.nan
    return {"n_effective": n, "sensitivity": sensitivity, "specificity": specificity, "kappa": kappa}


def aggregate_summary(input_path: Path, derived: pd.DataFrame) -> dict[str, object]:
    return {
        "input_file": str(input_path),
        "input_sha256": sha256_file(input_path),
        "n_rows": int(len(derived)),
        "coverage_by_gap": coverage_by_gap(derived).to_dict(orient="records"),
        "gap_score": {
            "mean": float(derived["gap_score"].mean(skipna=True)),
            "median": float(derived["gap_score"].median(skipna=True)),
            "iqr": float(derived["gap_score"].quantile(0.75) - derived["gap_score"].quantile(0.25)),
            "n_effective": int(derived["gap_score"].notna().sum()),
        },
        "mri": {
            "mean": float(derived["mri"].mean(skipna=True)),
            "median": float(derived["mri"].median(skipna=True)),
            "n_effective": int(derived["mri"].notna().sum()),
        },
        "fri": {
            "mean": float(derived["fri"].mean(skipna=True)),
            "median": float(derived["fri"].median(skipna=True)),
            "n_effective": int(derived["fri"].notna().sum()),
        },
        "pgi": {
            "mean": float(derived["pgi"].mean(skipna=True)),
            "median": float(derived["pgi"].median(skipna=True)),
            "n_effective": int(derived["pgi"].notna().sum()),
        },
        "mdi": {
            "mean": float(derived["mdi"].mean(skipna=True)),
            "median": float(derived["mdi"].median(skipna=True)),
            "multimodal_n": int(derived["is_multimodal"].sum()),
            "n_effective": int(derived["mdi"].notna().sum()),
        },
        "model_family_concentration": model_family_concentration(derived),
        "automated_triage_agreement": automated_triage_agreement(derived),
    }


def write_outputs(input_path: Path, output_prefix: Path) -> None:
    df = read_charting_csv(input_path)
    derived = compute_derived_variables(df)
    summary = aggregate_summary(input_path, derived)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    derived_path = output_prefix.with_suffix(".derived.csv")
    summary_path = output_prefix.with_suffix(".summary.json")
    workbook_path = output_prefix.with_suffix(".derived.xlsx")

    derived.to_csv(derived_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        derived.to_excel(writer, sheet_name="derived_records", index=False)
        coverage_by_gap(derived).to_excel(writer, sheet_name="coverage_by_gap", index=False)
        task_gap_matrix(derived).to_excel(writer, sheet_name="task_gap_matrix", index=False)
        temporal_task_share(derived).to_excel(writer, sheet_name="temporal_task_share", index=False)
        pd.DataFrame([model_family_concentration(derived)]).to_excel(writer, sheet_name="model_family_concentration", index=False)
        pd.DataFrame([automated_triage_agreement(derived)]).to_excel(writer, sheet_name="triage_agreement", index=False)

    print(f"Wrote {derived_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {workbook_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute derived variables for a metadata-only scoping or mapping review.")
    parser.add_argument("input_csv", type=Path, help="Frozen extracted charting CSV.")
    parser.add_argument("--output-prefix", type=Path, default=Path("reports/derived_variables/derived_variables"), help="Output prefix without extension.")
    args = parser.parse_args()
    write_outputs(args.input_csv, args.output_prefix)


if __name__ == "__main__":
    main()
