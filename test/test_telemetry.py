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

from unittest.mock import MagicMock, patch

from common.analytics import track_model_call
from common.error_handling import ErrorCategory, GenerationError, classify_error


def test_classify_error_generation_error():
    err = GenerationError(
        "Quota exceeded",
        category=ErrorCategory.CAPACITY_EXHAUSTED,
        code=429,
        retryable=True,
    )
    classified = classify_error(err)
    assert classified["category"] == "CAPACITY_EXHAUSTED"
    assert classified["code"] == 429
    assert classified["retryable"] is True
    assert classified["message"] == "Quota exceeded"


def test_classify_error_exceptions():
    # Quota
    exc1 = Exception("ResourceExhausted: 429 Rate limit exceeded")
    assert classify_error(exc1)["category"] == "CAPACITY_EXHAUSTED"

    # Safety
    exc2 = Exception("Blocked due to safety filters")
    assert classify_error(exc2)["category"] == "SAFETY_FILTER"
    assert classify_error(exc2)["retryable"] is False

    # Timeout
    exc3 = Exception("DeadlineExceeded: 504 Gateway Timeout")
    assert classify_error(exc3)["category"] == "CLIENT_TIMEOUT"

    # Invalid argument
    exc4 = Exception("InvalidArgument: Prompt too long")
    assert classify_error(exc4)["category"] == "INVALID_ARGUMENT"

    # Auth
    exc5 = Exception("PermissionDenied: 403 Forbidden")
    assert classify_error(exc5)["category"] == "AUTH_ERROR"

    # Upstream
    exc6 = Exception("InternalServerError: 500 Service Unavailable")
    assert classify_error(exc6)["category"] == "UPSTREAM_FAILURE"

    # Not Found
    exc8 = Exception("404 GET https://storage.googleapis.com/...: Not Found")
    assert classify_error(exc8)["category"] == "NOT_FOUND"
    assert classify_error(exc8)["code"] == 404
    assert classify_error(exc8)["retryable"] is False

    # Unknown
    exc7 = Exception("Random unexpected issue")
    assert classify_error(exc7)["category"] == "UNKNOWN"


def test_classify_error_false_positives():
    # Ensure parameter names like "block_low_and_above" do not trigger SAFETY_FILTER
    exc_block_param = Exception(
        "Failed processing config with safety_filter_level=block_low_and_above"
    )
    assert classify_error(exc_block_param)["category"] == "UNKNOWN"

    # Ensure URI numbers like "asset_4041_v2.png" do not trigger NOT_FOUND
    exc_uri = Exception("Failed processing asset_4041_v2.png")
    assert classify_error(exc_uri)["category"] == "UNKNOWN"


@patch("common.storage.get_storage_client")
def test_store_to_gcs_bucket_normalization(mock_get_client):
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_client.get_bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_get_client.return_value = mock_client

    from common.storage import store_to_gcs

    # Test raw bucket name with gs:// prefix and path
    uri = store_to_gcs(
        folder="videos",
        file_name="test.mp4",
        mime_type="video/mp4",
        contents=b"data",
        bucket_name="gs://my-test-bucket/subpath",
    )

    mock_client.get_bucket.assert_called_once_with("my-test-bucket")
    assert uri == "gs://my-test-bucket/videos/test.mp4"


@patch("common.analytics.analytics_logger")
def test_track_model_call_success(mock_logger):
    with track_model_call("test-model", pipeline_id="pipe-123") as ctx:
        ctx["billing_units"]["prompt_tokens"] = 100
        ctx["billing_units"]["candidates_tokens"] = 50

    mock_logger.info.assert_called_once()
    _args, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]["extra_data"]

    assert extra["event_type"] == "model_call"
    assert extra["model_name"] == "test-model"
    assert extra["status"] == "success"
    assert extra["pipeline_id"] == "pipe-123"
    assert extra["billing_units"] == {"prompt_tokens": 100, "candidates_tokens": 50}


@patch("common.analytics.analytics_logger")
def test_track_model_call_safety_filter(mock_logger):
    import pytest

    with pytest.raises(Exception, match="Content Filtered"):
        with track_model_call("imagen-4.0") as ctx:
            ctx["billing_units"]["sample_count"] = 1
            raise Exception("Content Filtered: Prompt triggered safety filter")

    mock_logger.info.assert_called_once()
    _args, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]["extra_data"]

    assert extra["status"] == "failure"
    assert extra["error"]["category"] == "SAFETY_FILTER"
    assert extra["error"]["retryable"] is False
    assert extra["billing_units"] == {"sample_count": 1}


@patch("common.analytics.analytics_logger")
def test_track_model_call_upstream_failure(mock_logger):
    import pytest

    with pytest.raises(Exception, match="503 Service Unavailable"):
        with track_model_call("veo-3.1") as ctx:
            ctx["billing_units"]["video_seconds_generated"] = 8
            raise Exception("503 Service Unavailable: Backend error")

    mock_logger.info.assert_called_once()
    _args, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]["extra_data"]

    assert extra["status"] == "failure"
    assert extra["error"]["category"] == "UPSTREAM_FAILURE"
    assert extra["error"]["retryable"] is True
    assert extra["billing_units"] == {"video_seconds_generated": 8}


from models.gemini import _extract_usage_metadata


def test_extract_usage_metadata():
    class DummyUsageMetadata:
        prompt_token_count = 120
        candidates_token_count = 45
        total_token_count = 165

    class DummyResponse:
        usage_metadata = DummyUsageMetadata()

    metadata = _extract_usage_metadata(DummyResponse())
    assert metadata == {
        "prompt_tokens": 120,
        "candidates_tokens": 45,
        "total_tokens": 165,
    }


@patch("common.analytics.analytics_logger")
@patch("google.cloud.texttospeech.TextToSpeechClient")
def test_gemini_tts_telemetry(mock_tts_client, mock_logger):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.audio_content = b"fake_audio_bytes"
    mock_instance.synthesize_speech.return_value = mock_response
    mock_tts_client.return_value = mock_instance

    from models.gemini_tts import synthesize_speech

    result = synthesize_speech(
        "Hello world",
        "Prompt",
        "gemini-tts",
        "en-US-Standard-A",
        "en-US",
    )
    assert result == b"fake_audio_bytes"

    mock_logger.info.assert_called_once()
    args, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]["extra_data"]

    assert extra["model_name"] == "gemini-tts"
    assert extra["billing_units"]["characters_synthesized"] == 11
    assert extra["billing_units"]["voice_name"] == "en-US-Standard-A"
    assert extra["billing_units"]["audio_bytes"] == len(b"fake_audio_bytes")


@patch("common.analytics.analytics_logger")
@patch("google.cloud.texttospeech_v1beta1.TextToSpeechClient")
def test_chirp_3hd_telemetry(mock_tts_client, mock_logger):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.audio_content = b"chirp_audio_data"
    mock_instance.synthesize_speech.return_value = mock_response
    mock_tts_client.return_value = mock_instance

    from models.chirp_3hd import synthesize_chirp_speech

    result = synthesize_chirp_speech("Test speech", "Orus", "en-US")
    assert result == b"chirp_audio_data"

    mock_logger.info.assert_called_once()
    args, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]["extra_data"]

    assert extra["model_name"] == "chirp-3-hd"
    assert extra["billing_units"]["characters_synthesized"] == 11
    assert extra["billing_units"]["voice_name"] == "en-US-Chirp3-HD-Orus"
    assert extra["billing_units"]["audio_bytes"] == len(b"chirp_audio_data")
