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

import os
import concurrent.futures
import uuid
from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig
import config
from typing import List
from utils.select_best import select_best_image
from utils.outpainting import outpaint_image
from utils.schemas import FacialCompositeProfile, GeneratedPrompts

# Initialize clients
client = genai.Client(vertexai=True, project=config.PROJECT_ID, location=config.GEMINI_LOCATION)

edit_model = config.IMAGEN_MODEL_NAME

def _get_description_for_image(image_path: str) -> str:
    """
    Analyzes a single image to extract a detailed facial profile and then
    generates a natural language description from that profile. This is the
    first step in creating a consistent character representation.
    """
    model_name = "gemini-3.1-pro-preview"
    
    # Step 1: Extract the structured FacialCompositeProfile
    profile_config = GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=FacialCompositeProfile.model_json_schema(),
        temperature=0.1,
    )
    profile_prompt_parts = [
        "You are a forensic analyst. Analyze the following image and extract a detailed, structured facial profile.",
        types.Part.from_bytes(data=types.Image.from_file(location=image_path).image_bytes, mime_type="image/png")
    ]
    profile_response = client.models.generate_content(
        model=model_name,
        contents=profile_prompt_parts,
        config=profile_config
    )
    profile = FacialCompositeProfile.model_validate_json(profile_response.text)

    # Step 2: Generate a natural language description from the profile
    description_config = GenerateContentConfig(temperature=0.1)
    description_prompt = f"""
    Based on the following structured JSON data of a person's facial features, write a concise, natural language description suitable for an image generation model. Focus on key physical traits.

    JSON Profile:
    {profile.model_dump_json(indent=2)}
    """
    description_response = client.models.generate_content(
        model=model_name,
        contents=[description_prompt],
        config=description_config
    )
    return description_response.text.strip()

def _generate_final_scene_prompt(base_description: str, user_prompt: str) -> GeneratedPrompts:
    """
    Generates a detailed, photorealistic prompt to place a described person
    in a novel scene. It combines the character's description with the user's
    desired scenario to create a prompt suitable for Imagen.
    """
    model_name = "gemini-3.1-pro-preview"
    config = GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeneratedPrompts.model_json_schema(),
        temperature=0.3,
    )

    meta_prompt = f"""
    You are an expert prompt engineer for a text-to-image generation model.
    Your task is to create a detailed, photorealistic prompt that places a specific person into a new scene.

    **Person Description:**
    {base_description}

    **User's Desired Scene:**
    {user_prompt}

    **Instructions:**
    1.  Combine the person's description with the user's scene to create a single, coherent, and highly detailed prompt.
    2.  The final image should be photorealistic. Add photography keywords like lens type (e.g., 85mm), lighting (e.g., cinematic lighting, soft light), and composition.
    3.  Ensure the final prompt clearly describes the person performing the action or being in the scene requested by the user.
    4.  Generate a standard negative prompt to avoid common artistic flaws.
    """

    response = client.models.generate_content(
        model=model_name,
        contents=[meta_prompt],
        config=config
    )
    return GeneratedPrompts.model_validate_json(response.text)

def generate_images_and_select_best(image_paths: List[str], prompt: str) -> tuple[str, str, List[str]]:
    """
    The core function of the image generation step. It takes the reference
    images and a scenario, generates a new set of images, selects the best one
    for character consistency, and then out-paints it to create the final
    scene for video generation.
    """
    output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Generate a detailed description for each reference image in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_descriptions = list(executor.map(_get_description_for_image, image_paths))

    # Create the reference images for Imagen
    reference_images_for_generation = []
    for i, image_path in enumerate(image_paths):
        image = types.Image.from_file(location=image_path)
        reference_images_for_generation.append(
            types.SubjectReferenceImage(
                reference_id=i,
                reference_image=image,
                config=types.SubjectReferenceConfig(
                    subject_type="SUBJECT_TYPE_PERSON",
                    subject_description=all_descriptions[i],
                )
            )
        )

    # Generate the final, scene-focused prompt
    # Use the first description as the basis for the person's appearance
    generated_prompts = _generate_final_scene_prompt(all_descriptions[0], prompt)
    final_prompt = generated_prompts.prompt
    negative_prompt = generated_prompts.negative_prompt

    # Generate the images with Imagen
    response = client.models.edit_image(
        model=edit_model,
        prompt=final_prompt,
        reference_images=reference_images_for_generation,
        config=types.EditImageConfig(
            edit_mode="EDIT_MODE_DEFAULT",
            number_of_images=4,
            aspect_ratio="1:1",
            person_generation="allow_all",
            safety_filter_level="block_few",
            negative_prompt=negative_prompt,
        )
    
    )

    generated_image_paths = []
    for i, image in enumerate(response.generated_images):
        file_name = os.path.join(output_dir, f"generated_image_{i}.png")
        image.image.save(file_name)
        generated_image_paths.append(file_name)

    # Select the best image
    best_image_selection = select_best_image(image_paths, generated_image_paths)
    
    # Outpaint the best image to create the final scene
    outpainted_image_path = outpaint_image(best_image_selection.best_image_path, final_prompt)

    return output_dir, outpainted_image_path, generated_image_paths
