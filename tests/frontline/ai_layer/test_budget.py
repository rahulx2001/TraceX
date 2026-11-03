"""Spend-ledger pricing must not trip on ordinary prose.  [AI-LAYER]"""

from __future__ import annotations

import pytest

from src.ai_layer.budget import bound, limit_micros, reserve, status


def _payload(text: str) -> dict:
    return {
        "model": "muse-spark-1.3",
        "messages": [{"role": "user", "content": text}],
        "max_tokens": 1000,
    }


def test_bound_ignores_media_words_in_prose():
    # A complaint mentioning the audio system is still a text call.
    cost = bound(_payload("The rear audio display went blank and the fuel gauge failed."))
    assert isinstance(cost, int) and cost > 0


def test_bound_still_rejects_media_urls():
    with pytest.raises(ValueError, match="unpriced media"):
        bound(_payload("see data:video/mp4;base64,AAAA"))


def test_allowance_defaults_to_30_and_honors_operator_increase(monkeypatch):
    monkeypatch.delenv("META_BUDGET_USD", raising=False)
    assert limit_micros() == 30_000_000
    monkeypatch.setenv("META_BUDGET_USD", "50")
    assert limit_micros() == 50_000_000


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_allowance_fails_closed(monkeypatch, value):
    monkeypatch.setenv("META_BUDGET_USD", value)
    with pytest.raises(ValueError):
        limit_micros()


def test_allowance_increase_preserves_existing_reservations(tmp_path, monkeypatch):
    from src.ai_layer.meta_client import MetaError
    monkeypatch.setenv("META_BUDGET_PATH", str(tmp_path / "budget.sqlite"))
    payload = _payload("Fictional report")
    cost = bound(payload)
    monkeypatch.setenv("META_BUDGET_USD", str(cost / 1_000_000))
    reserve(payload)
    with pytest.raises(MetaError, match="budget_exceeded"):
        reserve(payload)
    monkeypatch.setenv("META_BUDGET_USD", "50")
    before = status()["reserved_upper_bound_usd"]
    reserve(payload)
    assert status()["reserved_upper_bound_usd"] == before * 2
    assert status()["limit_usd"] == 50
