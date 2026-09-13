
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
""" Generate Images from models in Model Garden or Gemini """

import base64
import io
import logging
import time
from typing import Any
import uuid
import random
import os

from PIL import Image

from google.cloud import aiplatform
from google.cloud.firestore import Client, FieldFilter
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from config.default import Default
from config.firebase_config import FirebaseClient
from common.storage import store_to_gcs
from common.metadata import add_image_metadata


config = Default()
logging.basicConfig(level=logging.DEBUG)


def base64_to_image(image_str: str) -> Any:
    """Convert base64 encoded string to an image.

    Args:
      image_str: A string of base64 encoded image.

    Returns:
      A PIL.Image instance.
    """
    image = Image.open(io.BytesIO(base64.b64decode(image_str)))
    return image

def generate_images_from_model_garden(
    prompt: str,
    endpoint_id: str,
    model_name: str,
    output_gcs_folder: str,
    parameters: dict[str, Any],
    project_id: str = config.PROJECT_ID,
    location: str = config.LOCATION,
) -> list[str]:
    """
    Generates images using a specified endpoints of Model Garden deployed models.

    Args:
        prompt: The text prompt for image generation.
        endpoint_id: The Vertex AI Endpoint ID to use.
        model_name: A descriptive name for the model (for logging/metadata).
        output_gcs_folder: The subfolder within config.GENMEDIA_BUCKET to store results.
        parameters: A dictionary of parameters required by the specific model endpoint
                    (e.g., height, width, num_inference_steps).
        project_id: Google Cloud Project ID. Defaults to config.PROJECT_ID.
        location: Google Cloud Location. Defaults to config.LOCATION.

    Returns:
        A list of GCS URIs for the generated images (e.g., ["gs://bucket/folder/uuid.png"]).

    Raises:
        ValueError: If required arguments are missing or invalid.
        # Re-raises exceptions from aiplatform.Endpoint.predict
    """
    if not all([prompt, endpoint_id, model_name, output_gcs_folder, parameters]):
        raise ValueError("Missing one or more required arguments: prompt, endpoint_id, model_name, output_gcs_folder, parameters")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")

    logging.info(f"Generating image with endpoint model: {model_name}")
    logging.info(f"Prompt: '{prompt}'")
    logging.info(f"Endpoint ID: {endpoint_id}")
    logging.info(f"Parameters: {parameters}")
    logging.info(f"Target GCS Folder: gs://{config.GENMEDIA_BUCKET}/{output_gcs_folder}/")

    aiplatform.init(project=project_id, location=location)

    instances = [{"text": prompt}] 

    endpoint_path = f"projects/{project_id}/locations/{location}/endpoints/{endpoint_id}"
    endpoint = aiplatform.Endpoint(endpoint_path)

    arena_output: list[str] = []
    start_time = time.time()

    try:
        logging.info(f"Calling endpoint: {endpoint_path}")
        response = endpoint.predict(
            instances=instances,
            parameters=parameters,
        )
        # logging.info(f"Received response from endpoint: {response}")
        if not response or not hasattr(response, 'predictions') or not response.predictions:
             logging.error("Received empty or invalid response from endpoint.")
             return []

        image_outputs = []
        for prediction in response.predictions:
             # Check common keys for base64 image data
             img_data = prediction.get("output") or prediction.get("bytesBase64Encoded")
             if img_data:
                 image_outputs.append(img_data)
             else:
                 logging.warning(f"Prediction missing expected image data key ('output' or 'bytesBase64Encoded'): {prediction}")

        if not image_outputs:
             logging.error("No valid image data found in any endpoint predictions.")
             return [] # Or raise an error
    except Exception as e:
        logging.error(f"Error calling Vertex AI endpoint {endpoint_path}: {e}", exc_info=True)
        raise

    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Endpoint call finished in {elapsed_time:.2f} seconds. Processing {len(image_outputs)} images.")

    for idx, img_base64 in enumerate(image_outputs):
        try:
            image_filename = f"{uuid.uuid4()}.png"
            gcs_path_suffix = store_to_gcs(
                folder=output_gcs_folder,
                file_name=image_filename,
                mime_type="image/png",
                contents=img_base64,
                decode=True
            )
            # Construct full GCS URI
            gcs_uri = f"gs://{gcs_path_suffix}"

            logging.info(
                f"Generated image {idx+1}/{len(image_outputs)} with model {model_name}. "
                f"Stored at: {gcs_uri}"
            )
            arena_output.append(gcs_uri)

            try:
                add_image_metadata(gcs_uri, prompt, model_name)
                logging.debug(f"Successfully added metadata for {gcs_uri}")
            except Exception as ex:
                if "DeadlineExceeded" in str(ex):
                    logging.error(f"Firestore timeout adding metadata for {gcs_uri}: {ex}")
                else:
                    logging.error(f"Error adding image metadata for {gcs_uri}: {ex}", exc_info=True)

        except Exception as ex:
            logging.error(f"Error processing or uploading image {idx+1} from {model_name}: {ex}", exc_info=True)
            # Continue with the next image

    logging.info(f"Finished endpoint processing for model {model_name}. Returning {len(arena_output)} GCS URIs.")
    return arena_output

