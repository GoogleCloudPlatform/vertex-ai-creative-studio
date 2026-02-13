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
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.veo import image_to_video
from config.default import Default

# Use an existing test image for consistency
PERSON_IMAGE = os.environ.get("PERSON_IMAGE", "gs://genai-blackbelt-fishfooding-assets/vto_person_images/vto_model_001.png")

# Mock the fetch_operation to avoid long waits
@patch('models.veo.fetch_operation', return_value=MagicMock())
@patch('models.veo.send_request_to_google_api', return_value={'name': 'mock_operation_name'})
def test_i2v_uses_veo3_model(mock_send_request, mock_fetch_operation):
    """Tests that image_to_video uses the Veo 3.0 endpoint when model is '3.0'."""
    cfg = Default()
    image_to_video(
        model="3.0",
        prompt="A test prompt",
        image_gcs=PERSON_IMAGE,
        seed=123,
        aspect_ratio="16:9",
        sample_count=1,
        output_gcs="gs://fake-bucket/videos",
        enable_pr=False,
        duration_seconds=5,
    )

    mock_send_request.assert_called_once()
    called_endpoint = mock_send_request.call_args[0][0]
    assert cfg.VEO_EXP_MODEL_ID in called_endpoint
    assert cfg.VEO_MODEL_ID not in called_endpoint
    print(f"\nVeo 3.0 test PASSED: Endpoint '{called_endpoint}' correctly contains '{cfg.VEO_EXP_MODEL_ID}'")

@patch('models.veo.fetch_operation', return_value=MagicMock())
@patch('models.veo.send_request_to_google_api', return_value={'name': 'mock_operation_name'})
def test_i2v_uses_veo2_model(mock_send_request, mock_fetch_operation):
    """Tests that image_to_video uses the Veo 2.0 endpoint when model is '2.0'."""
    cfg = Default()
    image_to_video(
        model="2.0",
        prompt="A test prompt",
        image_gcs=PERSON_IMAGE,
        seed=123,
        aspect_ratio="16:9",
        sample_count=1,
        output_gcs="gs://fake-bucket/videos",
        enable_pr=False,
        duration_seconds=5,
    )

    mock_send_request.assert_called_once()
    called_endpoint = mock_send_request.call_args[0][0]
    assert cfg.VEO_MODEL_ID in called_endpoint
    assert cfg.VEO_EXP_MODEL_ID not in called_endpoint
    print(f"\nVeo 2.0 test PASSED: Endpoint '{called_endpoint}' correctly contains '{cfg.VEO_MODEL_ID}'")

