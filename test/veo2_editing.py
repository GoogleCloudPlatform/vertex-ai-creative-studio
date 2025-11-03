# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import os
import time
import requests

# --- Configuration ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
OUTPUT_GCS_BUCKET = os.getenv("OUTPUT_GCS", f"{PROJECT_ID}-assets")
VIDEO_EDITING_MODEL = "veo-2.0-edit-001"

# --- Placeholder files for video editing inputs ---
# Please replace these with actual file paths to test the editing features.
SOURCE_VIDEO_PATH = "path/to/your/source_video.mp4"
MASK_VIDEO_PATH = "path/to/your/mask_video.mp4"  # For inpainting


def get_access_token():
    """Gets the access token from the gcloud command."""
    token_command = "gcloud auth print-access-token"
    return os.popen(token_command).read().strip()


def encode_file_to_base64(file_path):
    """Encodes a file to base64."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def poll_operation(operation_name, access_token):
    """Polls a long-running operation and returns the result."""
    print(f"Polling operation: {operation_name}")
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{operation_name}"
    headers = {"Authorization": f"Bearer {access_token}"}
    start_time = time.time()

    while True:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("done", False):
            end_time = time.time()
            print(f"Operation finished in {end_time - start_time:.2f} seconds.")
            if "error" in result:
                print(f"Operation failed: {result['error']}")
                return None
            return result

        print("Operation in progress...")
        time.sleep(15)


def run_video_editing(edit_mode, prompt, source_video_path, mask_video_path=None):
    """Run a video editing job using the REST API."""
    print(f"{'=' * 20} Running {edit_mode} {'=' * 20}")

    if not os.path.exists(source_video_path):
        print(f"Skipping {edit_mode}: Source video not found at '{source_video_path}'")
        return

    if mask_video_path and not os.path.exists(mask_video_path):
        print(f"Skipping {edit_mode}: Mask video not found at '{mask_video_path}'")
        return

    access_token = get_access_token()
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{VIDEO_EDITING_MODEL}:generateVideo"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    source_video_base64 = encode_file_to_base64(source_video_path)

    request_body = {
        "prompt": prompt,
        "sourceVideo": {"video": source_video_base64},
        "editSpec": {"mode": edit_mode},
        "outputGcsUri": f"gs://{OUTPUT_GCS_BUCKET}/",
    }

    if edit_mode == "INPAINTING" and mask_video_path:
        mask_video_base64 = encode_file_to_base64(mask_video_path)
        request_body["editSpec"]["maskVideo"] = {"video": mask_video_base64}

    print(f"Prompt: '{prompt}'")
    response = requests.post(url, headers=headers, json=request_body)

    if response.status_code != 200:
        print(f"Error: {response.status_code} {response.text}")
        return

    operation_name = response.json().get("name")
    if not operation_name:
        print("Failed to get operation name.")
        return

    result = poll_operation(operation_name, access_token)
    if result and "response" in result:
        video_uri = result["response"]["generatedVideos"][0]["gcsUri"]
        print(f"Generated video for {edit_mode}: {video_uri}")


# --- Run Inpainting ---
inpainting_prompt = "a cute robot waving"
run_video_editing(
    edit_mode="INPAINTING",
    prompt=inpainting_prompt,
    source_video_path=SOURCE_VIDEO_PATH,
    mask_video_path=MASK_VIDEO_PATH,
)

# --- Run Outpainting ---
outpainting_prompt = "a beautiful beach in the background"
run_video_editing(
    edit_mode="OUTPAINTING",
    prompt=outpainting_prompt,
    source_video_path=SOURCE_VIDEO_PATH,
)
