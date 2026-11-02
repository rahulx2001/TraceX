from copy import deepcopy

import pytest

from scripts.defect_grounded_row_validation import first_valid_predictions, recover_batch


SOURCE = [{"record_id": "R1", "text": "The fuel pump failed."},
          {"record_id": "R2", "text": "The wiring failed."}]
ALLOWED = ["a", "b", "other_unclear"]


def row(local, text, part):
    return {"record_id": local, "label_id": "a", "confidence": 0.8,
            "evidence": text, "part_evidence": part, "mode_evidence": "failed",
            "grounding_status": "specific_supported"}


def batch():
    return {"items": [row("c1", SOURCE[0]["text"], "fuel pump"),
                      row("c2", SOURCE[1]["text"], "wiring")]}


def test_one_invalid_row_does_not_remove_an_independently_valid_row():
    raw = batch()
    raw["items"][1]["mode_evidence"] = "exploded"
    original = deepcopy(raw)
    result = recover_batch(raw, items=SOURCE, allowed_ids=ALLOWED)
    assert [value["record_id"] for value in result["items"]] == ["c1"]
    assert result["batch_error"] is None
    assert "nonverbatim" in result["row_errors"]["c2"]
    assert raw == original


def test_fabricated_quote_suffix_rejects_only_that_row_without_quote_rewriting():
    raw = batch()
    raw["items"][0]["evidence"] += " It exploded."
    result = recover_batch(raw, items=SOURCE, allowed_ids=ALLOWED)
    assert [value["record_id"] for value in result["items"]] == ["c2"]
    assert "nonverbatim_specific_evidence" in result["row_errors"]["c1"]
    assert raw["items"][0]["evidence"].endswith("It exploded.")


@pytest.mark.parametrize("corruption", ["duplicate", "wrong_count", "missing_identity"])
def test_ambiguous_or_incomplete_mapping_rejects_the_entire_batch(corruption):
    raw = batch()
    if corruption == "duplicate":
        raw["items"][1]["record_id"] = "c1"
    elif corruption == "wrong_count":
        raw["items"].pop()
    else:
        raw["items"][1]["record_id"] = "c3"
    result = recover_batch(raw, items=SOURCE, allowed_ids=ALLOWED)
    assert result["items"] == []
    assert result["batch_error"] is not None
    assert set(result["row_errors"]) == {"c1", "c2"}


def test_first_valid_attempt_wins_and_later_confidence_or_label_does_not_replace_it():
    first = batch()
    first["items"][1]["evidence"] = "not in source"
    second = batch()
    second["items"][0]["label_id"] = "b"
    second["items"][0]["confidence"] = 1.0
    attempts = [(1, {"phase": "evaluation", "batch_key": "K", "raw": first}),
                (2, {"phase": "evaluation", "batch_key": "K", "raw": second})]
    selected, errors, counts = first_valid_predictions(attempts, [{"key": "K", "records": SOURCE, "allowed_ids": ALLOWED}])
    assert selected["R1"]["label_id"] == "a"
    assert selected["R1"]["source_attempt_line"] == 1
    assert selected["R2"]["source_attempt_line"] == 2
    assert errors["R2"][0]["attempt_line"] == 1
    assert counts["K"] == 2


def test_absent_raw_response_leaves_every_record_missing():
    selected, errors, counts = first_valid_predictions(
        [(1, {"phase": "evaluation", "batch_key": "K", "error": "schema_failure"})],
        [{"key": "K", "records": SOURCE, "allowed_ids": ALLOWED}])
    assert selected == {}
    assert set(errors) == {"R1", "R2"}
    assert counts["K"] == 1


def test_more_than_one_retry_is_rejected():
    attempts = [(i, {"phase": "evaluation", "batch_key": "K", "raw": batch()}) for i in range(1, 4)]
    with pytest.raises(ValueError, match="initial plus one"):
        first_valid_predictions(attempts, [{"key": "K", "records": SOURCE, "allowed_ids": ALLOWED}])
