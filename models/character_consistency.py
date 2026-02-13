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

import concurrent.futures
import io
import logging
import uuid
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig
from PIL import Image as PIL_Image

from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import download_from_gcs, store_to_gcs
from config.default import Default

from models.gemini import (
    get_facial_composite_profile,
    get_natural_language_description,
    generate_final_scene_prompt,
    select_best_image,
    generate_image_from_prompt_and_images,
)
from .character_consistency_models import (
    BestImage,
    FacialCompositeProfile,
    GeneratedPrompts,
    WorkflowStepResult,
)

cfg = Default()

from typing import Generator

def generate_character_video(
    user_email: str, reference_image_gcs_uris: list[str], scene_prompt: str
) -> Generator[WorkflowStepResult, None, None]:
    """
    Orchestrates the entire character consistency workflow as a generator,
    yielding the result of each step.
    """
    total_start_time = time.time()
    logger.info("Starting character consistency workflow for user: %s", user_email)

    # Step 1: Download image bytes from GCS
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="download_images",
        status="processing",
        message=f"Step 1 of 7: Downloading {len(reference_image_gcs_uris)} reference images...",
        duration_seconds=0,
        data={},
    )
    reference_image_bytes_list = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        reference_image_bytes_list = list(
            executor.map(download_from_gcs, reference_image_gcs_uris)
        )
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="download_images",
        status="complete",
        message="Reference images downloaded.",
        duration_seconds=step_duration,
        data={},
    )

    # Step 2: Generate descriptions
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="generate_descriptions",
        status="processing",
        message="Step 2 of 7: Generating descriptions for reference images...",
        duration_seconds=0,
        data={},
    )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        profiles = list(executor.map(get_facial_composite_profile, reference_image_bytes_list))
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_descriptions = list(executor.map(get_natural_language_description, profiles))
    character_description = all_descriptions[0]
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="generate_descriptions",
        status="complete",
        message="Descriptions generated.",
        duration_seconds=step_duration,
        data={"character_description": character_description},
    )

    # Step 3: Generate Imagen prompt
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="generate_imagen_prompt",
        status="processing",
        message="Step 3 of 7: Generating scene prompt for Imagen...",
        duration_seconds=0,
        data={},
    )
    generated_prompts = generate_final_scene_prompt(character_description, scene_prompt)
    final_prompt = generated_prompts.prompt
    negative_prompt = generated_prompts.negative_prompt
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="generate_imagen_prompt",
        status="complete",
        message="Imagen prompt generated.",
        duration_seconds=step_duration,
        data={"imagen_prompt": final_prompt, "negative_prompt": negative_prompt},
    )

    # Step 4: Generate candidate images
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="generate_candidates",
        status="processing",
        message="Step 4 of 7: Generating candidate images with Imagen and Gemini...",
        duration_seconds=0,
        data={},
    )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Generate images with Imagen
        imagen_future = executor.submit(
            _generate_imagen_candidates, reference_image_bytes_list, all_descriptions, final_prompt, negative_prompt
        )
        # Generate images with Gemini
        gemini_future = executor.submit(
            generate_image_from_prompt_and_images,
            final_prompt,
            reference_image_gcs_uris,
            aspect_ratio="1:1",
            gcs_folder="character_consistency_candidates",
            file_prefix="candidate",
        )

        imagen_candidate_gcs_uris, imagen_candidate_image_bytes_list = imagen_future.result()
        gemini_candidate_gcs_uris, _, _, _ = gemini_future.result()

    candidate_image_gcs_uris = imagen_candidate_gcs_uris + gemini_candidate_gcs_uris
    candidate_image_bytes_list = imagen_candidate_image_bytes_list  # We don't have bytes from Gemini yet

    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="generate_candidates",
        status="complete",
        message="Candidate images generated.",
        duration_seconds=step_duration,
        data={"candidate_image_gcs_uris": candidate_image_gcs_uris, "candidate_image_bytes_list": candidate_image_bytes_list},
    )

    # Step 5: Select the best image
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="select_best_image",
        status="processing",
        message="Step 5 of 7: Selecting the best image...",
        duration_seconds=0,
        data={},
    )
    best_image_selection = select_best_image(
        reference_image_bytes_list, candidate_image_bytes_list, candidate_image_gcs_uris
    )
    best_image_gcs_uri = best_image_selection.best_image_path
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="select_best_image",
        status="complete",
        message="Best image selected.",
        duration_seconds=step_duration,
        data={"best_image_gcs_uri": best_image_gcs_uri},
    )

    # Step 6: Outpaint the best image
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="outpaint_image",
        status="processing",
        message="Step 6 of 7: Outpainting the best image...",
        duration_seconds=0,
        data={},
    )
    best_image_bytes = None
    for i, gcs_uri in enumerate(candidate_image_gcs_uris):
        if gcs_uri == best_image_gcs_uri:
            best_image_bytes = candidate_image_bytes_list[i]
            break
    outpainted_image_bytes = _outpaint_image(best_image_bytes, final_prompt)
    outpainted_image_gcs_uri = store_to_gcs(
        folder="character_consistency_outpainted",
        file_name=f"outpainted_{uuid.uuid4()}.png",
        mime_type="image/png",
        contents=outpainted_image_bytes,
    )
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="outpaint_image",
        status="complete",
        message="Image outpainted.",
        duration_seconds=step_duration,
        data={"outpainted_image_gcs_uri": outpainted_image_gcs_uri, "outpainted_image_bytes": outpainted_image_bytes},
    )

    # Step 7: Generate Video
    step_start_time = time.time()
    yield WorkflowStepResult(
        step_name="generate_video",
        status="processing",
        message="Step 7 of 7: Generating final video with Veo...",
        duration_seconds=0,
        data={},
    )
    video_bytes, veo_prompt = _generate_video_from_image(outpainted_image_bytes, scene_prompt)
    video_gcs_uri = store_to_gcs(
        folder="character_consistency_videos",
        file_name=f"video_{uuid.uuid4()}.mp4",
        mime_type="video/mp4",
        contents=video_bytes,
    )
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="generate_video",
        status="complete",
        message="Final video generated.",
        duration_seconds=step_duration,
        data={"video_gcs_uri": video_gcs_uri, "veo_prompt": veo_prompt},
    )

    # Step 8: Save all metadata and artifacts to Firestore
    total_duration = time.time() - total_start_time
    logger.info("Step 8: Saving metadata to Firestore...")
    new_item = MediaItem(
        user_email=user_email,
        media_type="character_consistency",
        model=cfg.CHARACTER_CONSISTENCY_VEO_MODEL,
        mime_type="video/mp4",
        source_character_images=reference_image_gcs_uris,
        character_description=character_description,
        imagen_prompt=final_prompt,
        prompt=scene_prompt,
        negative_prompt=negative_prompt,
        candidate_images=candidate_image_gcs_uris,
        best_candidate_image=best_image_gcs_uri,
        outpainted_image=outpainted_image_gcs_uri,
        gcsuri=video_gcs_uri,
        veo_prompt=veo_prompt,
        generation_time=total_duration,
    )
    add_media_item_to_firestore(new_item)
    logger.info("Workflow complete in %.2f seconds. MediaItem ID: %s", total_duration, new_item.id)

