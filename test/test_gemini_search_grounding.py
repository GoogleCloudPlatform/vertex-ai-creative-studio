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

import os
import pytest
from google import genai
from google.genai import types

# Retrieve project and location from environment variables
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = "gemini-2.5-flash-image"

if not PROJECT_ID:
    print("Skipping test: GOOGLE_CLOUD_PROJECT not set.")
    pytest.skip("GOOGLE_CLOUD_PROJECT not set", allow_module_level=True)

MODEL_ID = "gemini-3-pro-image-preview"

if not PROJECT_ID:
    print("Skipping test: GOOGLE_CLOUD_PROJECT not set.")
    pytest.skip("GOOGLE_CLOUD_PROJECT not set", allow_module_level=True)

def test_gemini_search_grounding():
    """Tests Gemini Image Generation with Google Search to inspect grounding metadata."""
    
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION
    )

    prompt = "A realistic image of the current weather in New York City."
    
    print(f"\n--- Testing Model: {MODEL_ID} ---")
    print(f"Prompt: {prompt}")

    # 1. With Search
    print("\n--- Generating WITH Search ---")
    try:
        response_search = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_modalities=["IMAGE", "TEXT"],
            )
        )
        
        print("Response received.")
        
        if response_search.candidates:
            candidate = response_search.candidates[0]
            print(f"Candidate has grounding_metadata: {hasattr(candidate, 'grounding_metadata')}")
            
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                print("\nGrounding Metadata:")
                print(candidate.grounding_metadata)
                
                # Check specific fields we might want
                if hasattr(candidate.grounding_metadata, 'search_entry_point'):
                     print(f"Search Entry Point: {candidate.grounding_metadata.search_entry_point}")
                if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                     print(f"Grounding Chunks: {candidate.grounding_metadata.grounding_chunks}")
            else:
                print("No grounding_metadata found in candidate.")
                
    except Exception as e:
        print(f"Error with search: {e}")

if __name__ == "__main__":
    test_gemini_search_grounding()
