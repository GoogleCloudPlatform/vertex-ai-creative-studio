# Copyright 2024 Google LLC
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

# import json

# from google.cloud.aiplatform import telemetry
# from typing import TypedDict # Remove if not used elsewhere in this file


# from models.model_setup import (
#    ImagenModelSetup,
# )

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.analytics import get_logger, track_model_call
from config.default import Default

logger = get_logger(__name__)

# class ImageModel(TypedDict): # Remove this definition
#     """Defines Models For Image Generation."""
#
#     display: str
#     model_name: str


class ImagenModelSetup:
    """Imagen model setup"""

    @staticmethod
    def init(
        project_id: str | None = None,
        location: str | None = None,
        model_id: str | None = None,
    ):
        """Init method"""
        config = Default()
        if not project_id:
            project_id = config.PROJECT_ID
        if not location:
            location = config.LOCATION
        if not model_id:
            model_id = config.MODEL_ID
        if None in [project_id, location, model_id]:
            raise ValueError("All parameters must be set.")
        logger.info(f"initiating genai client with {project_id} in {location}")
        client = genai.Client(
            vertexai=config.INIT_VERTEX,
            project=project_id,
            location=location,
            http_options={"api_version": config.VERTEX_API_VERSION},
        )
        return client


@retry(
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=10,
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions for robustness
    reraise=True,  # re-raise the last exception if all retries fail
)
def generate_images(
    model: str,
    prompt: str,
    number_of_images: int,
    aspect_ratio: str,
    negative_prompt: str,
):
    """Imagen image generation with Google GenAI client"""
    client = ImagenModelSetup.init(model_id=model)
    cfg = Default()  # Instantiate Default config to access IMAGE_BUCKET

    # Define a GCS path for outputting generated images
    gcs_output_directory = f"gs://{cfg.IMAGE_BUCKET}/{cfg.IMAGEN_GENERATED_SUBFOLDER}"

    try:
        logger.info(
            f"models.image_models.generate_images: Requesting {number_of_images} images for model {model} with output to {gcs_output_directory}",
        )
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=number_of_images,
                include_rai_reason=True,
                output_gcs_uri=gcs_output_directory,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
            ),
        )

        # Diagnostic logging for the response
        if (
            response
            and hasattr(response, "generated_images")
            and response.generated_images
        ):
            logger.info(
                f"models.image_models.generate_images: Received {len(response.generated_images)} generated_images.",
            )
            for i, gen_img in enumerate(response.generated_images):
                if hasattr(gen_img, "image") and gen_img.image:
                    if not gen_img.image.gcs_uri:
                        logger.warning(
                            f"models.image_models.generate_images: Image {i} has NO gcs_uri. Image object: {gen_img.image}",
                        )
                    else:
                        logger.info(
                            f"models.image_models.generate_images: Image {i} has gcs_uri: {gen_img.image.gcs_uri}",
                        )
                    if not gen_img.image.image_bytes:
                        logger.warning(
                            f"models.image_models.generate_images: Image {i} has NO image_bytes.",
                        )
                elif hasattr(gen_img, "error"):
                    logger.error(
                        f"models.image_models.generate_images: GeneratedImage {i} has an error: {getattr(gen_img, 'error', 'Unknown error')}",
                    )
                else:
                    logger.warning(
                        f"models.image_models.generate_images: GeneratedImage {i} has no .image attribute or it's None. Full GeneratedImage object: {gen_img}",
                    )
        elif response and hasattr(response, "error"):
            logger.error(
                f"models.image_models.generate_images: API response contains an error: {getattr(response, 'error', 'Unknown error')}",
            )
        else:
            logger.warning(
                f"models.image_models.generate_images: Response has no generated_images or is empty. Full response: {response}",
            )

        return response
    except Exception as e:
        logger.error(f"models.image_models.generate_images: API call failed: {e}")
        raise


def generate_images_from_prompt(
    input_txt: str,
    current_model_name: str,
    image_count: int,
    negative_prompt: str,
    prompt_modifiers_segment: str,
    aspect_ratio: str,
) -> list[str]:
    """Generates images based on the input prompt and parameters.
    Returns a list of image URIs. Does not directly modify PageState.
    """
    full_prompt = f"{input_txt}, {prompt_modifiers_segment}"
    billing_units = {
        "sample_count": image_count,
        "aspect_ratio": aspect_ratio,
    }
    with track_model_call(
        model_name=current_model_name,
        billing_units=billing_units,
        prompt=full_prompt,
        negative_prompt=negative_prompt,
    ) as ctx:
        response = generate_images(
            model=current_model_name,
            prompt=full_prompt,
            number_of_images=image_count,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
        )
        generated_uris = [
            img.image.gcs_uri
            for img in response.generated_images
            if hasattr(img, "image") and hasattr(img.image, "gcs_uri")
        ]
        ctx["billing_units"]["images_generated"] = len(generated_uris)
        return generated_uris


