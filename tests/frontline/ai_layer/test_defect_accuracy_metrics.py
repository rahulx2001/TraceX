import pandas as pd
import pytest

from scripts.defect_accuracy import build_metrics


def metrics(tmp_path, labels, predictions, statuses=None):
    statuses = statuses or ["ok"] * len(labels)
    sample = pd.DataFrame([
        {
            "sample_id": f"S{i}", "odino": str(i), "component": "TEST COMPONENT",
            "allowed_label_ids": "a;b;other_unclear",
            "allowed_label_text": "a=Defect A;b=Defect B;other_unclear=other/unclear",
            "label": label,
        }
        for i, label in enumerate(labels)
    ])
    classifier = pd.DataFrame([
        {
            "record_id": f"{i}|TEST COMPONENT", "label_id": prediction,
            "status": statuses[i], "component": "TEST COMPONENT",
            "model": "test-model", "prompt_version": "test-v1", "taxonomy_sha256": "test-taxonomy",
        }
        for i, prediction in enumerate(predictions) if prediction is not None
    ])
    csv_path = tmp_path / "sample.csv"
    clf_path = tmp_path / "classifications.parquet"
    manifest_path = tmp_path / "manifest.json"
    sample.to_csv(csv_path, index=False)
    # build_metrics receives the frame directly and hashes this fixture file.
    clf_path.write_bytes(b"test classifier fixture")
    manifest_path.write_text("{}")
    return build_metrics(sample, classifier, manifest={}, csv_path=csv_path,
                         clf_path=clf_path, manifest_path=manifest_path)


@pytest.mark.parametrize("missing_mode", ["absent", "error"])
def test_missing_prediction_remains_in_denominators_and_confusion(tmp_path, missing_mode):
    predictions = ["a", None if missing_mode == "absent" else "a", "other_unclear"]
    result = metrics(tmp_path, ["a", "a", "other_unclear"], predictions,
                     statuses=["ok", "error", "ok"])
    assert result["accuracy"] == pytest.approx(2 / 3)
    assert result["accuracy_all_labelled"] == pytest.approx(2 / 3)
    assert result["accuracy_numerator"] == 2
    assert result["accuracy_denominator"] == 3
    assert result["accuracy_available_predictions"] == 1
    assert result["specific_accuracy"] == 0.5
    assert result["specific_n"] == 2
    assert result["model_missing"] == 1
    label = next(row for row in result["per_label"] if row["label_id"] == "a")
    assert (label["support"], label["predicted"], label["tp"], label["fn"]) == (2, 1, 1, 1)
    assert label["precision"] == 1
    assert label["recall"] == 0.5
    assert label["recall_denominator"] == 2
    assert label["f1"] == pytest.approx(2 / 3)
    assert result["confusion"]["a"]["__missing_prediction__"] == 1
    assert sum(sum(row.values()) for row in result["confusion"].values()) == 3
    assert result["macro_f1"] == pytest.approx((2 / 3 + 1) / 2)


def test_all_correct_retains_counts_and_reports_intervals(tmp_path):
    result = metrics(tmp_path, ["a", "b", "other_unclear"], ["a", "b", "other_unclear"])
    assert result["accuracy"] == result["specific_accuracy"] == result["macro_f1"] == 1
    assert (result["accuracy_numerator"], result["accuracy_denominator"]) == (3, 3)
    assert result["model_missing"] == 0
    assert 0 < result["accuracy_ci95"][0] < 1
    assert result["accuracy_ci95"][1] == pytest.approx(1)
    assert result["macro_f1_ci95"] == [1, 1]
    for label in result["per_label"]:
        assert label["f1_ci95"] == [1, 1]
        assert label["precision_ci95"][0] < label["precision"] <= label["precision_ci95"][1]
        assert label["recall_ci95"][0] < label["recall"] <= label["recall_ci95"][1]


def test_prediction_only_label_counts_in_union_macro_f1(tmp_path):
    result = metrics(tmp_path, ["a", "a"], ["b", "a"])
    assert result["macro_f1_label_count"] == 2
    assert result["macro_f1"] == pytest.approx(1 / 3)
    assert result["macro_f1_human_supported_label_count"] == 1
    assert result["macro_f1_human_supported"] == pytest.approx(2 / 3)
    prediction_only = next(row for row in result["per_label"] if row["label_id"] == "b")
    assert (prediction_only["support"], prediction_only["fp"], prediction_only["f1"]) == (0, 1, 0)