def _generate_imagen_candidates(reference_image_bytes_list, all_descriptions, final_prompt, negative_prompt):
    """Generates candidate images with Imagen."""
    client = genai.Client(vertexai=True, project=cfg.PROJECT_ID, location=cfg.LOCATION)
    edit_model = cfg.CHARACTER_CONSISTENCY_IMAGEN_MODEL
    reference_images_for_generation = []
    for i, image_bytes in enumerate(reference_image_bytes_list[:4]):
        image = types.Image(image_bytes=image_bytes)
        reference_images_for_generation.append(
            types.SubjectReferenceImage(
                reference_id=i,
                reference_image=image,
                config=types.SubjectReferenceConfig(
                    subject_type="SUBJECT_TYPE_PERSON",
                    subject_description=all_descriptions[i],
                ),
            ),
        )
    response = client.models.edit_image(
        model=edit_model,
        prompt=final_prompt,
        reference_images=reference_images_for_generation,
        config=types.EditImageConfig(
            edit_mode="EDIT_MODE_DEFAULT",
            number_of_images=4,
            aspect_ratio="1:1",
            person_generation="allow_all",
            safety_filter_level="block_only_high",
            negative_prompt=negative_prompt,
        ),
    )
    candidate_image_gcs_uris = []
    candidate_image_bytes_list = []
    for i, image in enumerate(response.generated_images):
        image_bytes = image.image.image_bytes
        gcs_uri = store_to_gcs(
            folder="character_consistency_candidates",
            file_name=f"candidate_{uuid.uuid4()}_{i}.png",
            mime_type="image/png",
            contents=image_bytes,
        )
        candidate_image_gcs_uris.append(gcs_uri)
        candidate_image_bytes_list.append(image_bytes)
    return candidate_image_gcs_uris, candidate_image_bytes_list


def _generate_video_from_image(
    image_bytes: bytes, provided_prompt: str | None = None
) -> tuple[bytes, str]:
    """Generates a video from an image."""
    gemini_client = genai.Client(
        vertexai=True, project=cfg.PROJECT_ID, location=cfg.LOCATION
    )
    veo_client = genai.Client(
        vertexai=True, project=cfg.PROJECT_ID, location=cfg.LOCATION
    )

    pil_image = PIL_Image.open(io.BytesIO(image_bytes))
    width, height = pil_image.size
    aspect_ratio = "9:16" if height > width else "16:9"

    gemini_contents = [
        "You are an expert Cinematic Prompt Engineer and a creative director for Veo. Your purpose is to transform a user's basic prompt and optional reference image into a masterful, detailed, and technically rich Veo prompt that will guide the model to generate a high-quality video.",
        pil_image,
    ]
    if provided_prompt:
        gemini_contents.insert(
            1, f"the user has provided this prompt as a starter {provided_prompt}"
        )

    video_prompt_response = gemini_client.models.generate_content(
        model=cfg.CHARACTER_CONSISTENCY_GEMINI_MODEL,
        contents=gemini_contents,
        config=genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(thinking_budget=-1)
        ),
    )
    video_prompt = video_prompt_response.text.strip()

    input_image = genai.types.Image(image_bytes=image_bytes, mime_type="image/png")

    operation = veo_client.models.generate_videos(
        model=cfg.CHARACTER_CONSISTENCY_VEO_MODEL,
        prompt=video_prompt,
        config=genai.types.GenerateVideosConfig(
            duration_seconds=8,
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
            enhance_prompt=True,
            person_generation="allow_adult",
        ),
        image=input_image,
    )

    # This is a long running operation, we should not block here in a real app
    # For this example, we will wait for it to complete
    import time

    while not operation.done:
        time.sleep(10)
        operation = veo_client.operations.get(operation)

    if operation.error:
        raise Exception(f"Error generating video: {operation.error}")

    return operation.response.generated_videos[0].video.video_bytes, video_prompt

