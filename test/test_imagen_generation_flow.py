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

from components.imagen.generation_controls import on_click_generate_images
from state.imagen_state import PageState
from state.state import AppState
from common.metadata import MediaItem

@patch('components.imagen.generation_controls.add_media_item_to_firestore')
@patch('components.imagen.generation_controls.generate_compliment', return_value="A stunning image!")
@patch('components.imagen.generation_controls.generate_images_from_prompt', return_value=["gs://fake-bucket/fake_image.png"])
@patch('mesop.state')
def test_imagen_generation_flow_and_metadata(mock_state, mock_generate_images, mock_generate_compliment, mock_add_media_item):
    """    
    Tests the Imagen generation flow, focusing on the data handling and metadata
    creation after a successful API call.
    """
    # --- Arrange ---
    # Setup the mocked state that the on_click_generate_images function will use.
    mock_app_state = AppState(user_email="test_user@example.com")
    mock_page_state = PageState(
        image_prompt_input="a test prompt for imagen",
        image_model_name="imagen-4.0-generate-preview-06-06",
        imagen_image_count=1,
        image_negative_prompt_input="",
        image_aspect_ratio="1:1",
        imagen_seed=123
    )

    # Configure the mesop.state mock to return the correct state object when called.
    mock_state.side_effect = [mock_app_state, mock_page_state]

    # --- Act ---
    # Call the event handler function. This is a generator function, so we need to exhaust it.
    for _ in on_click_generate_images(MagicMock()):
        pass

    # --- Assert ---
    # 1. Verify that our main image generation function was called.
    mock_generate_images.assert_called_once()

    # 2. Verify that the Firestore logging function was called.
    mock_add_media_item.assert_called_once()

    # 3. Inspect the data that was passed to the Firestore function.
    # This is the crucial part that catches the `NameError` or `AttributeError`.
    call_args, _ = mock_add_media_item.call_args
    media_item_logged = call_args[0]

    assert isinstance(media_item_logged, MediaItem)
    assert media_item_logged.user_email == "test_user@example.com"
    assert media_item_logged.prompt == "a test prompt for imagen"
    assert media_item_logged.gcs_uris == ["gs://fake-bucket/fake_image.png"]
    assert media_item_logged.model == "imagen-4.0-generate-preview-06-06"
    assert media_item_logged.critique == "A stunning image!"

    print("\nComponent-level integration test for Imagen passed successfully.")

