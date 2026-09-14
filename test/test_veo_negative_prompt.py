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
from models.requests import VideoGenerationRequest

@patch('pages.veo.start_async_veo_job')
@patch('mesop.state')
def test_veo_negative_prompt_flow(mock_state, mock_start_async_veo_job, app_state_factory):
    """
    Tests that the negative_prompt is correctly passed from the UI state
    through to the async generation request.

    Veo generation runs as an async job: on_click_veo builds a
    VideoGenerationRequest from the page state and hands it to
    start_async_veo_job. The negative_prompt must survive that hand-off so the
    downstream service/model layer (which reads request.negative_prompt) can
    apply it.
    """
    # --- Arrange ---
    prompt = "a cinematic shot of a raccoon"
    negative_prompt = "text, watermark, signature"

    # Return a job that is already complete so on_click_veo does not enter its
    # Firestore polling loop.
    mock_start_async_veo_job.return_value = {
        "job_id": "test-job-id",
        "status": "complete",
    }

    # Setup the mocked states that me.state() will return.
    mock_app_state = app_state_factory(user_email="test_user@example.com")
    mock_page_state = PageState(
        veo_prompt_input=prompt,
        negative_prompt=negative_prompt,
        veo_model="3.1-fast",
        aspect_ratio="16:9",
        video_length=5,
        resolution="1080p",
        reference_image_gcs=None,
        last_reference_image_gcs=None,
        auto_enhance_prompt=False,
    )

    # The on_click_veo function (and its @track_click decorator) call me.state()
    # multiple times for both AppState and PageState. Return the appropriate
    # state object based on the requested class so the mock is order-independent.
    mock_state.side_effect = (
        lambda cls: mock_page_state if cls is PageState else mock_app_state
    )

    # --- Act ---
    # Call the event handler, which is a generator. We need to exhaust it.
    for _ in on_click_veo(MagicMock()):
        pass

    # --- Assert ---
    # The async job must be kicked off exactly once with the built request.
    mock_start_async_veo_job.assert_called_once()
    request_arg = mock_start_async_veo_job.call_args[0][0]
    user_email_arg = mock_start_async_veo_job.call_args[0][1]

    assert isinstance(request_arg, VideoGenerationRequest)
    assert request_arg.prompt == prompt
    # The crux of this test: the negative_prompt must be carried into the request.
    assert request_arg.negative_prompt == negative_prompt
    assert user_email_arg == "test_user@example.com"
