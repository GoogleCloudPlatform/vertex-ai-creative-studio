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
import datetime

# Setup sys.path to allow imports from the parent directory.
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pages.veo import on_click_veo
from state.veo_state import PageState
from state.state import AppState
from common.metadata import MediaItem

@patch('pages.veo.add_media_item_to_firestore')
@patch('pages.veo.generate_video', return_value="gs://fake-bucket/fake_video.mp4")
@patch('mesop.state')
def test_veo_generation_flow_and_metadata(mock_state, mock_generate_video, mock_add_media_item):
    """
    Tests the VEO generation flow, focusing on the data handling and metadata
    creation after a successful API call.
    """
    # --- Arrange ---
    # Setup the mocked state that the on_click_veo function will use.
    mock_app_state = AppState(user_email="test_user@example.com")
    mock_page_state = PageState(
        veo_prompt_input="a test prompt for veo",
        veo_model="2.0",
        aspect_ratio="16:9",
        video_length=5,
        reference_image_gcs=None,
        last_reference_image_gcs=None,
        auto_enhance_prompt=False
    )

    # Configure the mesop.state mock to return the correct state object when called.
    mock_state.side_effect = [mock_app_state, mock_page_state]

    # --- Act ---
    # Call the event handler function. This is a generator function, so we need to exhaust it.
    for _ in on_click_veo(MagicMock()):
        pass

    # --- Assert ---
    # 1. Verify that our main video generation function was called.
    mock_generate_video.assert_called_once()

    # 2. Verify that the Firestore logging function was called.
    mock_add_media_item.assert_called_once()

    # 3. Inspect the data that was passed to the Firestore function.
    # This is the crucial part that catches the `NameError` or `AttributeError`.
    call_args, _ = mock_add_media_item.call_args
    media_item_logged = call_args[0]

    assert isinstance(media_item_logged, MediaItem)
    assert media_item_logged.user_email == "test_user@example.com"
    assert media_item_logged.prompt == "a test prompt for veo"
    assert media_item_logged.gcsuri == "gs://fake-bucket/fake_video.mp4"
    assert media_item_logged.model == "veo-2.0-generate-001" # This comes from config

    print("\nComponent-level integration test for VEO passed successfully.")

