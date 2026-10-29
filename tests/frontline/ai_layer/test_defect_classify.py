"""The classify prompt must state its exact JSON shape.

Backends with weak schema enforcement (Baseten, strict:false) follow the
prompt's own words, so the shape cannot live in the schema alone.
"""

from __future__ import annotations

from scripts.defect_classify import PROMPT_VERSION, make_prompt


def test_make_prompt_states_exact_json_shape():
    labels = [
        {"id": "tank_assembly_leak", "label": "tank leak", "definition": "d"},
        {"id": "other_unclear", "label": "other/unclear", "definition": "vague"},
    ]
    text = make_prompt(
        "FUEL SYSTEM",
        labels,
        [{"text": "fuel smell near tank"}, {"text": "gauge wrong"}],
    )
    assert PROMPT_VERSION == "defect-cls-v2"
    for token in ('"items"', '"record_id"', '"label_id"', '"confidence"', '"evidence"', '"c1"', '"c2"'):
        assert token in text
