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

# Setup sys.path to allow imports from the parent directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pages.veo import on_click_veo
from state.veo_state import PageState
from state.state import AppState
from common.metadata import MediaItem
from models.requests import VideoGenerationRequest

@patch('pages.veo.add_media_item_to_firestore')
@patch('pages.veo.generate_video')
@patch('mesop.state')
def test_veo_negative_prompt_flow(mock_state, mock_generate_video, mock_add_media_item_to_firestore):
    """
    Tests that the negative_prompt is correctly passed from the UI state
    through the generation request and into the final metadata logging.
    """
    # --- Arrange ---
    prompt = "a cinematic shot of a raccoon"
    negative_prompt = "text, watermark, signature"

    # Mock the return value of the video generation
    mock_generate_video.return_value = ("gs://fake-bucket/video.mp4", "1080p")

    # Setup the mocked states that me.state() will return upon subsequent calls
    mock_app_state = AppState(user_email="test_user@example.com")
    mock_page_state = PageState(
        veo_prompt_input=prompt,
        negative_prompt=negative_prompt,
        veo_model="2.0",
        aspect_ratio="16:9",
        video_length=5,
        resolution="1080p",
        reference_image_gcs=None,
        last_reference_image_gcs=None,
        auto_enhance_prompt=False
    )

    # The on_click_veo function calls me.state() multiple times.
    # We configure the mock to return the appropriate state object each time.
    mock_state.side_effect = [mock_app_state, mock_page_state, mock_page_state, mock_page_state]

    # --- Act ---
    # Call the event handler, which is a generator. We need to exhaust it.
    for _ in on_click_veo(MagicMock()):
        pass

    # --- Assert ---
    # 1. Assert that the video generation function was called correctly.
    mock_generate_video.assert_called_once()
    request_arg = mock_generate_video.call_args[0][0]

    assert isinstance(request_arg, VideoGenerationRequest)
    assert request_arg.prompt == prompt
    assert request_arg.negative_prompt == negative_prompt

    # 2. Assert that the Firestore logging function was called with the correct data.
    mock_add_media_item_to_firestore.assert_called_once()
    media_item_arg = mock_add_media_item_to_firestore.call_args[0][0]

    assert isinstance(media_item_arg, MediaItem)
    assert media_item_arg.prompt == prompt
    assert media_item_arg.negative_prompt == negative_prompt
    assert media_item_arg.user_email == "test_user@example.com"