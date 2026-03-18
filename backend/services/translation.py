"""Translation service stub.

In a production system this module would call a real translation API
(e.g. DeepL or Google Cloud Translate).  For now it returns placeholder
strings so the rest of the pipeline can be developed and tested without
external API keys.
"""

from typing import Dict

# Supported target languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "uk")


async def translate(text: str, target_language: str) -> str:
    """Return the translation of *text* into *target_language*.

    Currently returns a stub result.  Replace the body of this function
    with a real API call when translation credentials are available.
    """
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported target language '{target_language}'. "
            f"Supported: {SUPPORTED_LANGUAGES}"
        )
    # TODO: integrate a real translation backend
    return f"[{target_language.upper()}] {text}"


async def translate_all(text: str) -> Dict[str, str]:
    """Translate *text* into all supported languages and return a mapping."""
    results: Dict[str, str] = {}
    for lang in SUPPORTED_LANGUAGES:
        results[lang] = await translate(text, lang)
    return results