def _outpaint_image(image_bytes: bytes, prompt: str) -> bytes:
    """
    Performs outpainting on an image to a 16:9 aspect ratio.
    """
    client = genai.Client(vertexai=True, project=cfg.PROJECT_ID, location=cfg.LOCATION)
    edit_model = cfg.CHARACTER_CONSISTENCY_IMAGEN_MODEL

    initial_image = PIL_Image.open(io.BytesIO(image_bytes))

    mask = PIL_Image.new("L", initial_image.size, 0)

    target_height = 1080
    target_width = int(target_height * 16 / 9)
    target_size = (target_width, target_height)

    image_pil_outpaint, mask_pil_outpaint = _pad_image_and_mask(
        initial_image,
        mask,
        target_size,
        0,
        0,
    )

    image_for_api = types.Image(image_bytes=_get_bytes_from_pil(image_pil_outpaint))
    mask_for_api = types.Image(image_bytes=_get_bytes_from_pil(mask_pil_outpaint))

    raw_ref_image = types.RawReferenceImage(
        reference_image=image_for_api, reference_id=0
    )
    mask_ref_image = types.MaskReferenceImage(
        reference_id=1,
        reference_image=mask_for_api,
        config=types.MaskReferenceConfig(
            mask_mode="MASK_MODE_USER_PROVIDED",
            mask_dilation=0.03,
        ),
    )

    edited_image_response = client.models.edit_image(
        model=edit_model,
        prompt=prompt,
        reference_images=[raw_ref_image, mask_ref_image],
        config=types.EditImageConfig(
            edit_mode="EDIT_MODE_OUTPAINT",
            number_of_images=1,
            safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
            person_generation="ALLOW_ALL",
        ),
    )

    return edited_image_response.generated_images[0].image.image_bytes

def _get_bytes_from_pil(image: PIL_Image.Image) -> bytes:
    """Gets the image bytes from a PIL Image object."""
    byte_io_png = io.BytesIO()
    image.save(byte_io_png, "PNG")
    return byte_io_png.getvalue()

def _pad_to_target_size(
    source_image,
    target_size,
    mode="RGB",
    vertical_offset_ratio=0,
    horizontal_offset_ratio=0,
    fill_val=255,
):
    """Pads an image to a target size."""
    orig_image_size_w, orig_image_size_h = source_image.size
    target_size_w, target_size_h = target_size

    insert_pt_x = (target_size_w - orig_image_size_w) // 2 + int(
        horizontal_offset_ratio * target_size_w
    )
    insert_pt_y = (target_size_h - orig_image_size_h) // 2 + int(
        vertical_offset_ratio * target_size_h
    )
    insert_pt_x = min(insert_pt_x, target_size_w - orig_image_size_w)
    insert_pt_y = min(insert_pt_y, target_size_h - orig_image_size_h)

    if mode == "RGB":
        source_image_padded = PIL_Image.new(
            mode, target_size, color=(fill_val, fill_val, fill_val)
        )
    elif mode == "L":
        source_image_padded = PIL_Image.new(mode, target_size, color=(fill_val))
    else:
        raise ValueError("source image mode must be RGB or L.")

    source_image_padded.paste(source_image, (insert_pt_x, insert_pt_y))
    return source_image_padded

def _pad_image_and_mask(
    image_pil: PIL_Image.Image,
    mask_pil: PIL_Image.Image,
    target_size,
    vertical_offset_ratio,
    horizontal_offset_ratio,
):
    """Pads and resizes an image and its mask to the same target size."""
    image_pil.thumbnail(target_size)
    mask_pil.thumbnail(target_size)

    image_pil_padded = _pad_to_target_size(
        image_pil,
        target_size=target_size,
        mode="RGB",
        vertical_offset_ratio=vertical_offset_ratio,
        horizontal_offset_ratio=horizontal_offset_ratio,
        fill_val=0,
    )
    mask_pil_padded = _pad_to_target_size(
        mask_pil,
        target_size=target_size,
        mode="L",
        vertical_offset_ratio=vertical_offset_ratio,
        horizontal_offset_ratio=horizontal_offset_ratio,
        fill_val=255,  # White for the area to be filled
    )
    return image_pil_padded, mask_pil_padded
