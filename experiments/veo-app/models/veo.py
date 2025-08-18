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
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

from common.error_handling import GenerationError
from config.default import Default
from config.veo_models import get_veo_model_config
from models.requests import VideoGenerationRequest

import google.auth
import google.auth.transport.requests


config = Default()


load_dotenv(override=True)

client = genai.Client(
    vertexai=True,
    project=config.VEO_PROJECT_ID,
    location=config.LOCATION,
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
        raise GenerationError(
            f"Unsupported VEO model version: {request.model_version_id}"
        )

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


t2v_video_model = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{config.VEO_PROJECT_ID}/locations/us-central1/publishers/google/models/{config.VEO_MODEL_ID}"
t2v_prediction_endpoint = f"{t2v_video_model}:predictLongRunning"
fetch_endpoint = f"{t2v_video_model}:fetchPredictOperation"
t2v_video_model_exp = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{config.VEO_EXP_PROJECT_ID}/locations/us-central1/publishers/google/models/{config.VEO_EXP_MODEL_ID}"
t2v_prediction_endpoint_exp = f"{t2v_video_model_exp}:predictLongRunning"
fetch_endpoint_exp = f"{t2v_video_model_exp}:fetchPredictOperation"


def compose_videogen_request(
    prompt,
    image_uri,
    gcs_uri,
    seed,
    aspect_ratio,
    sample_count,
    enable_prompt_rewriting,
    duration_seconds,
    last_image_uri,
):
    """Create a JSON Request for Veo"""
    enhance_prompt = "no"
    if enable_prompt_rewriting:
        enhance_prompt = "yes"

    instance = {"prompt": prompt}
    if image_uri:
        instance["image"] = {"gcsUri": image_uri, "mimeType": "png"}
    if last_image_uri:
        instance["lastFrame"] = {"gcsUri": last_image_uri, "mimeType": "png"}
    request = {
        "instances": [instance],
        "parameters": {
            "storageUri": gcs_uri,
            "sampleCount": sample_count,
            "seed": seed,
            "aspectRatio": aspect_ratio,
            # "enablePromptRewriting": enable_prompt_rewriting,
            "durationSeconds": duration_seconds,
            "enhancePrompt": enhance_prompt,
        },
    }
    print(f"VEO REQUEST IS {request}")
    return request


def send_request_to_google_api(api_endpoint, data=None):
    """
    Sends an HTTP request to a Google API endpoint.

    Args:
        api_endpoint: The URL of the Google API endpoint.
        data: (Optional) Dictionary of data to send in the request body (for POST, PUT, etc.).

    Returns:
        The response from the Google API.
    """

    # Get access token calling API
    creds, project = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    access_token = creds.token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(api_endpoint, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def fetch_operation(fetch_endpoint, lro_name):
    """Long Running Operation fetch"""
    print(f"fetching from: {fetch_endpoint}")
    request = {"operationName": lro_name}
    # The generation usually takes 2 minutes. Loop 30 times, around 5 minutes.
    for i in range(60):
        resp = send_request_to_google_api(fetch_endpoint, request)
        if "done" in resp and resp["done"]:
            print("FOUND RESPONSE")
            print(resp)
            return resp
        time.sleep(10)


def image_to_video(
    prompt,
    image_gcs,
    seed,
    aspect_ratio,
    sample_count,
    output_gcs,
    enable_pr,
    duration_seconds,
    model,
):
    image_gcs_new = image_gcs.replace(
        "gs://",
        "https://storage.mtls.cloud.google.com/",
    )

    """Image to video"""
    req = compose_videogen_request(
        prompt,
        image_gcs,
        output_gcs,
        seed,
        aspect_ratio,
        sample_count,
        enable_pr,
        duration_seconds,
        None,
    )

    print(f"REQUEST {image_gcs}")

    prediction_endpoint = t2v_prediction_endpoint
    fetch_ep = fetch_endpoint
    # model = "3.0"
    if model == "3.0":
        prediction_endpoint = t2v_prediction_endpoint_exp
        fetch_ep = fetch_endpoint_exp
    print(f"Fetch EP: {fetch_ep}")
    print(req)
    print(prediction_endpoint)
    print(fetch_ep)

    resp = send_request_to_google_api(prediction_endpoint, req)
    print(resp)
    return fetch_operation(fetch_ep, resp["name"])
