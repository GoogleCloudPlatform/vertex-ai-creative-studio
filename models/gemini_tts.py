# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Model for Gemini Text-to-Speech."""

from google.cloud import texttospeech

from common.analytics import get_logger, track_model_call
from config.default import Default

cfg = Default()
logger = get_logger(__name__)


def synthesize_speech(
    text: str, prompt: str, model_name: str, voice_name: str, language_code: str,
) -> bytes:
    """Synthesizes speech from text using the Gemini TTS API.

    Args:
        text: The text to synthesize.
        prompt: The prompt for the voice.
        model_name: The name of the TTS model to use.
        voice_name: The name of the voice to use.
        language_code: Language code for synthesis.

    Returns:
        The synthesized audio in bytes.

    """
    billing_units = {
        "characters_synthesized": len(text) if text else 0,
        "voice_name": voice_name,
        "language_code": language_code,
    }

    with track_model_call(
        model_name or "gemini-tts", billing_units=billing_units,
    ) as ctx:
        client_options = {}
        if cfg.GEMINI_TTS_LOCATION and cfg.GEMINI_TTS_LOCATION != "global":
            client_options["api_endpoint"] = (
                f"{cfg.GEMINI_TTS_LOCATION}-texttospeech.googleapis.com"
            )

        client = texttospeech.TextToSpeechClient(client_options=client_options)

        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text, prompt=prompt),
            voice=texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name, model_name=model_name,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            ),
        )

        audio_content = response.audio_content
        ctx["billing_units"]["audio_bytes"] = len(audio_content) if audio_content else 0
        return audio_content