def images_from_flux(model_name: str, prompt: str, aspect_ratio: str) -> list[str]:
    """
    Generates images using the configured Flux.1 model endpoint.

    Args:
        prompt: The text prompt.
        params_override: Optional dictionary to override default parameters.

    Returns:
        A list of GCS URIs for the generated images.
    """
    _ = aspect_ratio  # aspect ratio is not used in this function
    if not config.MODEL_FLUX1_ENDPOINT_ID:
         raise ValueError("config.MODEL_FLUX1_ENDPOINT_ID is not set.")

    default_params = {
        "height": 1024,
        "width": 1024,
        "num_inference_steps": 4, # Default for Flux
    }

    return generate_images_from_model_garden(
        prompt=prompt,
        endpoint_id=config.MODEL_FLUX1_ENDPOINT_ID,
        model_name=model_name,
        output_gcs_folder="flux1",
        parameters=default_params,
    )

def images_from_stable_diffusion(model_name: str, prompt: str, aspect_ratio: str) -> list[str]:
    """
    Generates images using the configured Stable Diffusion model endpoint.
    *Adjust default_params based on your specific Stable Diffusion deployment.*

    Args:
        prompt: The text prompt.
        params_override: Optional dictionary to override default parameters.

    Returns:
        A list of GCS URIs for the generated images.
    """
    _ = aspect_ratio  # aspect ratio is not used in this function
    if not config.MODEL_STABLE_DIFFUSION_ENDPOINT_ID:
         raise ValueError("config.MODEL_STABLE_DIFFUSION_ENDPOINT_ID is not set.")

    default_params = {
        "height": 1024,
        "width": 1024,
        "num_inference_steps": 25,  # Typically higher for SD
        "guidance_scale": 7.5,     # Common SD parameter
    }

    return generate_images_from_model_garden(
        prompt=prompt,
        endpoint_id=config.MODEL_STABLE_DIFFUSION_ENDPOINT_ID,
        model_name=model_name,
        output_gcs_folder="stablediffusion", 
        parameters=default_params,
    )

def images_from_imagen(model_name: str, prompt: str, aspect_ratio: str):
    """creates images from Imagen and returns a list of gcs uris
    Args:
        model_name (str): imagen model name
        prompt (str): prompt for t2i model
        aspect_ratio (str): aspect ratio string
    Returns:
        _type_: a list of strings (gcs uris of image output)
    """

    start_time = time.time()

    arena_output = []
    logging.info(f"model: {model_name}")
    logging.info(f"prompt: {prompt}")
    logging.info(f"target output: {config.GENMEDIA_BUCKET}")

    vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)

    image_model = ImageGenerationModel.from_pretrained(model_name)

    response = image_model.generate_images(
        prompt=prompt,
        add_watermark=True,
        # aspect_ratio=getattr(state, "image_aspect_ratio"),
        aspect_ratio=aspect_ratio,
        number_of_images=1,
        output_gcs_uri=f"gs://{config.GENMEDIA_BUCKET}/imagen_live",
        language="auto",
        # negative_prompt=state.image_negative_prompt_input,
        safety_filter_level="block_few",
        # include_rai_reason=True,
    )
    end_time = time.time()
    elapsed_time = end_time - start_time

    for idx, img in enumerate(response.images):
        logging.info(f"Generated image {idx} with model {model_name} in {elapsed_time:.2f} seconds")

        logging.info(
            f"Generated image: #{idx}, len {len(img._as_base64_string())} at {img._gcs_uri}"
        )
        # output = img._as_base64_string()
        # state.image_output.append(output)
        arena_output.append(img._gcs_uri)
        logging.info(f"Image created: {img._gcs_uri}")
        try:
            add_image_metadata(img._gcs_uri, prompt, model_name)
        except Exception as e:
            if "DeadlineExceeded" in str(e):  # Check for timeout error
                logging.error(f"Firestore timeout: {e}")
            else:
                logging.error(f"Error adding image metadata: {e}")

    return arena_output

def study_fetch(model_name: str, prompt: str) -> list[str]:
    db: Client = FirebaseClient(database_id=config.IMAGE_FIREBASE_DB).get_client()
    collection_ref = db.collection(config.IMAGE_COLLECTION_NAME)
    print(f"Using: {model_name}")

    query = collection_ref.where(filter=FieldFilter("prompt", "==", prompt)).where(filter=FieldFilter("model", "==", model_name)).stream()

    docs = []
    for doc in query:
        gs_uri = doc.to_dict()['gcsuri']
        if "stablediffusion" not in gs_uri:
            docs.append(os.path.splitext(gs_uri)[0])
        else:
            if gs_uri.startswith("20250328_"):
                docs.append(os.path.splitext(gs_uri)[0])
            else:
                docs.append(gs_uri)
    return random.sample(docs, 1)

if __name__ == "__main__":
    # Example usage
    prompt = "A futuristic city skyline at sunset"
    aspect_ratio = "16:9"
    model_name = config.MODEL_FLUX1

    images = images_from_flux(model_name, prompt, aspect_ratio)
    print("Generated images:", images[0])

