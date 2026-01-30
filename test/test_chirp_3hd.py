# Copyright 2026 Google LLC
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

"""Test script for Chirp3 HD Text-to-Speech model."""
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.chirp_3hd import synthesize_chirp_speech

def main():
    """Main function to test the Chirp3 HD TTS model."""
    print("Testing Chirp3 HD speech synthesis...")

    # Sample inputs
    text_input = "This is a test of the Chirp3 HD text to speech model."
    voice_name = "Orus"
    language_code = "en-US"
    output_filename = "chirp3_hd_test_output.wav"

    try:
        audio_bytes = synthesize_chirp_speech(
            text=text_input,
            voice_name=voice_name,
            language_code=language_code,
        )

        with open(output_filename, "wb") as f:
            f.write(audio_bytes)

        print(f"Successfully synthesized speech and saved to {output_filename}")
        print("You can now play this file to verify the audio.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
