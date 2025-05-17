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
"""Gemini methods"""

import json
from typing import Dict, Optional

from google.genai import types

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from models.model_setup import (
    GeminiModelSetup,
)

# Initialize client and default model ID for rewriter
# The analysis function will use its own specific model ID for now.
client, model_id = GeminiModelSetup.init()
REWRITER_MODEL_ID = model_id  # Use a more specific name for the rewriter's model ID


@retry(
    wait=wait_exponential(
        multiplier=1, min=1, max=10
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions for robustness
    reraise=True,  # re-raise the last exception if all retries fail
)
def rewriter(original_prompt: str, rewriter_prompt: str) -> str:
    """A Gemini rewriter.

    Args:
        original_prompt: The original prompt to be rewritten.
        rewriter_prompt: The rewriter prompt.

    Returns:
        The rewritten prompt text.
    """

    full_prompt = f"{rewriter_prompt} {original_prompt}"

    try:
        response = client.models.generate_content(
            model=REWRITER_MODEL_ID,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )
        print(f"Rewriter success! {response.text}")
        return response.text
    except Exception as e:
        print(f"Rewriter error: {e}")
        raise


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def analyze_audio_with_gemini(
    audio_uri: str, music_generation_prompt: str
) -> Optional[Dict[str, any]]:
    """
    Analyzes a given audio file URI against an original music generation prompt using Gemini.

    Args:
        audio_uri: The GCS URI (gs://bucket/object) of the audio file to analyze.
        music_generation_prompt: The original prompt used to generate the music.

    Returns:
        A dictionary containing the structured analysis from Gemini, or None if an error occurs.
    """
    print(
        f"Starting audio analysis for URI: {audio_uri} with prompt: '{music_generation_prompt}'"
    )

    # Define the specific model for audio analysis (as per your sample)
    analysis_model_id = "gemini-2.5-flash-preview-04-17"

    # Prepare the audio part using from_uri
    try:
        audio_part = types.Part.from_uri(file_uri=audio_uri, mime_type="audio/wav")
        print(f"Audio part created from URI: {audio_uri}")
    except Exception as e:
        print(f"Failed to create audio Part from URI '{audio_uri}': {e}")
        raise  # Re-raise to be caught by tenacity or calling function

    # Prepare the text part, incorporating the dynamic music_generation_prompt
    text_prompt_for_analysis = f"""Describe this musical clip ("audio-analysis"), then suggest a list of genres and qualities.

The original prompt was the following:

"{music_generation_prompt}"

Then, review the original prompt with your description.

Output this as JSON.

"""

    text_part = types.Part.from_text(text=text_prompt_for_analysis)

    # System instruction
    system_instruction_text = """You're a music producer and critic with a keen ear for describing musical qualities and soundscapes. If you're given audio, describe it. If you're given an idea or a scenario, describe the music that would represent that. Aim for a single paragraph description of musical direction and optionally any explanation of your direction. As a rule, don't refer to any particular artist, but instead describe their style."""
    # system_instruction_part = types.Part.from_text(text=system_instruction_text) # API expects a Part or list of Parts

    safety_settings_list = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    schema_json = {  # This is the schema from your sample
        # "$schema": "http://json-schema.org/draft-07/schema#", # Schema for schema, optional here
        "title": "Music Analysis and Alignment Response",
        "description": "Schema for describing audio analysis, suggested genres/qualities, and alignment with an initial prompt.",
        "type": "OBJECT",
        "properties": {
            "audio-analysis": {
                "description": "A single-paragraph description of the provided audio or suggested musical direction.",
                "type": "STRING",
            },
            "genre-quality": {
                "description": "A list of suggested genres and descriptive musical qualities.",
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "minItems": 1,
            },
            "prompt-alignment": {
                "description": "An evaluation of how well the audio or generated description aligns with the original prompt's requirements.",
                "type": "STRING",
            },
        },
        "required": ["audio-analysis", "genre-quality", "prompt-alignment"],
        # "additionalProperties": False, # This can be strict; ensure model adheres or remove
    }
    generation_config_params = types.GenerateContentConfig(
        system_instruction=system_instruction_text,
        safety_settings=safety_settings_list,
        #temperature=1.0,  # Corrected: float value
        #top_p=1.0,  # Corrected: float value
        # seed=0, # Seed might not be available in all models or SDK versions, or might be int
        #max_output_tokens=8192,  # Max for Flash is 8192. 65535 is too high.
        response_mime_type="application/json",  # This is key for JSON output
        response_schema=schema_json,
    )

    # Construct the contents for the API call
    contents_for_api = [
        types.Content(role="user", parts=[audio_part, text_part]),
    ]

    try:
        print(f"Sending request to Gemini model: {analysis_model_id}")

        response = client.models.generate_content(  # Or client.generate_content if client is a model instance
            model=analysis_model_id,
            contents=contents_for_api,
            config=generation_config_params,
        )

        print("Received response from Gemini.")
        print(f"{response}")

        # Assuming the response.text contains the JSON string due to response_mime_type
        if response.text:
            parsed_json = json.loads(response.text)
            print(f"Successfully parsed analysis JSON: {parsed_json}")
            return parsed_json
            #return response.text
        else:
            # Handle cases where response.text might be empty or parts are structured differently
            # This part might need adjustment based on actual API response structure for JSON
            if response.parts:
                # Try to assemble from parts if text is empty but parts exist (less common for JSON)
                json_text_from_parts = "".join(
                    part.text for part in response.parts if hasattr(part, "text")
                )
                if json_text_from_parts:
                    parsed_json = json.loads(json_text_from_parts)
                    print(
                        f"Successfully parsed analysis JSON from parts: {parsed_json}"
                    )
                    return parsed_json
            print("Warning: Gemini response text was empty.")
            return None  # Or raise an error

    except Exception as e:
        print(f"Error during Gemini API call for audio analysis: {e}")
        # The retry decorator will handle re-raising if all attempts fail.
        # If not using retry, you'd raise e here.
        raise  # Re-raise for tenacity or the caller
