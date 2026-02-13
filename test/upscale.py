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

# upscale example

import os
from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

upscale_model = "imagen-4.0-upscale-preview"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

image = "gs://cloud-samples-data/generative-ai/image/daisy.jpg"

# NOTE: upscale_factor = 'x2', 'x3', 'x4'

upscale = client.models.upscale_image(
    model=upscale_model,
    image=types.Image(gcs_uri=image),
    upscale_factor='x4',
)
upscale.generated_images[0].image.show()