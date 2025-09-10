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

import base64
import logging
import uuid

from google import genai
from google.api_core.exceptions import GoogleAPIError
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic import PredictResponse

from common.storage import store_to_gcs
from common.utils import https_url_to_gcs_uri
from config.default import Default
from models.model_setup import GeminiModelSetup, VtoModelSetup

cfg = Default()


def generate_vto_image_genai(
    person_gcs_url: str, product_gcs_url: str, sample_count: int
) -> list[str]:
    """Generates a VTO image using the google.genai client."""
    client = GeminiModelSetup.init()
    model_name = f"publishers/google/models/{cfg.VTO_MODEL_ID}"

    person_image_part = genai.types.Part.from_uri(
        file_uri=person_gcs_url,
        mime_type="image/png",
    )
    product_image_part = genai.types.Part.from_uri(
        file_uri=product_gcs_url,
        mime_type="image/png",
    )

    # Call generate_content on the client's model endpoint, not a GenerativeModel instance
    response = client.models.generate_content(
        model=model_name,
        contents=[person_image_part, product_image_part],
    )

    gcs_uris = []
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.file_data:
                print(f"{part.file_data.uri}")
                gcs_uris.append(part.file_data.uri)

    return gcs_uris


def generate_vto_image(
    person_gcs_url: str, product_gcs_url: str, sample_count: int, base_steps: int
) -> list[str]:
    """Generates a VTO image."""

    try:
        client_options = {"api_endpoint": f"{cfg.LOCATION}-aiplatform.googleapis.com"}
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    except Exception as client_err:
        print(f"Failed to create PredictionServiceClient: {client_err}")
        raise ValueError(
            f"Configuration error: Failed to initialize prediction client. Details: {str(client_err)}"
        ) from client_err

    model_endpoint = f"projects/{cfg.PROJECT_ID}/locations/{cfg.LOCATION}/publishers/google/models/{cfg.VTO_MODEL_ID}"

    instance = {
        "personImage": {
            "image": {
                "gcsUri": https_url_to_gcs_uri(person_gcs_url)
            }
        },
        "productImages": [
            {
                "image": {
                    "gcsUri": https_url_to_gcs_uri(product_gcs_url)
                }
            }
        ],
    }

    if base_steps == 0:
        base_steps = 32

    parameters = {
        "sampleCount": sample_count,
        "baseSteps": base_steps,
    }

    try:
        response = client.predict(
            endpoint=model_endpoint, instances=[instance], parameters=parameters
        )

        if not response.predictions:
            raise ValueError(
                "VTO API returned an unexpected response (no predictions)."
            )

        gcs_uris = []
        unique_id = uuid.uuid4()
        for i, prediction in enumerate(response.predictions):
            if not prediction.get("bytesBase64Encoded"):
                raise ValueError("VTO API returned a prediction with no image data.")

            encoded_mask_string = prediction["bytesBase64Encoded"]
            mask_bytes = base64.b64decode(encoded_mask_string)

            gcs_uri = store_to_gcs(
                folder="vto_results",
                file_name=f"vto_result_{unique_id}-{i}_.png",
                mime_type="image/png",
                contents=mask_bytes,
                decode=False,
            )
            gcs_uris.append(gcs_uri)

        return gcs_uris

    except GoogleAPIError as e:
        logging.error("VTO API Error: %s", e)
        raise
    except Exception as e:
        logging.error("An unexpected error occurred during VTO image generation: %s", e)
        raise


def call_virtual_try_on(
    person_image_bytes=None,
    product_image_bytes=None,
    person_image_uri=None,
    product_image_uri=None,
    sample_count=1,
    prompt=None,
    product_description=None,
) -> PredictResponse:
    instances = []
    if person_image_uri and product_image_uri:
        instance = {
            "personImage": {"image": {"gcsUri": person_image_uri}},
            "productImages": [{"image": {"gcsUri": product_image_uri}}],
        }
    elif person_image_bytes and product_image_bytes:
        instance = {
            "personImage": {"image": {"bytesBase64Encoded": person_image_bytes}},
            "productImages": [{"image": {"bytesBase64Encoded": product_image_bytes}}],
        }
    else:
        raise ValueError(
            "Both person_image_bytes and product_image_bytes or both person_image_uri and product_image_uri must be set."
        )
    # if prompt:
    #     instance["prompt"] = prompt

    # if product_description is not None and product_description != "":
    #     instance["productImages"][0]["productConfig"] = {
    #         "productDescription": product_description
    #     }

    instances.append(instance)
    parameters = {
        "storageUri": f"gs://{cfg.GENMEDIA_BUCKET}/vto",
        "sampleCount": sample_count,
    }

    client, model_endpoint = VtoModelSetup.init()

    response = client.predict(
        endpoint=model_endpoint, instances=instances, parameters=parameters
    )

    return response