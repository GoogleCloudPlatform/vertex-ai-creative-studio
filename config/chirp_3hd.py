"""Configuration for Chirp3 HD voices and languages."""

# To avoid duplication, we reuse the voice and language lists from the
# Gemini TTS configuration, as they are compatible with Chirp3 HD.
from .gemini_tts import (
    GEMINI_TTS_VOICES as CHIRP3_HD_VOICES,
    CHIRP3_HD_LANGUAGES,
    GEMINI_TTS_ENCODINGS as CHIRP3_HD_ENCODINGS,
)
