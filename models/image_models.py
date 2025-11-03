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

import base64
import uuid

# from models.model_setup import (
#    ImagenModelSetup,
# )
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.cloud import aiplatform
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.storage import store_to_gcs
from config.default import Default
from common.analytics import track_model_call

# class ImageModel(TypedDict): # Remove this definition
#     """Defines Models For Image Generation."""
#
#     display: str
#     model_name: str


class ImagenModelSetup:
    """Imagen model setup"""

    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_id: Optional[str] = None,
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
        print(f"initiating genai client with {project_id} in {location}")
        client = genai.Client(
            vertexai=config.INIT_VERTEX,
            project=project_id,
            location=location,
        )
        return client


@retry(
    wait=wait_exponential(
        multiplier=1, min=1, max=10
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
        print(
            f"models.image_models.generate_images: Requesting {number_of_images} images for model {model} with output to {gcs_output_directory}"
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
            print(
                f"models.image_models.generate_images: Received {len(response.generated_images)} generated_images."
            )
            for i, gen_img in enumerate(response.generated_images):
                if hasattr(gen_img, "image") and gen_img.image:
                    if not gen_img.image.gcs_uri:
                        print(
                            f"models.image_models.generate_images: Image {i} has NO gcs_uri. Image object: {gen_img.image}"
                        )
                    else:
                        print(
                            f"models.image_models.generate_images: Image {i} has gcs_uri: {gen_img.image.gcs_uri}"
                        )
                    if not gen_img.image.image_bytes:
                        print(
                            f"models.image_models.generate_images: Image {i} has NO image_bytes."
                        )
                elif hasattr(gen_img, "error"):
                    print(
                        f"models.image_models.generate_images: GeneratedImage {i} has an error: {getattr(gen_img, 'error', 'Unknown error')}"
                    )
                else:
                    print(
                        f"models.image_models.generate_images: GeneratedImage {i} has no .image attribute or it's None. Full GeneratedImage object: {gen_img}"
                    )
        elif response and hasattr(response, "error"):
            print(
                f"models.image_models.generate_images: API response contains an error: {getattr(response, 'error', 'Unknown error')}"
            )
        else:
            print(
                f"models.image_models.generate_images: Response has no generated_images or is empty. Full response: {response}"
            )

        return response
    except Exception as e:
        print(f"models.image_models.generate_images: API call failed: {e}")
        raise


def generate_images_from_prompt(
    input_txt: str,
    current_model_name: str,
    image_count: int,
    negative_prompt: str,
    prompt_modifiers_segment: str,
    aspect_ratio: str,
) -> list[str]:
    """
    Generates images based on the input prompt and parameters.
    Returns a list of image URIs. Does not directly modify PageState.
    """
    full_prompt = f"{input_txt}, {prompt_modifiers_segment}"
    with track_model_call(
        model_name=current_model_name,
        prompt=full_prompt,
        image_count=image_count,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
    ):
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
        return generated_uris


def generate_virtual_models(prompt: str, num_images: int) -> list[str]:
    """
    Generates multiple virtual model images and saves them to GCS.

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
    """
    Generates a single, randomized virtual model and returns the image bytes.
    This function is designed to be a non-breaking replacement for the original VTO
    workflow, ensuring backward compatibility.
    """
    # Use the VirtualModelGenerator to create a single random prompt
    from models.virtual_model_generator import VirtualModelGenerator, DEFAULT_PROMPT
    
    # The VTO page passes a simple prompt, so we use the generator with the default template
    generator = VirtualModelGenerator(DEFAULT_PROMPT)
    generator.randomize_all()
    # Set a default variant for the VTO page
    generator.set_value("variant", "facing forward with a natural, relaxed posture and a neutral expression")

    random_prompt = generator.build_prompt()
    
    print(f"Generated random prompt for VTO: {random_prompt}")

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
    else:
        raise ValueError("Image generation failed or returned no data.")


def recontextualize_product_in_scene(
    image_uris_list: list[str], prompt: str, sample_count: int
) -> list[str]:
    """Recontextualizes a product in a scene and returns a list of GCS URIs."""
    cfg = Default()
    if cfg.LOCATION == "global":
        api_endpoint = "aiplatform.googleapis.com"
    else:
        api_endpoint = f"{cfg.LOCATION}-aiplatform.googleapis.com"
    client_options = {"api_endpoint": api_endpoint}
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

    model_endpoint = f"projects/{cfg.PROJECT_ID}/locations/{cfg.LOCATION}/publishers/google/models/{cfg.MODEL_IMAGEN_PRODUCT_RECONTEXT}"

    instance = {"productImages": []}
    for product_image_uri in image_uris_list:
        product_image = {"image": {"gcsUri": product_image_uri}}
        instance["productImages"].append(product_image)

    if prompt:
        instance["prompt"] = prompt

    parameters = {"sampleCount": sample_count}

    response = client.predict(
        endpoint=model_endpoint, instances=[instance], parameters=parameters
    )

    gcs_uris = []
    for prediction in response.predictions:
        if prediction.get("bytesBase64Encoded"):
            encoded_mask_string = prediction["bytesBase64Encoded"]
            mask_bytes = base64.b64decode(encoded_mask_string)

            gcs_uri = store_to_gcs(
                folder="recontext_results",
                file_name=f"recontext_result_{uuid.uuid4()}.png",
                mime_type="image/png",
                contents=mask_bytes,
                decode=False,
            )
            gcs_uris.append(gcs_uri)

    return gcs_uris


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
        print(
            f"models.image_models.edit_image: Requesting {number_of_images} edited images for model {model} with output to {gcs_output_directory}"
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
            print(
                f"models.image_models.edit_image: Received {len(response.generated_images)} edited images."
            )
            edited_uris = [
                img.image.gcs_uri
                for img in response.generated_images
                if hasattr(img, "image") and hasattr(img.image, "gcs_uri")
            ]
            return edited_uris
        elif response and hasattr(response, "error"):
            print(
                f"models.image_models.edit_image: API response contains an error: {getattr(response, 'error', 'Unknown error')}"
            )
            return []
        else:
            print(
                f"models.image_models.edit_image: Response has no generated_images or is empty. Full response: {response}"
            )
            return []

    except Exception as e:
        print(f"models.image_models.edit_image: API call failed: {e}")
        raise