def generate_virtual_models(prompt: str, num_images: int) -> list[str]:
    """Generates multiple virtual model images and saves them to GCS.

    Args:
        prompt: The prompt to generate the images.
        num_images: The number of images to generate.

    Returns:
        A list of GCS URIs for the generated images.

    """
    response = generate_images(
        model=Default().MODEL_IMAGEN4_FAST,
        prompt=prompt,
        number_of_images=num_images,
        aspect_ratio="1:1",
        negative_prompt="",  # Assuming no negative prompt for this case
    )
    generated_uris = [
        img.image.gcs_uri
        for img in response.generated_images
        if hasattr(img, "image") and hasattr(img.image, "gcs_uri")
    ]
    return generated_uris


def generate_image_for_vto(prompt: str) -> bytes:
    """Generates a single, randomized virtual model and returns the image bytes.
    This function is designed to be a non-breaking replacement for the original VTO
    workflow, ensuring backward compatibility.
    """
    # Use the VirtualModelGenerator to create a single random prompt
    from models.virtual_model_generator import DEFAULT_PROMPT, VirtualModelGenerator

    # The VTO page passes a simple prompt, so we use the generator with the default template
    generator = VirtualModelGenerator(DEFAULT_PROMPT)
    generator.randomize_all()
    # Set a default variant for the VTO page
    generator.set_value(
        "variant",
        "facing forward with a natural, relaxed posture and a neutral expression",
    )

    random_prompt = generator.build_prompt()

    logger.info(f"Generated random prompt for VTO: {random_prompt}")

    cfg = Default()
    client = ImagenModelSetup.init(model_id=cfg.MODEL_IMAGEN4_FAST)
    response = client.models.generate_images(
        model=cfg.MODEL_IMAGEN4_FAST,
        prompt=random_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
        ),
    )
    if response.generated_images and response.generated_images[0].image.image_bytes:
        return response.generated_images[0].image.image_bytes
    raise ValueError("Image generation failed or returned no data.")


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def edit_image(
    model: str,
    prompt: str,
    edit_mode: str,
    mask_mode: str,
    reference_image_bytes: bytes,
    number_of_images: int,
):
    """Edits an image using the Google GenAI client."""
    billing_units = {
        "sample_count": number_of_images,
        "edit_mode": edit_mode,
        "mask_mode": mask_mode,
    }
    with track_model_call(model, billing_units=billing_units) as ctx:
        client = ImagenModelSetup.init(model_id=model)
        cfg = Default()
        gcs_output_directory = f"gs://{cfg.IMAGE_BUCKET}/{cfg.IMAGEN_EDITED_SUBFOLDER}"

        raw_ref_image = types.RawReferenceImage(
            reference_id=1,
            reference_image=reference_image_bytes,
        )

        mask_ref_image = types.MaskReferenceImage(
            reference_id=2,
            config=types.MaskReferenceConfig(
                mask_mode=mask_mode,
                mask_dilation=0,
            ),
        )

        try:
            logger.info(
                f"models.image_models.edit_image: Requesting {number_of_images} edited images for model {model} with output to {gcs_output_directory}",
            )
            response = client.models.edit_image(
                model=model,
                prompt=prompt,
                reference_images=[raw_ref_image, mask_ref_image],
                config=types.EditImageConfig(
                    edit_mode=edit_mode,
                    number_of_images=number_of_images,
                    include_rai_reason=True,
                    output_gcs_uri=gcs_output_directory,
                    output_mime_type="image/jpeg",
                ),
            )

            if (
                response
                and hasattr(response, "generated_images")
                and response.generated_images
            ):
                logger.info(
                    f"models.image_models.edit_image: Received {len(response.generated_images)} edited images.",
                )
                edited_uris = [
                    img.image.gcs_uri
                    for img in response.generated_images
                    if hasattr(img, "image") and hasattr(img.image, "gcs_uri")
                ]
                ctx["billing_units"]["images_generated"] = len(edited_uris)
                return edited_uris
            if response and hasattr(response, "error"):
                logger.error(
                    f"models.image_models.edit_image: API response contains an error: {getattr(response, 'error', 'Unknown error')}",
                )
                return []
            logger.warning(
                f"models.image_models.edit_image: Response has no generated_images or is empty. Full response: {response}",
            )
            return []

        except Exception as e:
            logger.error(f"models.image_models.edit_image: API call failed: {e}")
            raise
