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

from google import genai
from google.genai.types import (
    Image,
    ProductImage,
    RecontextImageConfig,
    RecontextImageSource,
)

from common.analytics import get_logger, track_model_call
from config.default import Default

cfg = Default()
logger = get_logger(__name__)


def init_client() -> genai.Client:
    """Initializes the GenAI client."""
    return genai.Client(
        vertexai=True,
        project=cfg.PROJECT_ID,
        location=cfg.LOCATION,
        http_options={"api_version": cfg.VERTEX_API_VERSION},
    )


def generate_vto_image(
    person_gcs_uri: str,
    product_gcs_uri: str,
    sample_count: int = 1,
    base_steps: int = 32,
    output_mime_type: str = "image/jpeg",
    person_generation: str = "allow_all",
    safety_filter_level: str = "block_low_and_above",
) -> list[str]:
    """Generates Virtual Try-On images using the Google GenAI SDK.

    Args:
        person_gcs_uri: GCS URI of the person image.
        product_gcs_uri: GCS URI of the product image.
        sample_count: Number of images to generate.
        base_steps: Number of diffusion steps.
        output_mime_type: Desired output MIME type (e.g., "image/jpeg", "image/png").
        person_generation: Person generation mode ('allow_all', 'allow_adult', 'dont_allow').
        safety_filter_level: Safety filter level ('block_low_and_above', 'block_medium_and_above', 'block_only_high').

    Returns:
        List of GCS URIs of the generated images.

    """
    client = init_client()
    model_id = cfg.VTO_MODEL_ID or "vto-1"

    billing_units = {
        "sample_count": sample_count,
        "base_steps": base_steps,
        "safety_filter_level": safety_filter_level,
    }

    with track_model_call(model_id, billing_units=billing_units) as ctx:
        logger.info(f"Calling VTO (GenAI SDK) with model: {model_id}")

        # Define the output GCS folder prefix
        output_gcs_uri_prefix = f"gs://{cfg.GENMEDIA_BUCKET}/vto_results/"

        try:
            response = client.models.recontext_image(
                model=model_id,
                source=RecontextImageSource(
                    person_image=Image(gcs_uri=person_gcs_uri),
                    product_images=[
                        ProductImage(product_image=Image(gcs_uri=product_gcs_uri)),
                    ],
                ),
                config=RecontextImageConfig(
                    number_of_images=sample_count,
                    base_steps=base_steps,
                    output_mime_type=output_mime_type,
                    person_generation=person_generation,
                    safety_filter_level=safety_filter_level,
                    output_gcs_uri=output_gcs_uri_prefix,
                ),
            )

            gcs_uris = []
            if response.generated_images:
                for generated_image in response.generated_images:
                    if generated_image.image.gcs_uri:
                        gcs_uris.append(generated_image.image.gcs_uri)
                    else:
                        logger.warning(
                            "VTO API returned an image without a GCS URI despite output_gcs_uri being set.",
                        )

            ctx["billing_units"]["images_generated"] = len(gcs_uris)
            return gcs_uris

        except Exception as e:
            logger.error(f"Error generating VTO image with GenAI SDK: {e}")
            raise
