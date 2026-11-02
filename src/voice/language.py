"""Small validated speech preference contract; script language is independent."""
import re

SPEECH_LOCALES = {"en-US", "en-IN", "hi-IN"}


def speech_locale(value: str | None) -> str:
    if value is None or value == "":
        return "en-US"
    if value not in SPEECH_LOCALES:
        raise ValueError("Speech locale must be en-US, en-IN or hi-IN")
    return value


def response_locale(text: str, preference: str | None = None) -> str:
    locale = speech_locale(preference)
    if re.search(r"[\u0900-\u097f]", text or ""):
        return "hi-IN"
    return "en-IN" if locale in {"hi-IN", "en-IN"} else "en-US"
