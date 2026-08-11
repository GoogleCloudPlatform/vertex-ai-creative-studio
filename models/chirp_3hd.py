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

"""Model for Chirp3 HD Text-to-Speech."""


from google.cloud import texttospeech_v1beta1 as texttospeech

from common.analytics import get_logger, track_model_call

logger = get_logger(__name__)


def synthesize_chirp_speech(
    text: str,
    voice_name: str,
    language_code: str,
    speaking_rate: float = 1.0,
    # pitch: float = 0.0, # Disabled pending API support
    volume_gain_db: float = 0.0,
    pronunciations: list[dict[str, str]] = None,
    phonetic_encoding: str = "PHONETIC_ENCODING_X_SAMPA",
) -> bytes:
    """Synthesizes speech from text using the Chirp3 HD model."""
    full_voice_name = f"{language_code}-Chirp3-HD-{voice_name}"
    billing_units = {
        "characters_synthesized": len(text) if text else 0,
        "voice_name": full_voice_name,
        "language_code": language_code,
        "speaking_rate": speaking_rate,
    }

    with track_model_call("chirp-3-hd", billing_units=billing_units) as ctx:
        client = texttospeech.TextToSpeechClient()

        input_dict = {"text": text}

        # Handle custom pronunciations
        custom_pronunciation_entries = []
        if pronunciations:
            logger.info(f"Custom pronunciations: {pronunciations}")
            for p in pronunciations:
                entry = texttospeech.CustomPronunciationParams(
                    phrase=p["phrase"],
                    pronunciation=p["pronunciation"],
                    phonetic_encoding=phonetic_encoding,
                )
                custom_pronunciation_entries.append(entry)
            if custom_pronunciation_entries:
                input_dict["custom_pronunciations"] = texttospeech.CustomPronunciations(
                    pronunciations=custom_pronunciation_entries,
                )

        synthesis_input = texttospeech.SynthesisInput(input_dict)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=full_voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=speaking_rate,
            # pitch=pitch,
            volume_gain_db=volume_gain_db,
        )

        logger.debug(
            f"Synthesize speech request - Voice: {voice}, Audio Config: {audio_config}",
        )

        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            audio_content = response.audio_content
            ctx["billing_units"]["audio_bytes"] = (
                len(audio_content) if audio_content else 0
            )
            return audio_content
        except Exception as e:
            logger.error(f"synthesize_speech call failed: {e}")
            raise
