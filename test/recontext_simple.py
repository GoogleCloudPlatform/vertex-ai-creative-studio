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

"""
Product Recontextualization brings Google's cutting edge Imagen model to generate high quality images of products "recontextualized" in new scenes and backgrounds.
you will be exploring the features of Imagen Product Recontextualization using the Vertex AI Python SDK.
You will

* Generate images by providing images of a product
  * (Optional) Set a product description
* Supported product categories
  * business and industrial
  * clothing
  * furniture
  * garden and yard
  * health and beauty
  * jewelry
  * shoes
  * sporting goods
  * toys and games

Product recontextualization using Imagen with PredictionServiceClient
"""

import base64
import io
import os
import re
import timeit
from typing import Any, Dict

from google.cloud import aiplatform
from google.cloud.aiplatform.gapic import PredictResponse

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
RECONTEXT = "imagen-product-recontext-preview-06-30"
api_regional_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
model_endpoint = (
    f"projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/{RECONTEXT}"
)
OUTPUT_GCS = os.getenv(
    "OUTPUT_GCS", f"gs://{PROJECT_ID}-assets",
)  # gs:// prefix required

client_options = {"api_endpoint": api_regional_endpoint}
client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)


def call_product_recontext(
    image_bytes_list=None,
    image_uris_list=None,
    prompt=None,
    product_description=None,
    disable_prompt_enhancement: bool = False,
    sample_count: int = 1,
    base_steps=None,
    safety_setting=None,
    person_generation=None,
    output_gcs=None,
) -> PredictResponse:
    instances = []

    instance: Dict[str, Any] = {"productImages": []}

    if image_bytes_list:
        for product_image_bytes in image_bytes_list:
            product_image = {"image": {"bytesBase64Encoded": product_image_bytes}}
            instance["productImages"].append(product_image)

    if image_uris_list:
        for product_image_uri in image_uris_list:
            product_image = {"image": {"gcsUri": product_image_uri}}
            instance["productImages"].append(product_image)

    if len(instance["productImages"]) == 0:
        raise ValueError(
            "No product images provided. At least one image must be provided."
        )

    if product_description:
        instance["productImages"][0]["productConfig"] = {
            "productDescription": product_description
        }

    if prompt:
        instance["prompt"] = prompt

    parameters = {"sampleCount": sample_count}

    if base_steps:
        parameters["baseSteps"] = base_steps

    if safety_setting:
        parameters["safetySetting"] = safety_setting

    if person_generation:
        parameters["personGeneration"] = person_generation

    if disable_prompt_enhancement:
        parameters["enhancePrompt"] = False
    
    if output_gcs:
        parameters["storageUri"] = output_gcs

    instances.append(instance)

    start = timeit.default_timer()

    response = client.predict(
        endpoint=model_endpoint, instances=instances, parameters=parameters
    )
    end = timeit.default_timer()
    print(f"Product Recontextualization took {end - start:.2f}s.")

    return response


prompt = ""
product_description = ""

# Parameters
disable_prompt_enhancement = False
sample_count = 1  # 1-4
base_steps = None
safety_setting = "block_low_and_above"  # ["block_low_and_above", "block_medium_and_above", "block_only_high", "block_none"]
person_generation = "allow_adult"  # ["dont_allow", "allow_adult", "allow_all"]


product_1 = "gs://genai-blackbelt-fishfooding-assets/vto_product_images/product_hawaiian_shirt.png"
product_2 = "gs://genai-blackbelt-fishfooding-assets/images/generated_images/1752171998606/sample_0.png"
product_3 = "gs://genai-blackbelt-fishfooding-assets/uploads/girlwithapearlearing_vermeer.jpg"

r = call_product_recontext(
    prompt=prompt,
    #image_bytes_list=image_bytes_list,
    image_uris_list=[
        product_1, product_2, product_3,
    ],
    product_description=product_description,
    disable_prompt_enhancement=disable_prompt_enhancement,
    sample_count=sample_count,
    base_steps=base_steps,
    safety_setting=safety_setting,
    person_generation=person_generation,
    output_gcs=OUTPUT_GCS,
)
print(r)

print(list(r.predictions))
