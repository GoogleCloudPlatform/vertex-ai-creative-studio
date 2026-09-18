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
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.veo_models import get_models_by_mode
from models.requests import VideoGenerationRequest
from models.veo import generate_video


def _make_fake_operation(uri="gs://fake-bucket/videos/out.mp4"):
    fake_video = MagicMock()
    fake_video.video.uri = uri
    fake_result = MagicMock()
    fake_result.rai_media_filtered_count = 0
    fake_result.generated_videos = [fake_video]
    fake_op = MagicMock()
    fake_op.done = True
    fake_op.error = None
    fake_op.response = "ok"
    fake_op.result = fake_result
    return fake_op


T2V_MODELS = get_models_by_mode("t2v")


@pytest.mark.parametrize(
    "model_config", T2V_MODELS, ids=[m.version_id for m in T2V_MODELS]
)
@patch("models.veo.get_veo_client")
def test_generate_video_forwards_seed_and_keeps_enhancement(
    mock_get_client, model_config
):
    """Seed must reach gen_config_args while prompt enhancement stays on."""
    mock_client = MagicMock()
    mock_client.models.generate_videos.return_value = _make_fake_operation()
    mock_get_client.return_value = mock_client

    request = VideoGenerationRequest(
        prompt="a happy dog running on a sunny beach",
        model_version_id=model_config.version_id,
        aspect_ratio=model_config.supported_aspect_ratios[0],
        resolution=model_config.resolutions[0],
        duration_seconds=model_config.default_duration,
        video_count=model_config.default_samples,
        enhance_prompt=True,
        seed=424242,
        generate_audio=False,
        person_generation="Allow (Adults only)",
    )

    generate_video(request)

    mock_client.models.generate_videos.assert_called_once()
    config = mock_client.models.generate_videos.call_args.kwargs["config"]
    assert config.seed == 424242
    assert config.enhance_prompt is True
