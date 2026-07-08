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

"""Unit tests for Gemini Omni model backend services."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from unittest.mock import MagicMock, patch

from models.omni import (
    _build_input_parts,
    _extract_video_payload,
    _modify_prompt_for_omni,
    generate_omni_video,
)
from models.requests import APIReferenceImage, OmniVideoGenerationRequest


def test_build_input_parts_t2v() -> None:
    """Test building input parts for Text-to-Video mode."""
    req = OmniVideoGenerationRequest(
        prompt="A cute cat playing with yarn",
        duration_seconds=10,
        aspect_ratio="16:9",
        resolution="720p",
        omni_mode="t2v",
        model_version_id="gemini-omni-flash-preview",
    )
    parts = _build_input_parts(req)
    assert parts == [{"type": "text", "text": "A cute cat playing with yarn"}]


def test_build_input_parts_i2v() -> None:
    """Test building input parts for Image-to-Video mode."""
    req = OmniVideoGenerationRequest(
        prompt="Make it move",
        duration_seconds=10,
        aspect_ratio="16:9",
        resolution="720p",
        omni_mode="i2v",
        model_version_id="gemini-omni-flash-preview",
        reference_image_gcs="gs://bucket/image.png",
        reference_image_mime_type="image/png",
    )
    parts = _build_input_parts(req)
    assert len(parts) == 2
    assert parts[0] == {"type": "text", "text": "Make it move"}
    assert parts[1] == {
        "type": "image",
        "mime_type": "image/png",
        "uri": "gs://bucket/image.png",
    }


def test_build_input_parts_ref2v() -> None:
    """Test building input parts for Reference-to-Video mode."""
    req = OmniVideoGenerationRequest(
        prompt="Generate consistent video",
        duration_seconds=10,
        aspect_ratio="16:9",
        resolution="720p",
        omni_mode="ref2v",
        model_version_id="gemini-omni-flash-preview",
        r2v_references=[
            APIReferenceImage(gcs_uri="gs://bucket/ref1.jpg", mime_type="image/jpeg"),
            APIReferenceImage(gcs_uri="gs://bucket/ref2.jpg", mime_type="image/jpeg"),
        ],
    )
    parts = _build_input_parts(req)
    assert len(parts) == 3
    assert parts[0] == {"type": "text", "text": "Generate consistent video"}
    assert parts[1] == {
        "type": "image",
        "mime_type": "image/jpeg",
        "uri": "gs://bucket/ref1.jpg",
    }
    assert parts[2] == {
        "type": "image",
        "mime_type": "image/jpeg",
        "uri": "gs://bucket/ref2.jpg",
    }


def test_build_input_parts_edit() -> None:
    """Test building input parts for Video Editing mode."""
    req = OmniVideoGenerationRequest(
        prompt="Change character's shirt to blue",
        duration_seconds=10,
        aspect_ratio="16:9",
        resolution="720p",
        omni_mode="edit",
        model_version_id="gemini-omni-flash-preview",
        reference_image_gcs="gs://bucket/ref.png",
        reference_image_mime_type="image/png",
        reference_video_gcs="gs://bucket/base.mp4",
        reference_video_mime_type="video/mp4",
    )
    parts = _build_input_parts(req)
    assert len(parts) == 3
    assert parts[0] == {"type": "text", "text": "Change character's shirt to blue"}
    assert parts[1] == {
        "type": "image",
        "mime_type": "image/png",
        "uri": "gs://bucket/ref.png",
    }
    assert parts[2] == {
        "type": "video",
        "mime_type": "video/mp4",
        "uri": "gs://bucket/base.mp4",
    }


@patch("models.omni.download_from_gcs")
def test_build_input_parts_chat(mock_download: MagicMock) -> None:
    """Test building input parts for multi-turn chat mode."""
    mock_download.return_value = b"video_bytes_resolved"

    history = [
        {"type": "user_input", "content": [{"type": "text", "text": "Start video"}]},
        {
            "type": "model_output",
            "content": [
                {
                    "type": "video",
                    "gcs_uri": "gs://bucket/video.mp4",
                    "mime_type": "video/mp4",
                },
            ],
        },
    ]
    req = OmniVideoGenerationRequest(
        prompt="Make it faster",
        duration_seconds=10,
        aspect_ratio="16:9",
        resolution="720p",
        omni_mode="edit",
        model_version_id="gemini-omni-flash-preview",
        previous_interaction_id="int-123",
        chat_history_json=json.dumps(history),
    )
    parts = _build_input_parts(req)
    assert len(parts) == 3
    assert parts[0] == history[0]
    # Resolved model output containing base64 data
    assert parts[1] == {
        "type": "model_output",
        "content": [
            {
                "type": "video",
                "data": "dmlkZW9fYnl0ZXNfcmVzb2x2ZWQ=",
                "mime_type": "video/mp4",
            },
        ],
    }
    assert parts[2] == {
        "type": "user_input",
        "content": [{"type": "text", "text": "Make it faster"}],
    }
    mock_download.assert_called_once_with("gs://bucket/video.mp4")


def test_extract_video_payload() -> None:
    """Test parsing standard video payload from interaction steps."""
    mock_content = MagicMock()
    mock_content.type = "video"
    mock_content.data = "base64_data_here"

    mock_step = MagicMock()
    mock_step.type = "model_output"
    mock_step.content = [mock_content]

    mock_interaction = MagicMock()
    mock_interaction.id = "int-789"
    mock_interaction.steps = [mock_step]

    video_data, interaction_id = _extract_video_payload(mock_interaction)
    assert video_data == "base64_data_here"
    assert interaction_id == "int-789"


@patch("models.omni.get_omni_client")
@patch("models.omni._save_video_to_gcs")
def test_generate_omni_video_success(
    mock_save: MagicMock,
    mock_get_client: MagicMock,
) -> None:
    """Test generate_omni_video orchestrator on success."""
    req = OmniVideoGenerationRequest(
        prompt="Cinematic city sunset",
        duration_seconds=10,
        aspect_ratio="16:9",
        resolution="720p",
        omni_mode="t2v",
        model_version_id="gemini-omni-flash-preview",
    )

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_content = MagicMock()
    mock_content.type = "video"
    mock_content.data = "encoded_video_data"

    mock_step = MagicMock()
    mock_step.type = "model_output"
    mock_step.content = [mock_content]

    mock_interaction = MagicMock()
    mock_interaction.id = "new-interaction-id"
    mock_interaction.steps = [mock_step]

    mock_client.interactions.create.return_value = mock_interaction
    mock_save.return_value = "gs://bucket/videos/output.mp4"

    gcs_uri, interaction_id = generate_omni_video(req)
    assert gcs_uri == "gs://bucket/videos/output.mp4"
    assert interaction_id == "new-interaction-id"

    mock_client.interactions.create.assert_called_once()
    mock_save.assert_called_once_with("encoded_video_data")


def test_modify_prompt_for_omni_defaults() -> None:
    """Test prompt modification when defaults (16:9, 10s) are selected."""
    res = _modify_prompt_for_omni("A cute dog running", "16:9", 10)
    assert res == "A cute dog running"


def test_modify_prompt_for_omni_custom_aspect() -> None:
    """Test prompt modification when custom aspect ratio is selected."""
    res = _modify_prompt_for_omni("A cute dog running", "9:16", 10)
    assert res == "A cute dog running, aspect ratio 9:16"


def test_modify_prompt_for_omni_custom_duration() -> None:
    """Test prompt modification when custom duration is selected."""
    res = _modify_prompt_for_omni("A cute dog running", "16:9", 6)
    assert res == "A cute dog running, duration 6s"


def test_modify_prompt_for_omni_both_custom() -> None:
    """Test prompt modification when both aspect and duration are custom."""
    res = _modify_prompt_for_omni("A cute dog running", "9:16", 8)
    assert res == "A cute dog running, aspect ratio 9:16, duration 8s"


def test_modify_prompt_for_omni_with_trailing_comma() -> None:
    """Test prompt modification when prompt ends with a comma."""
    res = _modify_prompt_for_omni("A cute dog running,", "9:16", 8)
    assert res == "A cute dog running, aspect ratio 9:16, duration 8s"


@patch("pages.omni.me.state")
@patch("common.storage.generate_upload_signed_url")
def test_on_request_signed_url_video(
    mock_sign: MagicMock, mock_state: MagicMock,
) -> None:
    """Test generating signed URL event handler."""
    from pages.omni import on_request_signed_url_video

    mock_page_state = MagicMock()
    mock_state.return_value = mock_page_state

    mock_sign.return_value = "https://gcs-signed-url.com/upload"

    event = MagicMock()
    event.value = (
        '{"filename": "test_video.mp4", "contentType": "video/mp4", "fileSize": 1024}'
    )

    gen = on_request_signed_url_video(event)
    list(gen)

    assert (
        mock_page_state.video_upload_signed_url == "https://gcs-signed-url.com/upload"
    )
    assert "test_video.mp4" in mock_page_state.video_upload_gcs_uri
    assert mock_page_state.video_upload_error == ""
    mock_sign.assert_called_once()


@patch("pages.omni.me.state")
def test_on_upload_complete_video(mock_state: MagicMock) -> None:
    """Test direct upload completion event handler."""
    from pages.omni import on_upload_complete_video

    mock_page_state = MagicMock()
    mock_state.return_value = mock_page_state

    event = MagicMock()
    event.value = "gs://bucket/uploads/uuid_test_video.mp4"

    gen = on_upload_complete_video(event)
    list(gen)

    assert (
        mock_page_state.reference_video_gcs == "gs://bucket/uploads/uuid_test_video.mp4"
    )
    assert "uuid_test_video.mp4" in mock_page_state.reference_video_uri
    assert mock_page_state.video_upload_signed_url == ""


@patch("pages.omni.me.state")
def test_on_upload_progress_video(mock_state: MagicMock) -> None:
    """Test upload progress tracking event handler."""
    from pages.omni import on_upload_progress_video

    mock_page_state = MagicMock()
    mock_state.return_value = mock_page_state

    event = MagicMock()
    event.value = "45"

    gen = on_upload_progress_video(event)
    list(gen)

    assert mock_page_state.video_upload_progress == 45


@patch("pages.omni.me.state")
def test_on_upload_error_video(mock_state: MagicMock) -> None:
    """Test upload error event handler."""
    from pages.omni import on_upload_error_video

    mock_page_state = MagicMock()
    mock_state.return_value = mock_page_state

    event = MagicMock()
    event.value = "Network timeout"

    gen = on_upload_error_video(event)
    list(gen)

    assert mock_page_state.error_message == "Video upload failed: Network timeout"
    assert mock_page_state.show_error_dialog is True
    assert mock_page_state.video_upload_progress == 0


@patch("pages.omni.me.state")
def test_on_video_select(mock_state: MagicMock) -> None:
    """Test selecting a video from library callback."""
    from components.library.events import LibrarySelectionChangeEvent
    from pages.omni import on_video_select

    mock_page_state = MagicMock()
    mock_state.return_value = mock_page_state

    event = LibrarySelectionChangeEvent(gcs_uri="gs://bucket/library/vid.mp4")

    gen = on_video_select(event)
    list(gen)

    assert mock_page_state.reference_video_gcs == "gs://bucket/library/vid.mp4"
    assert "vid.mp4" in mock_page_state.reference_video_uri
