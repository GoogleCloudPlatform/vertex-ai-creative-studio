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

import argparse
import os
import time

from google import genai
from google.genai import types

# --- Configuration ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
OUTPUT_GCS_BUCKET = os.getenv("OUTPUT_GCS", f"{PROJECT_ID}-assets")
video_model = "veo-2.0-generate-001"

# --- Placeholder files for image/video inputs ---
# Please replace these with actual file paths to test the corresponding features.
I2V_GCS_URI = "gs://genai-blackbelt-fishfooding-assets/images/1747011785204/sample_0.png"  # "gs://your-bucket/path/to/your/image.png"
INTERPOLATE_FIRST_FRAME_GCS_URI = "gs://genai-blackbelt-fishfooding-assets/images/1747012074021/sample_0.png"  # "gs://your-bucket/path/to/your/first_frame.png"
INTERPOLATE_LAST_FRAME_GCS_URI = "gs://genai-blackbelt-fishfooding-assets/images/1747012879097/sample_0.png"  # "gs://your-bucket/path/to/your/last_frame.png"


# --- Initialize Client ---
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def poll_operation(operation, description=""):
    """Polls a long-running operation and prints its status."""
    print(f"Polling operation for {description}...")
    start_time = time.time()
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(f"Operation in progress: {operation.name}")
    end_time = time.time()
    print(f"Time taken for {description}: {end_time - start_time:.2f} seconds")

    if operation.error:
        print(f"Error during {description}: {operation.error}")
        return None

    if operation.response:
        video_uri = operation.result.generated_videos[0].video.uri
        print(f"Generated video for {description}: {video_uri}")
        return video_uri
    return None


def main():
    parser = argparse.ArgumentParser(description="Run specific steps of the VEO generation process.")
    parser.add_argument(
        "--step",
        type=int,
        nargs="+",
        choices=[1, 2, 3, 4],
        help="Which step(s) to run. If not specified, all steps are run.",
    )
    args = parser.parse_args()
    run_all = not args.step
    steps = args.step or []

    generated_video_gcs_uri = None

    # --- 1. Generate (Text-to-Video) ---
    if run_all or 1 in steps:
        print("\n" + "=" * 20 + " 1. Text-to-Video Generation " + "=" * 20)
        t2v_prompt = "a cat reading a book"
        print(f"Prompt: '{t2v_prompt}'")
        t2v_operation = client.models.generate_videos(
            model=video_model,
            prompt=t2v_prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="16:9",
                output_gcs_uri=f"gs://{OUTPUT_GCS_BUCKET}",
                number_of_videos=1,
                duration_seconds=5,
                person_generation="dont_allow",
                enhance_prompt=True,
            ),
        )
        generated_video_gcs_uri = poll_operation(t2v_operation, "Text-to-Video")

    # --- 2. Image-to-Video ---
    if run_all or 2 in steps:
        print("\n" + "=" * 20 + " 2. Image-to-Video Generation " + "=" * 20)
        if I2V_GCS_URI and "gs://" in I2V_GCS_URI:
            i2v_prompt = "the camera slowly zooms out from this image"
            print(f"Prompt: '{i2v_prompt}'")
            print(f"Input Image: '{I2V_GCS_URI}'")
            i2v_operation = client.models.generate_videos(
                model=video_model,
                prompt=i2v_prompt,
                image=types.Image(gcs_uri=I2V_GCS_URI, mime_type="image/png"),
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    output_gcs_uri=f"gs://{OUTPUT_GCS_BUCKET}",
                    number_of_videos=1,
                    duration_seconds=5,
                    person_generation="allow_adult",
                    enhance_prompt=True,
                ),
            )
            poll_operation(i2v_operation, "Image-to-Video")
        else:
            print(
                f"Skipping Image-to-Video: Input GCS URI not found or invalid in '{I2V_GCS_URI}'"
            )
            print("Please update the I2V_GCS_URI variable to test this feature.")

    # --- 3. Interpolate (First and Last Frame) ---
    if run_all or 3 in steps:
        print("\n" + "=" * 20 + " 3. Interpolation " + "=" * 20)
        if (
            INTERPOLATE_FIRST_FRAME_GCS_URI
            and "gs://" in INTERPOLATE_FIRST_FRAME_GCS_URI
            and INTERPOLATE_LAST_FRAME_GCS_URI
            and "gs://" in INTERPOLATE_LAST_FRAME_GCS_URI
        ):
            interpolate_prompt = (
                "a hand reaches in and places a glass of milk next to the plate of cookies"
            )
            print(f"Prompt: '{interpolate_prompt}'")
            print(f"First Frame: '{INTERPOLATE_FIRST_FRAME_GCS_URI}'")
            print(f"Last Frame: '{INTERPOLATE_LAST_FRAME_GCS_URI}'")
            interpolate_operation = client.models.generate_videos(
                model=video_model,
                prompt=interpolate_prompt,
                image=types.Image(
                    gcs_uri=INTERPOLATE_FIRST_FRAME_GCS_URI, mime_type="image/png"
                ),
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    last_frame=types.Image(
                        gcs_uri=INTERPOLATE_LAST_FRAME_GCS_URI, mime_type="image/png"
                    ),
                    number_of_videos=1,
                    duration_seconds=7,
                    person_generation="allow_adult",
                    enhance_prompt=True,
                    output_gcs_uri=f"gs://{OUTPUT_GCS_BUCKET}",
                ),
            )
            poll_operation(interpolate_operation, "Interpolation")
        else:
            print("Skipping Interpolation: Input GCS URIs not found or invalid.")
            print(
                "Please update INTERPOLATE_FIRST_FRAME_GCS_URI and INTERPOLATE_LAST_FRAME_GCS_URI to test this feature."
            )

    # --- 4. Extend Video ---
    if run_all or 4 in steps:
        print("\n" + "=" * 20 + " 4. Video Extension " + "=" * 20)
        if generated_video_gcs_uri:
            extend_prompt = "the cat closes the book and looks at the camera"
            print(f"Prompt: '{extend_prompt}'")
            print(f"Input Video: '{generated_video_gcs_uri}'")
            extend_operation = client.models.generate_videos(
                model=video_model,
                prompt=extend_prompt,
                video=types.Video(uri=generated_video_gcs_uri),
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    output_gcs_uri=f"gs://{OUTPUT_GCS_BUCKET}",
                    number_of_videos=1,
                    duration_seconds=4,  # Extend duration must be 4-7 seconds
                    person_generation="dont_allow",
                    enhance_prompt=True,
                ),
            )
            poll_operation(extend_operation, "Video Extension")
        else:
            print("Skipping Video Extension: No initial video was generated in step 1.")


if __name__ == "__main__":
    main()
