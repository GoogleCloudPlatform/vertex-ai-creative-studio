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
        message="Step 4 of 7: Generating candidate images with Gemini (Nano Banana)...",
        duration_seconds=0,
        data={},
    )

    candidate_image_gcs_uris, candidate_image_bytes_list = _generate_gemini_candidates(
        final_prompt, reference_image_gcs_uris, negative_prompt=negative_prompt
    )

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
        message="Step 6 of 7: Reframing the best image to 16:9 with Gemini (Nano Banana)...",
        duration_seconds=0,
        data={},
    )
    outpainted_image_gcs_uri, outpainted_image_bytes = _reframe_image_to_16_9(
        best_image_gcs_uri, final_prompt
    )
    step_duration = time.time() - step_start_time
    yield WorkflowStepResult(
        step_name="outpaint_image",
        status="complete",
        message="Image reframed to 16:9.",
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

def _fold_negative_prompt(prompt: str, negative_prompt: str | None) -> str:
    """Folds a negative prompt into a prompt-based request.

    The Gemini Image (Nano Banana) adapter has no dedicated ``negative_prompt``
    input (unlike the retired Imagen ``EditImageConfig``). To honour the user's
    negative-prompt intent via the prompt-based path, it is appended as an
    explicit "avoid" instruction rather than being stored-but-ignored.
    """
    if negative_prompt and negative_prompt.strip():
        return f"{prompt}\n\nAvoid the following in the image: {negative_prompt.strip()}"
    return prompt


def _generate_gemini_candidates(
    final_prompt: str,
    reference_image_gcs_uris: list[str],
    negative_prompt: str | None = None,
    num_candidates: int = 4,
) -> tuple[list[str], list[bytes]]:
    """Generates candidate images with Gemini (Nano Banana), prompt-based.

    Replaces the retired ``imagen-3.0-capability-001`` mask/subject-customization
    edit path. Rather than passing reference images as Imagen ``SubjectReferenceImage``
    objects with a mask, the reference images and the scene prompt are sent to the
    Gemini Image (Nano Banana) ``generateContent`` adapter, which performs a
    prompt-based, mask-free edit/customization. The ``negative_prompt`` (which the
    Imagen path passed via ``EditImageConfig``) is folded into the prompt text,
    since the Gemini adapter has no negative-prompt input.

    ``gemini-3.1-flash-image`` returns one image per call, so ``num_candidates``
    calls are issued in parallel (mirroring the previous behaviour of returning a
    set of candidates for downstream best-image selection).

    Returns the candidate GCS URIs and their downloaded bytes (the bytes are
    required by the downstream best-image selection step). Raises ``RuntimeError``
    if every candidate call comes back empty, so an empty candidate set never
    silently flows into best-image selection.
    """
    candidate_prompt = _fold_negative_prompt(final_prompt, negative_prompt)
    candidate_image_gcs_uris: list[str] = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                generate_image_from_prompt_and_images,
                candidate_prompt,
                reference_image_gcs_uris,
                aspect_ratio="1:1",
                gcs_folder="character_consistency_candidates",
                file_prefix="candidate",
            )
            for _ in range(num_candidates)
        ]
        for future in futures:
            gcs_uris, _, _, _, _ = future.result()
            candidate_image_gcs_uris.extend(gcs_uris)

    if not candidate_image_gcs_uris:
        raise RuntimeError(
            "Gemini (Nano Banana) candidate generation returned no images "
            f"for {len(reference_image_gcs_uris)} reference image(s)",
        )

    candidate_image_bytes_list = [
        download_from_gcs(gcs_uri) for gcs_uri in candidate_image_gcs_uris
    ]
    return candidate_image_gcs_uris, candidate_image_bytes_list


def _generate_video_from_image(
    image_bytes: bytes, provided_prompt: str | None = None
) -> tuple[bytes, str]:
    """Generates a video from an image."""
    gemini_client = genai.Client(
        vertexai=True,
        project=cfg.PROJECT_ID,
        location=cfg.LOCATION,
        http_options={"api_version": cfg.VERTEX_API_VERSION},
    )
    veo_client = genai.Client(
        vertexai=True,
        project=cfg.PROJECT_ID,
        location=cfg.LOCATION,
        http_options={"api_version": cfg.VERTEX_API_VERSION},
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

def _reframe_image_to_16_9(
    image_gcs_uri: str,
    prompt: str,
) -> tuple[str, bytes]:
    """Reframes the best candidate image to a 16:9 aspect ratio, prompt-based.

    Replaces the retired ``imagen-3.0-capability-001`` mask-based OUTPAINT step.
    Imagen outpaint padded the image onto a wider 16:9 canvas and filled the
    user-provided mask region. There is no like-for-like mask-based replacement,
    so the go-forward is a prompt-based reframe via the Gemini Image (Nano Banana)
    adapter: the source image plus a reframe instruction are sent with
    ``aspect_ratio="16:9"`` and the model extends the scene to fill the wider
    frame. This is mask-free (no explicit outpaint canvas/pad region), which is
    the accepted go-forward behaviour change.

    Returns the reframed image's GCS URI (stored by the adapter) and its bytes
    (needed by the downstream Veo step).
    """
    reframe_prompt = (
        f"{prompt}\n\n"
        "Expand and reframe this image to a 16:9 widescreen aspect ratio. "
        "Naturally extend the scene on the left and right to fill the wider frame, "
        "keeping the existing subject unchanged, in-focus, and consistent in "
        "identity, lighting, and style. Do not crop, distort, or alter the subject."
    )
    gcs_uris, _, _, _, _ = generate_image_from_prompt_and_images(
        reframe_prompt,
        [image_gcs_uri],
        aspect_ratio="16:9",
        gcs_folder="character_consistency_outpainted",
        file_prefix="outpainted",
    )
    if not gcs_uris:
        raise RuntimeError(
            "Gemini (Nano Banana) reframe returned no image for "
            f"{image_gcs_uri}",
        )
    reframed_gcs_uri = gcs_uris[0]
    return reframed_gcs_uri, download_from_gcs(reframed_gcs_uri)
