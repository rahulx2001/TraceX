"""Narrow contradiction/identifier checks, not a semantic-accuracy evaluator.

These rules catch critical unsupported transformations for review. Passing them
never certifies entailment: independently graded human support remains required.
"""
from __future__ import annotations

import re
import unicodedata

VERSION = "critical-source-support-v1"
_DENIAL = re.compile(r"\b(?:no|not|never|without|denied|denies|negative|nahi|nahin|nhi)\b|नहीं|नही|बिना", re.I)
_CLAUSES = re.compile(r"[.!?।;\n]+|\bbut\b|\blekin\b|लेकिन", re.I)
_CONCEPTS = {
    "fire": re.compile(r"\b(?:fire|flames?|aag)\b|आग", re.I),
    "smoke": re.compile(r"\b(?:smoke|dhua|dhuan)\b|धुआ", re.I),
    "injury": re.compile(r"\b(?:injur\w*|hurt|chot)\b|चोट", re.I),
    "leak": re.compile(r"\b(?:leak\w*|risav)\b|रिसाव", re.I),
    "crack": re.compile(r"\b(?:crack\w*|darar)\b|दरार", re.I),
}
_HISTORY = re.compile(r"\b(?:previous|earlier|initial|corrected|correction|mistaken|incorrect|instead|rather|not)\b|पहले|सुधार", re.I)
_ASSERTED_EVENT = re.compile(r"\b(?:occurred|happened|confirmed|detected|found|hua|hui)\b|लगी", re.I)


def normalize(text: str) -> str:
    return "".join(str(unicodedata.digit(c)) if c.isdecimal() else c for c in text).casefold()


def critical_tokens(text: str) -> set[str]:
    identifiers = {normalize(value) for value in re.findall(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b", text)}
    values = re.findall(r"(?<!\w)(?:[a-z]+[-_])+(?:[a-z0-9]+[-_]*)+|(?<!\w)[a-z]+\d+[a-z0-9-]*|\b\d+(?:[./-]\d+)*\b", normalize(text))
    return identifiers | {value for value in values if any(c.isdecimal() for c in value)}


def support_issues(interpretation: str, quotes: list[str], *, polarity: str | None = None) -> list[str]:
    """Return explicit reasons to withhold a claim; bounded English/Hindi rules."""
    cited = "\n".join(quotes)
    issues = []
    invented = critical_tokens(interpretation) - critical_tokens(cited)
    if invented:
        issues.append("number_or_identifier_not_in_citation:" + ",".join(sorted(invented)))
    claim_clauses = _CLAUSES.split(interpretation)
    source_clauses = _CLAUSES.split(cited)
    for name, pattern in _CONCEPTS.items():
        claimed = [s for s in claim_clauses if pattern.search(s)]
        if not claimed:
            continue
        relevant = [s for s in source_clauses if pattern.search(s)]
        if not relevant:
            issues.append("critical_event_not_in_citation:" + name)
            continue
        source_denies = all(_DENIAL.search(s) for s in relevant)
        claim_affirms = polarity == "affirmed" or any(not _DENIAL.search(s) and (polarity != "denied" or _ASSERTED_EVENT.search(s)) for s in claimed)
        if source_denies and claim_affirms:
            issues.append("denial_reversed:" + name)
    # Explicit model-year corrections must not silently reuse an earlier year.
    # General semantic/temporal entailment remains a human grading task.
    years = re.findall(r"\b(?:19|20)\d{2}\b", normalize(cited))
    claimed_years = re.findall(r"\b(?:19|20)\d{2}\b", normalize(interpretation))
    if len(set(years)) > 1 and _HISTORY.search(cited) and claimed_years and not _HISTORY.search(interpretation):
        issues.append("conflicting_years_need_explicit_correction_context")
    return list(dict.fromkeys(issues))
