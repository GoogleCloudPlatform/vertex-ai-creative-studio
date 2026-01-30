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

import logging
import os
import sys

from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.error_handling import GenerationError
from models.requests import VideoGenerationRequest
from models.veo import generate_video

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_veo_extension(
    input_video_gcs: str, model_id: str = "veo-3.1-fast-generate-preview"
):
    """
    Test the Veo video extension capability.
    """
    logger.info(f"--- Starting Veo Extension Test ---")
    logger.info(f"Input Video: {input_video_gcs}")
    logger.info(f"Model: {model_id}")

    # Create a mock request
    # Note: We are explicitly setting duration_seconds to 7 based on the error message
    request = VideoGenerationRequest(
        prompt="A continuation of the scene, cinematic lighting",
        model_version_id="3.1-fast-preview",  # Maps to the config ID
        aspect_ratio="16:9",
        resolution="720p",
        duration_seconds=7,
        video_count=1,
        enhance_prompt=False,
        generate_audio=True,
        person_generation="allow_all",
        video_input_gcs=input_video_gcs,
        video_input_mime_type="video/mp4",
    )

    try:
        logger.info("Sending request to generate_video...")
        video_uris, resolution = generate_video(request)

        logger.info("--- Generation Successful ---")
        logger.info(f"Generated Video URIs: {video_uris}")
        logger.info(f"Resolution: {resolution}")

    except GenerationError as e:
        logger.error(f"--- Generation Failed ---")
        logger.error(f"Error: {e}")
    except Exception as e:
        logger.error(f"--- Unexpected Error ---")
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    # Usage: python test/test_veo_extension.py [input_video_uri] [output_bucket_name]

    # 1. Input Video
    if len(sys.argv) > 1:
        input_video = sys.argv[1]
    else:
        # Default to a known accessible video
        # gs://cloud-samples-data/generative-ai/video/flower.mp4
        input_video = "gs://genai-blackbelt-fishfooding-assets/videos/flower.mp4"

    # 2. Output Bucket (Optional)
    if len(sys.argv) > 2:
        target_bucket = sys.argv[2]
        logger.info(f"Overriding output bucket to: {target_bucket}")

        # Patch the config in models.veo
        from models import veo

        veo.config.VIDEO_BUCKET = target_bucket

    test_veo_extension(input_video)
