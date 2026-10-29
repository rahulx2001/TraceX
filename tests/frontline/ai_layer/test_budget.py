"""Spend-ledger pricing must not trip on ordinary prose.  [AI-LAYER]"""

from __future__ import annotations

import pytest

from src.ai_layer.budget import bound


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
