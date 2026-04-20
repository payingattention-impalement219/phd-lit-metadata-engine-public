import json

import pandas as pd

from protocol.derived_variables import (
    compute_derived_variables,
    coverage_by_gap,
    model_family_concentration,
    write_outputs,
)


def test_compute_core_indices():
    frame = pd.DataFrame(
        [
            {
                "record_id": "s1",
                "title": "Example metadata study",
                "publication_year": 2024,
                "task_primary": "diagnosis",
                "task_secondary": "severity; explainability",
                "gap_prognosis": 1,
                "gap_generative": 0,
                "gap_multimodal": 1,
                "gap_fairness": 0,
                "gap_federated": 0,
                "external_validation": 1,
                "kfold_cv": 1,
                "confidence_intervals": 0,
                "comparator_model": 1,
                "human_vs_ai_comparison": 0,
                "error_analysis": 1,
                "code_availability": 0,
                "sample_size_justification": 0,
                "skin_tone_subgroup_performance": 1,
                "ethnicity_subgroup_performance": 0,
                "sex_subgroup_performance": 1,
                "age_subgroup_performance": 0,
                "fairness_metric_reported": 0,
                "federated_training": 0,
                "privacy_technique": 0,
                "governance_framework": 1,
                "ethics_approval_reported": 1,
                "modality_domain_specific_imaging": 1,
                "modality_standard_photograph": 1,
                "modality_specialist_imaging": 0,
                "modality_contextual_image": 0,
                "modality_histopathology": 0,
                "modality_lab_biomarker": 0,
                "modality_ehr_text": 0,
                "modality_structured_clinical": 0,
                "modality_genomic": 0,
                "model_family": "cnn",
            }
        ]
    )

    derived = compute_derived_variables(frame)

    assert derived.loc[0, "gap_score"] == 2
    assert derived.loc[0, "mri"] == 4
    assert derived.loc[0, "mri_normalised"] == 0.5
    assert derived.loc[0, "fri"] == 2
    assert derived.loc[0, "pgi"] == 2
    assert derived.loc[0, "mdi"] == 2
    assert derived.loc[0, "is_multimodal"] == 1
    assert derived.loc[0, "task_diagnosis"] == 1
    assert derived.loc[0, "task_severity"] == 1
    assert derived.loc[0, "task_explainability"] == 1


def test_coverage_and_model_concentration():
    frame = pd.DataFrame(
        [
            {"gap_prognosis": 1, "gap_generative": 0, "model_family": "cnn"},
            {"gap_prognosis": 0, "gap_generative": 1, "model_family": "cnn"},
            {"gap_prognosis": 1, "gap_generative": 1, "model_family": "transformer"},
        ]
    )
    derived = compute_derived_variables(frame)

    coverage = coverage_by_gap(derived).set_index("gap")
    assert coverage.loc["prognosis", "coverage"] == 2 / 3
    assert coverage.loc["generative", "coverage"] == 2 / 3
    assert model_family_concentration(derived)["mfc"] == (2 / 3) ** 2 + (1 / 3) ** 2


def test_write_outputs(tmp_path):
    input_path = tmp_path / "charting.csv"
    output_prefix = tmp_path / "derived" / "test"
    pd.DataFrame(
        [
            {
                "record_id": "s1",
                "title": "Example metadata study",
                "publication_year": 2025,
                "task_primary": "classification",
                "gap_prognosis": 0,
                "gap_generative": 0,
                "gap_multimodal": 0,
                "gap_fairness": 0,
                "gap_federated": 0,
            }
        ]
    ).to_csv(input_path, index=False)

    write_outputs(input_path, output_prefix)

    assert output_prefix.with_suffix(".derived.csv").exists()
    summary_path = output_prefix.with_suffix(".summary.json")
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["n_rows"] == 1
    assert len(summary["input_sha256"]) == 64
