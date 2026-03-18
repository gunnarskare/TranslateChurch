from __future__ import annotations

import asyncio
import logging
from typing import Dict

from openai import AsyncOpenAI

from backend.config import Settings

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: tuple[str, ...] = ('en', 'uk')
LANGUAGE_NAMES: dict[str, str] = {
    'en': 'English',
    'uk': 'Ukrainian',
}


class OpenAITranslationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def translate_text(self, text: str, target_language: str) -> str:
        if target_language not in SUPPORTED_LANGUAGES:
            raise ValueError(f'Unsupported language: {target_language}')

        response = await self.client.chat.completions.create(
            model=self.settings.translation_model,
            temperature=0,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You translate Norwegian church speech into natural, faithful target text. '
                        'Return only the translation, with no notes or labels.'
                    ),
                },
                {
                    'role': 'user',
                    'content': (
                        f'Translate the following Norwegian text into {LANGUAGE_NAMES[target_language]}. '
                        'Preserve meaning, names, Bible references, and sentence tone.\n\n'
                        f'Text: {text}'
                    ),
                },
            ],
        )
        translated = (response.choices[0].message.content or '').strip()
        logger.info('Translation ready for %s', target_language)
        return translated

    async def translate_bundle(self, text: str) -> Dict[str, str]:
        results = await asyncio.gather(*(self.translate_text(text, language) for language in SUPPORTED_LANGUAGES))
        return dict(zip(SUPPORTED_LANGUAGES, results, strict=True))


# TODO: Add text-to-speech generation hooks here once audio playback is needed.
