# Copyright 2024 Google LLC
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

"""Test script for Gemini Text-to-Speech model."""
import os

# Add the project root to the Python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.gemini_tts import synthesize_speech


def main():
    """Main function to test the Gemini TTS model."""
    print("Testing Gemini TTS speech synthesis...")

    # Sample inputs
    text_input = "[laughing] oh my god! [sigh] did you see what he is wearing?"
    prompt_input = "you are having a casual conversation with a friend and you are amused. say the following:"
    model_name_input = "gemini-2.5-flash-preview-tts"
    output_filename = "gemini_tts_test_output.wav"

    try:
        audio_bytes = synthesize_speech(
            text=text_input,
            prompt=prompt_input,
            model_name=model_name_input,
            voice_name="Callirrhoe",
        )

        with open(output_filename, "wb") as f:
            f.write(audio_bytes)

        print(f"Successfully synthesized speech and saved to {output_filename}")
        print("You can now play this file to verify the audio.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
