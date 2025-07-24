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

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from common.error_handling import GenerationError
from config.default import Default
from config.veo_models import get_veo_model_config
from models.requests import VideoGenerationRequest

config = Default()


load_dotenv(override=True)

client = genai.Client(
    vertexai=True, project=config.VEO_PROJECT_ID, location=config.LOCATION,
)

# Map for person generation options
PERSON_GENERATION_MAP = {
        "Allow (All ages)": "allow_all",
        "Allow (Adults only)": "allow_adult",
        "Don't Allow": "dont_allow",
    }

def generate_video(request: VideoGenerationRequest) -> tuple[str, str]:
    """Generate a video based on a request object using the genai SDK.
    This function handles text-to-video, image-to-video, and interpolation.
    """
    model_config = get_veo_model_config(request.model_version_id)
    if not model_config:
        raise GenerationError(f"Unsupported VEO model version: {request.model_version_id}")


    # Prepare Generation Configuration
    enhance_prompt_for_api = (
        True if request.model_version_id.startswith("3.") else request.enhance_prompt
    )
    gen_config_args = {
        "aspect_ratio": request.aspect_ratio,
        "number_of_videos": 1,
        "duration_seconds": request.duration_seconds,
        "enhance_prompt": enhance_prompt_for_api,
        "output_gcs_uri": f"gs://{config.VIDEO_BUCKET}",
        "resolution": request.resolution,
        "person_generation": PERSON_GENERATION_MAP.get(
            request.person_generation, "allow_all"
        ),
    }
    if request.negative_prompt:
        gen_config_args["negative_prompt"] = request.negative_prompt

    # Prepare Image and Video Inputs
    image_input = None
    # Check for interpolation (first and last frame)
    if request.reference_image_gcs and request.last_reference_image_gcs:
        print("Mode: Interpolation")
        image_input = types.Image(
            gcs_uri=request.reference_image_gcs,
            mime_type=request.reference_image_mime_type,
        )
        gen_config_args["last_frame"] = types.Image(
            gcs_uri=request.last_reference_image_gcs,
            mime_type=request.last_reference_image_mime_type,
        )

    # Check for standard image-to-video
    elif request.reference_image_gcs:
        print("Mode: Image-to-Video")
        image_input = types.Image(
            gcs_uri=request.reference_image_gcs,
            mime_type=request.reference_image_mime_type,
        )
    else:
        print("Mode: Text-to-Video")

    gen_config = types.GenerateVideosConfig(**gen_config_args)

    # Call the API
    try:
        operation = client.models.generate_videos(
            model=model_config.model_name,
            prompt=request.prompt,
            config=gen_config,
            image=image_input,
        )

        print("Polling video generation operation...")
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)
            print(f"Operation in progress: {operation.name}")

        if operation.error:
            error_details = str(operation.error)
            print(f"Video generation failed with error: {error_details}")
            raise GenerationError(f"API Error: {error_details}")

        if operation.response:
            if (
                hasattr(operation.result, "rai_media_filtered_count")
                and operation.result.rai_media_filtered_count > 0
            ):
                filter_reason = operation.result.rai_media_filtered_reasons[0]
                raise GenerationError(f"Content Filtered: {filter_reason}")

            if (
                hasattr(operation.result, "generated_videos")
                and operation.result.generated_videos
            ):
                video_uri = operation.result.generated_videos[0].video.uri
                print(f"Successfully generated video: {video_uri}")
                return video_uri, request.resolution
            else:
                raise GenerationError(
                    "API reported success but no video URI was found in the response."
                )
        else:
            raise GenerationError(
                "Unexpected API response structure or operation not done."
            )

    except Exception as e:
        print(f"An unexpected error occurred in generate_video: {e}")
        raise GenerationError(f"An unexpected error occurred: {e}") from e
