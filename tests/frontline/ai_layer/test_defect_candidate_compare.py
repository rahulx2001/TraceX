from copy import deepcopy

import pytest

from scripts.defect_candidate_compare import compare_scores


def score(predictions):
    rows = [{"sample_id": f"S{i:03d}", "record_id": f"{i}|TEST", "component": "TEST",
             "human_label": "a", "human_reason": "ok", "model_label": label,
             "model_status": "ok" if label is not None else "missing"}
            for i, label in enumerate(predictions)]
    correct = sum(label == "a" for label in predictions)
    return {"sample_size": 300, "labelled": 300, "invalid_human_labels": 0,
            "rows": rows, "correct": correct, "model_missing": predictions.count(None),
            "accuracy": correct / 300, "accuracy_denominator": 300}


def test_missing_candidate_prediction_counts_as_worsening_and_false_negative():
    result = compare_scores(score(["a"] * 300), score([None] + ["a"] * 299))
    assert result["candidate_accuracy"]["numerator"] == 299
    assert result["candidate_accuracy"]["denominator"] == 300
    assert result["paired_counts"]["worsened"] == {"numerator": 1, "denominator": 300}
    assert result["paired_counts"]["improved"]["numerator"] == 0
    assert result["paired_counts"]["tied"]["numerator"] == 299
    assert result["paired_accuracy_difference"]["value"] == pytest.approx(-1 / 300)
    assert result["missing_predictions"]["candidate"] == {"numerator": 1, "denominator": 300}
    label = result["common_label_macro_f1"]["candidate"]["per_label"][0]
    assert (label["support"], label["tp"], label["fn"]) == (300, 299, 1)


def test_common_macro_keeps_prediction_only_label_when_candidate_stops_using_it():
    result = compare_scores(score(["a"] * 150 + ["b"] * 150), score(["a"] * 300))
    common = result["common_label_macro_f1"]
    assert common["labels"] == ["a", "b"]
    assert common["baseline"]["value"] == pytest.approx(1 / 3)
    assert common["candidate"]["value"] == 0.5
    assert result["own_union_macro_f1_diagnostics"]["candidate"]["value"] == 1
    assert result["own_union_macro_f1_diagnostics"]["candidate"]["denominator"] == 1
    assert result["paired_counts"]["improved"]["numerator"] == 150
    assert result["target"]["met"] is True


def test_pairs_align_by_identity_and_zero_difference_has_zero_bootstrap_interval():
    baseline = score(["a"] * 270 + ["b"] * 30)
    candidate = deepcopy(baseline)
    candidate["rows"].reverse()
    result = compare_scores(baseline, candidate)
    assert result["paired_rows"] == 300
    assert result["paired_accuracy_difference"]["ci95"] == [0, 0]
    assert result["target"]["required_correct"] == 270
    assert result["target"]["met"] is True


@pytest.mark.parametrize("corruption", ["drop", "duplicate_sample", "duplicate_record", "record_identity", "gold_label"])
def test_rejects_dropped_duplicate_or_changed_gold_rows(corruption):
    baseline = score(["a"] * 300)
    candidate = deepcopy(baseline)
    if corruption == "drop":
        candidate["rows"].pop()
    elif corruption == "duplicate_sample":
        candidate["rows"][1]["sample_id"] = candidate["rows"][0]["sample_id"]
    elif corruption == "duplicate_record":
        candidate["rows"][1]["record_id"] = candidate["rows"][0]["record_id"]
    elif corruption == "record_identity":
        candidate["rows"][0]["record_id"] = "foreign|TEST"
    else:
        candidate["rows"][0]["human_label"] = "b"
        candidate["rows"][0]["model_label"] = "b"
    with pytest.raises(ValueError):
        compare_scores(baseline, candidate)
