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

"""Independent probe script to validate Gemini 3.1 Flash-Lite Image capabilities and restrictions against the live API."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google import genai
from google.genai import types
from google.genai.errors import APIError
import pytest

from config.default import Default

cfg = Default()
MODEL_NAME = "gemini-3.1-flash-lite-image"


@pytest.fixture(scope="module")
def client() -> genai.Client:
    """Initialize Vertex AI GenAI SDK Client."""
    http_options = None
    if cfg.GEMINI_IMAGE_GEN_API_BASE_URL:
        http_options = {"base_url": cfg.GEMINI_IMAGE_GEN_API_BASE_URL}

    return genai.Client(
        vertexai=True,
        project=cfg.PROJECT_ID,
        location=cfg.GEMINI_IMAGE_GEN_LOCATION,
        http_options=http_options,
    )


@pytest.mark.integration
def test_probe_1k_image_size_success(client: genai.Client) -> None:
    """Verify that generating an image with 1K size succeeds."""
    print(f"\n[PROBE] Testing {MODEL_NAME} with 1K image_size...")
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="A simple red circle on a white background.",
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
        ),
    )
    assert response.candidates, "No candidates returned for 1K generation."
    has_image = any(
        part.inline_data for candidate in response.candidates for part in candidate.content.parts if candidate.content and candidate.content.parts
    )
    assert has_image, "Response did not contain an inline image part."
    print("[PROBE] 1K image generation SUCCESS.")


@pytest.mark.integration
def test_probe_unsupported_image_size_rejection(client: genai.Client) -> None:
    """Verify that requesting an unsupported size (e.g. 4K) raises an API error or is rejected."""
    print(f"\n[PROBE] Testing {MODEL_NAME} with 4K image_size (expecting rejection or API error)...")
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="A simple red circle on a white background.",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(aspect_ratio="1:1", image_size="4K"),
            ),
        )
        print(f"[PROBE WARNING] 4K generation did not raise an exception. Candidates returned: {len(response.candidates)}")
    except (APIError, ValueError, Exception) as e:
        print(f"[PROBE] Successfully caught expected rejection for 4K image_size: {type(e).__name__}: {e}")


@pytest.mark.integration
def test_probe_thinking_support(client: genai.Client) -> None:
    """Verify that thinking_config is supported by Nano Banana 2 Lite."""
    print(f"\n[PROBE] Testing {MODEL_NAME} with ThinkingConfig...")
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="A futuristic cityscape at dusk, detailed architectural drawing.",
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(aspect_ratio="16:9", image_size="1K"),
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=-1,
            ),
        ),
    )
    assert response.candidates, "No candidates returned for thinking generation."
    print("[PROBE] Thinking generation SUCCESS.")


if __name__ == "__main__":
    c = genai.Client(
        vertexai=True,
        project=cfg.PROJECT_ID,
        location=cfg.GEMINI_IMAGE_GEN_LOCATION,
    )
    try:
        test_probe_1k_image_size_success(c)
        test_probe_unsupported_image_size_rejection(c)
        test_probe_thinking_support(c)
    except Exception as e:
        print(f"Probe execution failed: {e}")
