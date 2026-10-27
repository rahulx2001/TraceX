"""Consent text for real complaint collection.  [REAL-DATA]

The collector page renders ``CONSENT_TEXT`` verbatim. Every stored record keeps
the version and SHA-256 of the text the person actually agreed to, so a later
wording change cannot silently re-label old consent.

Do not edit ``CONSENT_TEXT`` in place after collection starts. Add a new
version to ``CONSENT_REGISTRY`` and keep the old one, so old records remain
verifiable.
"""
from __future__ import annotations

import hashlib

CONSENT_VERSION = "real-hindi-v1"

CONSENT_TEXT = """Purpose
I am testing a safety system that reads vehicle complaints. Real stories help me check whether it understands Hindi, Hinglish and English. This is a research evaluation, not a repair service. I cannot fix your vehicle or contact the manufacturer.

What you give
You can type your story, upload a voice recording, or both. Please describe a real problem you or your family had with a car or bike, in your own words.

What is stored
Your story and recording are stored only on this laptop, in data/real_hindi/. They are not put in the code repository. I do not ask for your name, phone number, or number plate, and I ask you not to include them. If you include them anyway, they will be stored with your story.

AI processing
To evaluate the safety system, the text of your story (not the audio) may be sent to Meta's AI service (Muse Spark). Before it leaves this laptop, common phone-number, email, card, address and VIN patterns are replaced automatically. That pattern matching is not perfect. The AI's output is stored locally with the evaluation. The audio recording itself is not sent to Meta; if I need a transcript, I will type it myself on this laptop.

Voluntary
Taking part is voluntary. You can stop at any time before you submit. After you submit, you can ask me to delete your story. Because it is anonymous, I can only find it with the ID shown after you submit, so please save that ID. There is no payment or other benefit.

Results
Only aggregate numbers will be shared. Your story will not be published. The evaluation may be inconclusive if too few stories are collected."""

CONSENT_SHA256 = hashlib.sha256(CONSENT_TEXT.encode("utf-8")).hexdigest()

#: version -> exact consent-text SHA-256. Keep old versions forever.
CONSENT_REGISTRY: dict[str, str] = {CONSENT_VERSION: CONSENT_SHA256}


def consent_sha256(version: str) -> str | None:
    return CONSENT_REGISTRY.get(version)


__all__ = ["CONSENT_REGISTRY", "CONSENT_SHA256", "CONSENT_TEXT", "CONSENT_VERSION", "consent_sha256"]
