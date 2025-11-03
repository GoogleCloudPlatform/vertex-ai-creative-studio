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
import google.cloud.texttospeech as texttospeech

def synthesize_speech(text: str, prompt: str, model_name: str, voice_name: str, language_code: str) -> bytes:
    """
    Synthesizes speech from text using the Gemini TTS API.

    Args:
        text: The text to synthesize.
        prompt: The prompt for the voice.
        model_name: The name of the TTS model to use.
        voice_name: The name of the voice to use.

    Returns:
        The synthesized audio in bytes.
    """
    client = texttospeech.TextToSpeechClient()
        
    response = client.synthesize_speech(input=texttospeech.SynthesisInput(text=text, prompt=prompt),
                                        voice=texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name, model_name=model_name),
                                        audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16))

    return response.audio_content