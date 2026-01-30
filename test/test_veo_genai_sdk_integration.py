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

import pytest
from unittest.mock import patch, MagicMock

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.veo import generate_video
from state.veo_state import PageState

@pytest.fixture
def mock_state():
    """Provides a mock PageState object for tests."""
    state = PageState(
        veo_prompt_input="a test prompt",
        veo_model="2.0",
        aspect_ratio="16:9",
        video_length=5,
        reference_image_gcs=None,
        last_reference_image_gcs=None,
        auto_enhance_prompt=False
    )
    return state

@pytest.mark.integration
def test_veo2_t2v_generation(mock_state):
    """Tests text-to-video with Veo 2.0."""
    mock_state.veo_model = "2.0"
    result = generate_video(mock_state)
    assert result.startswith("gs://")

@pytest.mark.integration
def test_veo3_t2v_generation(mock_state):
    """Tests text-to-video with Veo 3.0."""
    mock_state.veo_model = "3.0"
    result = generate_video(mock_state)
    assert result.startswith("gs://")

@pytest.mark.integration
def test_veo3_fast_t2v_generation(mock_state):
    """Tests text-to-video with Veo 3.0-fast."""
    mock_state.veo_model = "3.0-fast"
    result = generate_video(mock_state)
    assert result.startswith("gs://")

@pytest.mark.integration
def test_veo_i2v_generation(mock_state):
    """Tests image-to-video."""
    mock_state.reference_image_gcs = "gs://genai-blackbelt-fishfooding-assets/test-cat.png"
    result = generate_video(mock_state)
    assert result.startswith("gs://")
