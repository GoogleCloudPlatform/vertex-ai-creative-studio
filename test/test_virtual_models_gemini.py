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

"""Unit tests for the Nano Banana routing of generate_virtual_models.

They prove generate_virtual_models routes through the Nano Banana (Gemini
image) adapter instead of the retired Imagen generation path.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.default import Default
from models.image_models import generate_virtual_models


def _fake_adapter_return(
    uri: str,
) -> tuple[list[str], float, list[str], None, list[str]]:
    """Mirror the 5-tuple contract of generate_image_from_prompt_and_images."""
    return ([uri], 0.0, [], None, [])


def test_generate_virtual_models_routes_through_gemini_adapter() -> None:
    """A single-image request calls the Gemini adapter with text-only inputs."""
    with patch(
        "models.image_models.gemini.generate_image_from_prompt_and_images",
        return_value=_fake_adapter_return("gs://fake-bucket/virtual_model_0.png"),
    ) as mock_adapter:
        uris = generate_virtual_models(prompt="a model in a studio", num_images=1)

    mock_adapter.assert_called_once()
    _, kwargs = mock_adapter.call_args
    assert kwargs["prompt"] == "a model in a studio"
    assert kwargs["images"] == []  # text-only
    assert kwargs["aspect_ratio"] == "1:1"
    assert kwargs["gcs_folder"] == Default().IMAGEN_GENERATED_SUBFOLDER
    assert kwargs["file_prefix"] == "virtual_model"
    assert kwargs["model_name"] == Default().GEMINI_IMAGE_GEN_MODEL
    assert uris == ["gs://fake-bucket/virtual_model_0.png"]


def test_generate_virtual_models_produces_n_uris_for_n_images() -> None:
    """num_images=N yields N adapter calls and N accumulated GCS URIs."""
    returns = [
        _fake_adapter_return(f"gs://fake-bucket/virtual_model_{i}.png")
        for i in range(3)
    ]
    with patch(
        "models.image_models.gemini.generate_image_from_prompt_and_images",
        side_effect=returns,
    ) as mock_adapter:
        uris = generate_virtual_models(prompt="a model", num_images=3)

    assert mock_adapter.call_count == 3
    assert uris == [
        "gs://fake-bucket/virtual_model_0.png",
        "gs://fake-bucket/virtual_model_1.png",
        "gs://fake-bucket/virtual_model_2.png",
    ]
