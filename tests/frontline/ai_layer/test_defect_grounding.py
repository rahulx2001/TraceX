import pytest

from scripts.defect_grounding import (
    GROUNDING_STATUSES, make_prompt, make_schema, validate_grounded_output,
)


ALLOWED = ["fuel_pump_failure", "other_unclear"]
TEXT = "The fuel pump failed and was replaced."


def proposal(**changes):
    return {
        "record_id": "c1", "label_id": "fuel_pump_failure", "confidence": 0.8,
        "evidence": TEXT, "part_evidence": "fuel pump", "mode_evidence": "failed",
        "grounding_status": "specific_supported", **changes,
    }


def validate(row, text=TEXT):
    return validate_grounded_output({"items": [row]}, items=[{"text": text}], allowed_ids=ALLOWED)


def test_supported_part_and_mode_accept_whitespace_normalized_full_quotes():
    rows, reason = validate(proposal(), text="The fuel pump\nfailed and was replaced.")
    assert reason is None
    assert rows[0]["label_id"] == "fuel_pump_failure"
    assert rows[0]["part_evidence_verbatim"] is True
    assert rows[0]["mode_evidence_verbatim"] is True
    assert rows[0]["confidence"] == 0.8


def test_fabricated_quote_suffix_beyond_first_120_characters_rejects_batch():
    source = TEXT + " " + "x" * 130
    quote = source + " invented conclusion"
    assert 120 < len(quote) <= 200
    rows, reason = validate(proposal(evidence=quote), text=source)
    assert rows == []
    assert reason == "nonverbatim_specific_evidence:evidence:c1"


@pytest.mark.parametrize("status", [
    "symptom_only", "uncertain_cause", "negated", "wrong_component",
    "out_of_taxonomy", "multiple_causes",
])
def test_unsupported_specific_proposals_abstain_and_preserve_audit_fields(status):
    source = "The fuel pump was normal; the vehicle stalled."
    row = proposal(evidence="the vehicle stalled", part_evidence="fuel pump",
                   mode_evidence="", grounding_status=status)
    rows, reason = validate(row, text=source)
    assert reason is None
    result = rows[0]
    assert result["label_id"] == "other_unclear"
    assert result["proposed_label_id"] == "fuel_pump_failure"
    assert result["confidence"] is None
    assert result["proposed_confidence"] == 0.8
    assert result["grounding_status"] == status
    assert result["abstention_reason"] == f"grounding_status:{status}"
    assert result["part_evidence"] == row["part_evidence"]


def test_missing_part_or_mode_evidence_cannot_support_specific_label():
    rows, reason = validate(proposal(mode_evidence=""))
    assert rows == []
    assert reason == "missing_specific_evidence:mode_evidence:c1"


def test_duplicate_record_identity_rejects_batch():
    rows, reason = validate_grounded_output(
        {"items": [proposal(), proposal()]}, items=[{"text": TEXT}, {"text": TEXT}],
        allowed_ids=ALLOWED,
    )
    assert rows == []
    assert reason == "duplicate_record_id:c1"


def test_out_of_taxonomy_label_is_rejected_even_with_abstention_status():
    rows, reason = validate(proposal(label_id="unlisted_part", grounding_status="out_of_taxonomy"))
    assert rows == []
    assert reason == "label_not_allowed:unlisted_part"


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_invalid_confidence_rejects_batch(confidence):
    rows, reason = validate(proposal(confidence=confidence))
    assert rows == []
    assert reason.startswith("bad_confidence")


def test_other_unclear_allows_insufficient_detail_without_fabricating_quotes():
    rows, reason = validate(proposal(label_id="other_unclear", evidence="insufficient detail",
                                   part_evidence="", mode_evidence="", grounding_status="uncertain_cause"))
    assert reason is None
    assert rows[0]["label_id"] == "other_unclear"
    assert rows[0]["evidence_verbatim"] is False


def test_abstaining_specific_proposal_cannot_preserve_fabricated_main_quote():
    rows, reason = validate(proposal(grounding_status="symptom_only", evidence="Invented symptom"))
    assert rows == []
    assert reason == "nonverbatim_other_evidence:c1"


@pytest.mark.parametrize("label", ALLOWED)
@pytest.mark.parametrize("field", ["part_evidence", "mode_evidence"])
def test_every_nonempty_abstention_part_and_mode_quote_must_be_verbatim(label, field):
    row = proposal(label_id=label, grounding_status="uncertain_cause",
                   evidence="insufficient detail", **{field: "Invented source detail"})
    rows, reason = validate(row)
    assert rows == []
    assert reason == f"nonverbatim_abstention_evidence:{field}:c1"


def test_other_unclear_cannot_claim_specific_supported_status():
    rows, reason = validate(proposal(label_id="other_unclear"))
    assert rows == []
    assert reason == "other_cannot_be_specific_supported:c1"


def test_other_unclear_rejects_fabricated_main_quote():
    rows, reason = validate(proposal(label_id="other_unclear", grounding_status="uncertain_cause",
                                   evidence="Invented source detail", part_evidence="", mode_evidence=""))
    assert rows == []
    assert reason == "nonverbatim_other_evidence:c1"


def test_prompt_excludes_label_frequencies_and_recall_examples():
    labels = [{"id": "fuel_pump_failure", "label": "FUEL PUMP / failure",
               "leaf": "FUEL PUMP", "mode": "failure", "definition": "Named pump failure",
               "support": 987654, "examples": ["PRIVATE_EXAMPLE_NOT_FOR_PROMPT"]}]
    prompt = make_prompt("FUEL SYSTEM", labels, [{"text": TEXT}])
    assert "FUEL PUMP" in prompt and "Named pump failure" in prompt
    assert "987654" not in prompt and "PRIVATE_EXAMPLE_NOT_FOR_PROMPT" not in prompt


def test_schema_bounds_complete_batch_and_full_quotes():
    schema = make_schema(2, ALLOWED)
    items = schema["properties"]["items"]
    fields = items["items"]["properties"]
    assert items["minItems"] == items["maxItems"] == 2
    assert fields["record_id"]["enum"] == ["c1", "c2"]
    assert fields["grounding_status"]["enum"] == list(GROUNDING_STATUSES)
    assert all(fields[key]["maxLength"] == 200 for key in ("evidence", "part_evidence", "mode_evidence"))
