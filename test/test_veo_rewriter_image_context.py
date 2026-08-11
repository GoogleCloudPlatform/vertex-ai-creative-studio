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

"""Unit tests for image-aware Veo prompt rewriting (issue #1642).

These are fully mocked -- no live Gemini/GCS call is made. They assert that
reference image parts reach the ``contents=`` argument of the underlying model
client when images are supplied, remain absent when they are not (backward
compatible), and that the multimodal call falls back to text-only on failure.
"""

import os
from unittest.mock import MagicMock, patch

# Dummy env vars so model client init succeeds at import time.
os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("LOCATION", "us-central1")
os.environ.setdefault("VEO_PROJECT_ID", "test-project")
os.environ.setdefault("VEO_LOCATION", "us-central1")

from google.genai import types  # noqa: E402

import models.gemini as gemini  # noqa: E402


def _mock_response(text: str = "rewritten prompt") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.usage_metadata = None
    return resp


def _image_parts(contents) -> list:
    """Return the Part.from_uri entries in a contents payload."""
    if isinstance(contents, str):
        return []
    return [p for p in contents if isinstance(p, types.Part)]


def test_rewriter_text_only_when_no_images():
    """Absent/empty images -> contents is the plain text string (unchanged path)."""
    with patch.object(gemini.client.models, "generate_content") as mock_gen:
        mock_gen.return_value = _mock_response()

        result = gemini.rewriter("a cat", "REWRITE:")

        assert result == "rewritten prompt"
        assert mock_gen.call_count == 1
        contents = mock_gen.call_args.kwargs["contents"]
        assert isinstance(contents, str)
        assert "a cat" in contents


def test_rewriter_attaches_image_parts_when_images_present():
    """Supplied images -> Part.from_uri parts reach contents with correct uri/mime."""
    with patch.object(gemini.client.models, "generate_content") as mock_gen:
        mock_gen.return_value = _mock_response()

        images = [
            ("gs://bucket/first.png", "image/png"),
            ("gs://bucket/last.jpg", "image/jpeg"),
        ]
        result = gemini.rewriter("a cat", "REWRITE:", images=images)

        assert result == "rewritten prompt"
        contents = mock_gen.call_args.kwargs["contents"]
        assert isinstance(contents, list)
        # First element is the text prompt, followed by image parts.
        assert contents[0] == "REWRITE: a cat"
        parts = _image_parts(contents)
        assert len(parts) == 2
        uris = {p.file_data.file_uri for p in parts}
        mimes = {p.file_data.mime_type for p in parts}
        assert uris == {"gs://bucket/first.png", "gs://bucket/last.jpg"}
        assert mimes == {"image/png", "image/jpeg"}


def test_rewriter_skips_empty_uris():
    """Empty URIs are dropped; only real references become parts."""
    with patch.object(gemini.client.models, "generate_content") as mock_gen:
        mock_gen.return_value = _mock_response()

        images = [("gs://bucket/first.png", "image/png"), ("", "")]
        gemini.rewriter("a cat", "REWRITE:", images=images)

        contents = mock_gen.call_args.kwargs["contents"]
        assert len(_image_parts(contents)) == 1


def test_rewriter_falls_back_to_text_only_on_multimodal_failure():
    """If the multimodal call fails, retry text-only rather than crashing."""
    with patch.object(gemini.client.models, "generate_content") as mock_gen:
        mock_gen.side_effect = [
            Exception("model does not support image input"),
            _mock_response("fallback text"),
        ]

        images = [("gs://bucket/first.png", "image/png")]
        result = gemini.rewriter("a cat", "REWRITE:", images=images)

        assert result == "fallback text"
        assert mock_gen.call_count == 2
        # Second (fallback) call must be text-only.
        fallback_contents = mock_gen.call_args_list[1].kwargs["contents"]
        assert isinstance(fallback_contents, str)


def test_rewriter_text_only_failure_raises():
    """A pure text-only failure (no images) propagates -- no silent swallow.

    ``rewriter`` is wrapped with a tenacity ``@retry(stop_after_attempt(3))``,
    so a permanent failure is attempted 3 times before re-raising.
    """
    with patch.object(gemini.client.models, "generate_content") as mock_gen:
        mock_gen.side_effect = Exception("boom")

        try:
            gemini.rewriter("a cat", "REWRITE:")
        except Exception as e:
            assert "boom" in str(e)
        else:
            raise AssertionError("expected rewriter to raise on text-only failure")
        assert mock_gen.call_count == 3
