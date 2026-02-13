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

"""Model logic for the Object Rotation feature."""

import uuid
from common.analytics import get_logger
from config.firebase_config import FirebaseClient

db = FirebaseClient().get_client()
logger = get_logger(__name__)

def save_object_rotation_project(project: dict) -> dict:
    """
    Creates or updates an Object Rotation project document in Firestore.

    Args:
        project: A dictionary representing the project.

    Returns:
        The project dictionary, now with an 'id' if it was new.
    """
    if "id" not in project or not project.get("id"):
        project["id"] = str(uuid.uuid4())

    doc_ref = db.collection("object_rotation_projects").document(project["id"])
    doc_ref.set(project)
    logger.info(f"Object Rotation project saved to Firestore with ID: {project['id']}")
    return project


import asyncio
from models.gemini import generate_image_from_prompt_and_images

async def _generate_single_view(prompt: str, image_uri: str) -> str:
    """Helper to generate one view and return the URI."""
    gcs_uris, _, _, _ = await asyncio.to_thread(
        generate_image_from_prompt_and_images,
        prompt=prompt,
        images=[image_uri],
        aspect_ratio="1:1", # Assuming a square aspect ratio for product views
        gcs_folder="object_rotation_views",
    )
    if not gcs_uris:
        raise Exception(f"Failed to generate view for prompt: {prompt}")
    return gcs_uris[0]

async def generate_product_views(product_description: str, image_uri: str) -> dict[str, str]:
    """Generates four views of a product concurrently."""
    logger.info(f"Generating four views for source image: {image_uri}")

    base_prompt = f"a high-quality, professional {{view}} view of the product, which is {product_description}, on a plain white background."

    views_to_generate = {
        "front": base_prompt.format(view="front"),
        "back": base_prompt.format(view="back"),
        "left": base_prompt.format(view="left"),
        "right": base_prompt.format(view="right"),
    }

    tasks = [
        _generate_single_view(prompt, image_uri) 
        for prompt in views_to_generate.values()
    ]

    generated_uris = await asyncio.gather(*tasks)

    result = dict(zip(views_to_generate.keys(), generated_uris))

    logger.info(f"Successfully generated four views: {result}")
    return result


from models.requests import VideoGenerationRequest, APIReferenceImage
from models.veo import generate_video
from config.veo_models import get_veo_model_config

def generate_rotation_video(product_views: dict[str, str]) -> str:
    """Generates a 360 rotation video from the front, back, and left views."""
    logger.info("Generating 360 rotation video from views.")

    if not all(k in product_views for k in ["front", "back", "left"]):
        raise ValueError("Missing required views (front, back, left) for video generation.")

    # Use a model version that supports r2v, driven by config
    model_version = "3.1"
    model_config = get_veo_model_config(model_version)
    if not model_config:
        raise ValueError(f"Could not find configuration for VEO model version: {model_version}")

    prompt = (
        "Create a seamless, 360-degree rotating video of the product. "
        "The provided images are keyframes for the front, back, and left views, in that order. "
        "The video should smoothly transition between these views to create a full rotation."
    )

    references = [
        APIReferenceImage(gcs_uri=product_views["front"], mime_type="image/png"),
        APIReferenceImage(gcs_uri=product_views["back"], mime_type="image/png"),
        APIReferenceImage(gcs_uri=product_views["left"], mime_type="image/png"),
    ]

    video_request = VideoGenerationRequest(
        prompt=prompt,
        duration_seconds=model_config.default_duration,
        video_count=1,
        aspect_ratio=model_config.supported_aspect_ratios[0], # Use the first supported ratio
        resolution="720p",
        enhance_prompt=True,
        generate_audio=True,
        model_version_id=model_version,
        person_generation="dont_allow",
        r2v_references=references,
    )

    video_uris, _ = generate_video(video_request)

    if not video_uris:
        raise Exception("Failed to generate rotation video.")

    return video_uris[0]



