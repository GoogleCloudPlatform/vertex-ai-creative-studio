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
import os
import sys
import time
from unittest.mock import patch, MagicMock

# Setup sys.path to allow imports from the parent directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.veo import generate_video
from models.requests import VideoGenerationRequest, APIReferenceImage
from config.default import Default
from config.veo_models import VEO_MODELS, get_veo_model_config

config = Default()

def create_base_request(model_id):
    """Helper to create a valid request based on model config."""
    m_config = get_veo_model_config(model_id)
    return VideoGenerationRequest(
        prompt="a cinematic video of a futuristic city with glowing neon lights",
        duration_seconds=m_config.default_duration,
        video_count=1,
        aspect_ratio=m_config.supported_aspect_ratios[0],
        resolution=m_config.resolutions[0],
        enhance_prompt=True,
        generate_audio=True if "3." in model_id else False,
        model_version_id=model_id,
        person_generation="Allow (Adults only)"
    )

@pytest.mark.integration
def test_full_generation_4k():
    """Validates 4K generation for a GA model."""
    model_id = "3.1"
    req = create_base_request(model_id)
    req.resolution = "4k"
    
    print(f"\nStarting 4K generation with {model_id}...")
    video_uris, resolution = generate_video(req)
    
    assert video_uris
    assert len(video_uris) > 0
    assert video_uris[0].startswith("gs://")
    assert resolution == "4k"
    print(f"SUCCESS: 4K video generated at {video_uris[0]}")

@pytest.mark.integration
def test_full_generation_r2v_fast_preview():
    """Validates R2V generation for the 3.1-fast-preview model."""
    model_id = "3.1-fast-preview"
    req = create_base_request(model_id)
    req.r2v_references = [
        APIReferenceImage(
            gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
            mime_type="image/png"
        )
    ]
    
    print(f"\nStarting R2V generation with {model_id}...")
    video_uris, resolution = generate_video(req)
    
    assert video_uris
    assert len(video_uris) > 0
    assert video_uris[0].startswith("gs://")
    print(f"SUCCESS: R2V video generated at {video_uris[0]}")

@pytest.mark.integration
def test_full_generation_interpolation_all_models():
    """Optionally test interpolation on one model to ensure config parity."""
    model_id = "3.1-fast"
    req = create_base_request(model_id)
    req.reference_image_gcs = "gs://cloud-samples-data/generative-ai/image/flowers.png"
    req.reference_image_mime_type = "image/png"
    req.last_reference_image_gcs = "gs://cloud-samples-data/generative-ai/image/daisy.jpg"
    req.last_reference_image_mime_type = "image/jpeg"
    
    print(f"\nStarting Interpolation with {model_id}...")
    video_uris, resolution = generate_video(req)
    
    assert video_uris
    assert len(video_uris) > 0
    assert video_uris[0].startswith("gs://")
    print(f"SUCCESS: Interpolation video generated at {video_uris[0]}")

if __name__ == "__main__":
    pytest.main([__file__, "-m", "integration", "-s"])