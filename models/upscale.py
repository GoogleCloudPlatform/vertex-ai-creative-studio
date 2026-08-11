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

"""Upscale model integration."""

import io
import uuid

from google import genai
from google.genai import types
from PIL import Image

from common.analytics import get_logger, track_model_call
from common.storage import download_from_gcs, store_to_gcs
from config.default import Default

cfg = Default()
logger = get_logger(__name__)

UPSCALE_MODEL = "imagen-4.0-upscale-preview"


def get_image_resolution(image_data: bytes | str) -> str:
    """Gets the resolution of an image from GCS URI or bytes."""
    if isinstance(image_data, str) and image_data.startswith("gs://"):
        try:
            image_bytes = download_from_gcs(image_data)
        except Exception as e:
            logger.warning(f"Error downloading image for resolution check: {e}")
            return "Unknown"
    elif isinstance(image_data, bytes):
        image_bytes = image_data
    else:
        return "Unknown"

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            return f"{img.width}x{img.height}"
    except Exception as e:
        logger.warning(f"Error getting resolution: {e}")
        return "Unknown"


def upscale_image(input_gcs_uri: str, upscale_factor: str) -> tuple[str, str, str]:
    """Upscales an image using Imagen 4.0 Upscale.

    Args:
        input_gcs_uri: GCS URI of the image to upscale.
        upscale_factor: 'x2', 'x3', or 'x4'.

    Returns:
        Tuple of (output_gcs_uri, original_resolution, upscaled_resolution)

    """
    billing_units = {
        "upscale_factor": upscale_factor,
        "images_generated": 1,
    }

    with track_model_call(UPSCALE_MODEL, billing_units=billing_units) as ctx:
        client = genai.Client(
            vertexai=True,
            project=cfg.PROJECT_ID,
            location=cfg.LOCATION,
            http_options={"api_version": cfg.VERTEX_API_VERSION},
        )

        # Get original resolution
        original_resolution = get_image_resolution(input_gcs_uri)
        ctx["billing_units"]["original_resolution"] = original_resolution

        response = client.models.upscale_image(
            model=UPSCALE_MODEL,
            image=types.Image(gcs_uri=input_gcs_uri),
            upscale_factor=upscale_factor,
            config=types.UpscaleImageConfig(
                output_mime_type="image/png",
            ),
        )

        if not response.generated_images:
            raise RuntimeError("Upscale failed: No images generated.")

        generated_image = response.generated_images[0].image

        # Try to get bytes from the generated image object
        if hasattr(generated_image, "image_bytes"):
            image_data = generated_image.image_bytes
        elif hasattr(generated_image, "_image_bytes"):
            image_data = generated_image._image_bytes
        else:
            raise RuntimeError(
                f"Could not extract image bytes from response: {type(generated_image)}",
            )

        # Get upscaled resolution
        upscaled_resolution = get_image_resolution(image_data)
        ctx["billing_units"]["upscaled_resolution"] = upscaled_resolution

        # Store to GCS
        file_name = f"upscaled_{uuid.uuid4()}.png"
        output_gcs_uri = store_to_gcs(
            folder="upscaled_images",
            file_name=file_name,
            mime_type="image/png",
            contents=image_data,
        )

        return output_gcs_uri, original_resolution, upscaled_resolution
