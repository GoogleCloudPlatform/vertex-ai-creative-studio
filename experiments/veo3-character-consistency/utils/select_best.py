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

"""
This module is responsible for selecting the best generated image.

It compares the generated images with the original input images to ensure
character consistency and selects the one with the highest likeness.
"""
from google.genai import Client, types
from pydantic import BaseModel
from typing import List
import config

# Initialize the Gemini client to use Vertex AI
client = Client(vertexai=True, project=config.PROJECT_ID, location=config.GEMINI_LOCATION)

class BestImage(BaseModel):
    """Pydantic model for the best image selection."""
    best_image_path: str
    reasoning: str

def select_best_image(real_image_paths: List[str], generated_image_paths: List[str]) -> BestImage:
    """Selects the best generated image by comparing it against a set of real
    images. This function uses a multimodal model to analyze the images and
    determine which generated image has the highest character likeness to the
    person in the real photos.
    """
    model = "gemini-3.1-pro-preview"
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="application/json",
        response_schema=BestImage.model_json_schema(),
        temperature=0.2,
    )

    # Prepare the prompt with all the images
    prompt_parts = [
        "Please analyze the following images. The first set of images are real photos of a person. The second set of images are AI-generated.",
        "Your task is to select the generated image that best represents the person from the real photos, focusing on facial and physical traits, not clothing or style.",
        "Provide the path of the best image and your reasoning.",
        "\n--- REAL IMAGES ---"
    ]

    for path in real_image_paths:
        prompt_parts.append(types.Part.from_bytes(data=types.Image.from_file(location=path).image_bytes, mime_type="image/png"))

    prompt_parts.append("\n--- GENERATED IMAGES ---")

    for path in generated_image_paths:
        prompt_parts.append(f"Image path: {path}")
        prompt_parts.append(types.Part.from_bytes(data=types.Image.from_file(location=path).image_bytes, mime_type="image/png"))

    response = client.models.generate_content(
        model=model,
        contents=prompt_parts,
        config=config)
    return BestImage.model_validate_json(response.text)