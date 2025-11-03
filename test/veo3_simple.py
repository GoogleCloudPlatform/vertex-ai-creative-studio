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


import os
import time

from google import genai
from google.genai import types

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
OUTPUT_GCS = os.getenv("OUTPUT_GCS", f"{PROJECT_ID}-assets")

video_model = "veo-3.0-generate-preview"
video_model_fast = "veo-3.0-fast-generate-preview"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

prompt = "a garden gnome singing a pop song in a whimsical outdoor garden"

print(f"Prompt: '{prompt}'")
enhance_prompt = True
generate_audio = True

# Generate with the fast model first
print(f"Generating video with model: {video_model_fast}")
start_time_fast = time.time()
operation_fast = client.models.generate_videos(
    model=video_model_fast,
    prompt=prompt,
    config=types.GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=1,
        duration_seconds=8,
        person_generation="allow_adult",
        enhance_prompt=enhance_prompt,
        generate_audio=generate_audio,
        output_gcs_uri=f"gs://{OUTPUT_GCS}",
    ),
)

while not operation_fast.done:
    time.sleep(15)
    operation_fast = client.operations.get(operation_fast)
    print(f"Operation in progress: {operation_fast}")

end_time_fast = time.time()
print(f"Time taken for {video_model_fast}: {end_time_fast - start_time_fast:.2f} seconds")

if operation_fast.response:
    video_fast = operation_fast.result.generated_videos[0].video.uri
    if isinstance(video_fast, str):
        print(f"video {video_fast}")

print("-" * 20)

# Generate with the regular model
print(f"Generating video with model: {video_model}")
start_time = time.time()
operation = client.models.generate_videos(
    model=video_model,
    prompt=prompt,
    config=types.GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=1,
        duration_seconds=8,
        person_generation="allow_adult",
        enhance_prompt=enhance_prompt,
        generate_audio=generate_audio,
        output_gcs_uri=f"gs://{OUTPUT_GCS}",
    ),
)

while not operation.done:
    time.sleep(15)
    operation = client.operations.get(operation)
    print(f"Operation in progress: {operation}")

end_time = time.time()
print(f"Time taken for {video_model}: {end_time - start_time:.2f} seconds")


if operation.response:
    video = operation.result.generated_videos[0].video.uri
    if isinstance(video, str):
        # file_name = video.split("/")[-1]
        print(f"video {video}")
