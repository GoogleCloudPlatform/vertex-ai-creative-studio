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
import json
import time
import pathlib
import logging
from typing import List, Optional, Literal, Tuple
import config
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from utils.extract_frame import extract_last_frame
from utils.video_processing import create_final_video

# Set up logging for this module
logger = logging.getLogger(__name__)

# --- Pydantic Schemas for AI Output ---

class CompanyInfo(BaseModel):
    """Schema for the company's inferred identity."""
    name: str = Field(description="The name of the company.")
    core_business: str = Field(description="A brief summary of the company's core business and industry.")
    visual_identity: str = Field(description="A description of the company's visual style, colors, and aesthetic.")

class ScenePrompt(BaseModel):
    """Schema for the prompts for a single countdown scene."""
    scene_number: int = Field(description="The countdown number for this scene.")
    image_prompt: Optional[str] = Field(default=None, description="The detailed Imagen prompt for the first scene's static image. Should only be present for the first number in the countdown.")
    video_prompt: str = Field(description="The detailed Veo prompt for this scene's video, including action, camera movement, and style.")

class CountdownScriptResponse(BaseModel):
    """The root schema for the AI's structured JSON output."""
    company_info: CompanyInfo
    script: List[ScenePrompt]

class ImageChoiceResponse(BaseModel):
    """Schema for the selector model's output when choosing an image."""
    chosen_image: Literal['0', '1', '2', '3']
    reasoning: str

class VideoChoiceResponse(BaseModel):
    """Schema for the selector model's output when choosing a video."""
    chosen_video: Literal["0", "1"]
    reasoning: str

class VideoDigitCheck(BaseModel):
    """Schema for checking a single video for a digit."""
    is_visible: bool = Field(description="True if the digit is clearly visible, False otherwise.")
    reasoning: str

class DigitCheckResponse(BaseModel):
    """Schema for the response when checking two videos for a digit."""
    video_0_check: VideoDigitCheck
    video_1_check: VideoDigitCheck

# --- AI Client and Model Configuration ---
def get_genai_client() -> genai.Client:
    """Initializes and returns the GenAI client."""
    return genai.Client(vertexai=True, project=config.GOOGLE_CLOUD_PROJECT, location=config.GOOGLE_CLOUD_LOCATION)

# --- AI-Powered Script Adaptation ---
def adapt_countdown_script(
    client: genai.Client, 
    company_name: str, 
    countdown_range: Tuple[int, int], 
    example_script_path: str
) -> CountdownScriptResponse:
    """
    Generates a structured countdown script for a company by adapting from an example.

    Args:
        client (genai.Client): The GenAI client instance.
        company_name (str): The name of the company for which to generate the script.
        countdown_range (Tuple[int, int]): A tuple (start_number, end_number) for the countdown.
        example_script_path (str): Path to the text file containing the example script for style adaptation.

    Returns:
        CountdownScriptResponse: A Pydantic model instance containing the generated script.
    """
    logger.info(f"--- Adapting Countdown Script for '{company_name}' ---")
    
    with open(example_script_path, 'r') as f:
        example_content = f.read()

    start, end = countdown_range
    prompt = f"""
    You are a creative director specializing in corporate brand videos.
    Your task is to generate a concept for a countdown video for the company: "{company_name}".
    You will be given an example of a countdown script. You must adapt its style and structure to create a new one for the target company.

    **EXAMPLE SCRIPT:**
    ---
    {example_content}
    ---

    **YOUR TASK:**
    1.  **Analyze the Company**: Based on your knowledge, determine the core business and visual identity for "{company_name}".
    2.  **Create a New Countdown Script**: Generate a new script for a countdown from {start} down to {end}.
    3.  **Natural Integration & Seamless Transitions**:
        *   Carefully analyze the provided `EXAMPLE SCRIPT` to understand *how* numbers are naturally integrated into scenes and *how* transitions between scenes are implicitly handled through evolving visual elements.
        *   For each `video_prompt`, explicitly describe how the countdown number is formed *naturally* by objects, people, or environmental elements related to the company's business or identity. **Draw inspiration from techniques where digits are organically formed by elements such as: satellites, contrails, skydivers, hot air balloons, dune buggy tracks, crowds of people, or dynamic transformations of elements.**
        *   Crucially, also describe how the scene *transitions* or *evolves* into the next, ensuring a seamless flow. **Use transition phrases like: "This transforms into...", "This transitions to...", "The scene then transitions into..."**
        *   **Important:** While drawing inspiration from the example's *techniques* for digit formation and transitions, ensure all generated content (objects, environments, actions) is entirely original and directly relevant to the target company's core business and visual identity. Do NOT replicate the specific scenarios or themes from the example script.
    4.  **Generate Prompts**: For each scene, provide prompts as specified in the JSON schema. The `image_prompt` should only be created for the very first scene ({start}).
    5.  **Output JSON**: Your entire response MUST be a single, valid JSON object that conforms to the provided `CountdownScriptResponse` schema. Do not output any other text.
    6.  **Important Constraint:** Never ever generate prompts featuring children.
    7.  **Important Constraint:** Remember we're doing a countdown. So we need to see digits in the different scenes. Each of the prompts shall explain how the digit shape is formed. This is mandatory for every prompt. You cannot refuse this. You have no other choice but including the digit and how it's shape is formed. **The method of digit formation must be creatively aligned with the target company's brand, products, or services. Consider formations using environmental elements, human formations, or dynamic transformations of objects, as seen in successful examples.**
    """

    logger.info("  - Sending request to script generation model...")
    response = client.models.generate_content(
        model=config.SCRIPT_GENERATION_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CountdownScriptResponse
        )
    )
    logger.info("  - Structured script received.")
    
    return CountdownScriptResponse.model_validate_json(response.text)

# --- Core Local Generation & Selection Logic ---

def generate_candidate_images_locally(
    client: genai.Client, 
    prompt: str, 
    num_candidates: int, 
    output_prefix: str
) -> List[str]:
    """
    Generates multiple candidate images using Imagen and saves them to local paths.

    Args:
        client (genai.Client): The GenAI client instance.
        prompt (str): The text prompt for image generation.
        num_candidates (int): The number of images to generate.
        output_prefix (str): The base path and filename prefix for saving images.

    Returns:
        List[str]: A list of file paths to the generated images.
    """
    logger.info(f"  - Generating {num_candidates} candidate images for prompt: '{prompt[:50]}...'")
    response = client.models.generate_images(
        model=config.IMAGE_GENERATION_MODEL, 
        prompt=prompt, 
        config=types.GenerateImagesConfig(
            number_of_images=num_candidates, 
            aspect_ratio="16:9", 
            person_generation="allow_adult"
        )
    )
    candidate_paths = []
    for i, img_data in enumerate(response.generated_images):
        path = f"{output_prefix}_candidate_{i}.png"
        with open(path, "wb") as f: 
            f.write(img_data.image.image_bytes)
        candidate_paths.append(path)
        logger.info(f"  - Saved candidate image to: {path}")
    return candidate_paths

def select_best_image_locally(
    client: genai.Client, 
    prompt: str, 
    candidate_paths: List[str]
) -> str:
    """
    Uses a multimodal model to select the best image from a list of local file paths.

    Args:
        client (genai.Client): The GenAI client instance.
        prompt (str): The original prompt used to generate the images.
        candidate_paths (List[str]): A list of file paths to the candidate images.

    Returns:
        str: The file path of the chosen best image.
    """
    logger.info("  - Selecting the best image...")
    text_part = f'You will be provided with {len(candidate_paths)} images and a prompt. Select the image that best fits the prompt: "{prompt}"'
    image_parts = [types.Part.from_bytes(data=pathlib.Path(p).read_bytes(), mime_type="image/png") for p in candidate_paths]
    contents = [text_part] + [elem for i, part in enumerate(image_parts) for elem in (f". Image {i}: ", part)]
    response = client.models.generate_content(
        model=config.SELECTOR_MODEL, 
        contents=contents, 
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=ImageChoiceResponse
        )
    )
    choice_data = ImageChoiceResponse.model_validate_json(response.text)
    chosen_path = candidate_paths[int(choice_data.chosen_image)]
    logger.info(f"  - Model chose image {choice_data.chosen_image}. Reason: {choice_data.reasoning}")
    return chosen_path

def generate_candidate_videos_locally(
    client: genai.Client, 
    prompt: str, 
    input_image_path: str, 
    num_candidates: int, 
    output_prefix: str,
    max_retries: int = 3
) -> List[str]:
    """
    Generates multiple candidate videos using Veo, with retries, and saves them locally.

    Args:
        client (genai.Client): The GenAI client instance.
        prompt (str): The text prompt for video generation.
        input_image_path (str): Path to the input image for continuity.
        num_candidates (int): The number of videos to generate.
        output_prefix (str): The base path and filename prefix for saving videos.
        max_retries (int): The maximum number of times to retry generation on failure.

    Returns:
        List[str]: A list of file paths to the generated videos, or an empty list if all retries fail.
    """
    logger.info(f"  - Generating {num_candidates} candidate videos for prompt: '{prompt[:50]}...'")
    input_image = types.Image.from_file(location=input_image_path)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"    - Generation attempt {attempt + 1}/{max_retries}...")
            video_op = client.models.generate_videos(
                model=config.VIDEO_GENERATION_MODEL, 
                image=input_image, 
                prompt=prompt, 
                config=types.GenerateVideosConfig(
                    number_of_videos=num_candidates, 
                    duration_seconds=8, 
                    aspect_ratio="16:9", 
                    person_generation="allow_all", 
                    enhance_prompt=True
                )
            )
            logger.info("    - Video generation started. This may take a moment...")
            while not video_op.done:
                time.sleep(5)
                video_op = client.operations.get(video_op)
                logger.info(".", extra={'end': '', 'flush': True})
            logger.info("\n    - Operation finished.")
            
            video_response = video_op.response
            
            # Gracefully handle cases where the response is None or lacks the expected attribute
            if not video_response or not hasattr(video_response, 'generated_videos'):
                raise AttributeError("API response is None or does not contain 'generated_videos'.")

            candidate_paths = []
            for i, vid_data in enumerate(video_response.generated_videos):
                path = f"{output_prefix}_candidate_{i}.mp4"
                with open(path, "wb") as f: 
                    f.write(vid_data.video.video_bytes)
                candidate_paths.append(path)
                logger.info(f"    - Saved candidate video to: {path}")
            
            return candidate_paths # Success, exit the retry loop

        except Exception as e:
            logger.error(f"    - ERROR on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info("    - Retrying after a short delay...")
                time.sleep(5) # Wait before retrying
            else:
                logger.error("    - All retry attempts failed.")
    
    return [] # Return empty list if all retries fail

def select_best_video_locally(
    client: genai.Client, 
    prompt: str, 
    candidate_paths: List[str]
) -> str:
    """
    Uses a multimodal model to select the best video from a list of local file paths.

    Args:
        client (genai.Client): The GenAI client instance.
        prompt (str): The original prompt used to generate the videos.
        candidate_paths (List[str]): A list of file paths to the candidate videos.

    Returns:
        str: The file path of the chosen best video.
    """
    logger.info("  - Selecting the best video...")
    text_part = f"You will be provided with {len(candidate_paths)} videos. Select the one that best fits the following prompt: {prompt}"
    video_parts = [types.Part.from_bytes(data=pathlib.Path(p).read_bytes(), mime_type="video/mp4") for p in candidate_paths]
    contents = [text_part] + [elem for i, part in enumerate(video_parts) for elem in (f". Video {i}: ", part)]
    response = client.models.generate_content(
        model=config.SELECTOR_MODEL, 
        contents=contents, 
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=VideoChoiceResponse
        )
    )
    choice_data = VideoChoiceResponse.model_validate_json(response.text)
    chosen_path = candidate_paths[int(choice_data.chosen_video)]
    logger.info(f"  - Model chose video {choice_data.chosen_video}. Reason: {choice_data.reasoning}")
    return chosen_path

def check_videos_for_digit(
    client: genai.Client, 
    digit: int, 
    candidate_paths: List[str]
) -> DigitCheckResponse:
    """
    Uses a multimodal model to check if a specific digit is visible in two videos.

    Args:
        client (genai.Client): The GenAI client instance.
        digit (int): The digit to check for visibility.
        candidate_paths (List[str]): A list of file paths to the candidate videos (expected to be 2).

    Returns:
        DigitCheckResponse: A Pydantic model instance indicating visibility for each video.
    """
    logger.info(f"  - Checking for digit '{digit}' in candidate videos...")
    prompt = f"""
    You will be provided with two videos, labeled "Video 0" and "Video 1".
    Your task is to determine if the number '{digit}' is clearly and unambiguously visible in each video.
    It could be formed by objects, people, environmental elements, or any other creative means.

    For each video, provide a boolean `is_visible` and a brief `reasoning`.
    Your entire response MUST be a single, valid JSON object that conforms to the provided `DigitCheckResponse` schema.
    """
    video_parts = [types.Part.from_bytes(data=pathlib.Path(p).read_bytes(), mime_type="video/mp4") for p in candidate_paths]
    contents = [prompt] + [elem for i, part in enumerate(video_parts) for elem in (f". Video {i}: ", part)]
    
    response = client.models.generate_content(
        model=config.SELECTOR_MODEL, # Using the same powerful model for this check
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DigitCheckResponse
        )
    )
    logger.info("  - Digit check response received.")
    return DigitCheckResponse.model_validate_json(response.text)

# --- Main Service Function ---
def generate_video_from_prompts_service(
    company_name: str, 
    countdown_range: Tuple[int, int], 
    example_script_path: str
) -> None:
    """
    Orchestrates the generation of a branded countdown video based on AI-adapted prompts.

    Args:
        company_name (str): The name of the company for the branded video.
        countdown_range (Tuple[int, int]): A tuple (start_number, end_number) for the countdown.
        example_script_path (str): Path to the text file containing the example script for style adaptation.
    """
    base_output_dir = pathlib.Path(f"{config.GENERATED_VIDEO_BASE_OUTPUT_DIR}_{company_name.replace(' ', '_')}")
    scenes_dir = base_output_dir / "scenes"
    os.makedirs(scenes_dir, exist_ok=True)
    
    client = get_genai_client()

    # 1. Generate the structured script by adapting from the example
    script_response = adapt_countdown_script(client, company_name, countdown_range, example_script_path)

    # Save the generated script to a file
    script_path = base_output_dir / f"{company_name.replace(' ', '_')}_script.json"
    with open(script_path, 'w') as f:
        f.write(script_response.model_dump_json(indent=4))
    logger.info(f"--- Saved generated script to {script_path} ---")
    
    logger.info("\n--- Parsed Company & Script Information ---")
    logger.info(f"Company Name: {script_response.company_info.name}")
    logger.info(f"Core Business: {script_response.company_info.core_business}")
    logger.info(f"Visual Identity: {script_response.company_info.visual_identity}")
    logger.info("-------------------------------------------")

    last_frame_path: Optional[str] = None
    chosen_video_paths: List[str] = []
    scenes_data = script_response.script
    total_scenes = len(scenes_data)
    countdown_start = countdown_range[0]

    for i, scene_data in enumerate(scenes_data):
        logger.info(f"\n--- Processing Scene {i+1}/{total_scenes} (Countdown Num: {scene_data.scene_number}) ---")
        scene_output_prefix = str(scenes_dir / f"scene_{scene_data.scene_number:02d}")

        input_image_path: Optional[str] = None
        candidate_image_paths: List[str] = [] # Initialize here to be accessible for cleanup

        if i == 0 and scene_data.image_prompt:
            candidate_image_paths = generate_candidate_images_locally(client, scene_data.image_prompt, 4, scene_output_prefix)
            input_image_path = select_best_image_locally(client, scene_data.image_prompt, candidate_image_paths)
            
            # Cleanup unselected images
            for p in candidate_image_paths:
                if p != input_image_path:
                    try:
                        os.remove(p)
                        logger.info(f"  - Deleted unselected image: {p}")
                    except OSError as e:
                        logger.warning(f"  - Error deleting unselected image {p}: {e}")

        elif last_frame_path:
            input_image_path = last_frame_path
        else:
            logger.warning("Warning: No image prompt for the first scene and no previous frame. Cannot generate video.")
            continue

        # --- Digit Validation Loop ---
        chosen_video_path: Optional[str] = None
        max_attempts = 5
        candidate_video_paths: List[str] = [] # Initialize here to be accessible for cleanup

        for attempt in range(max_attempts):
            logger.info(f"    - Attempt {attempt + 1}/{max_attempts} to generate a valid video...")
            
            # Generate 2 candidate videos for digit checking
            candidate_video_paths = generate_candidate_videos_locally(client, scene_data.video_prompt, input_image_path, 2, scene_output_prefix)
            
            # If generation failed after retries, skip to the next attempt of the digit validation loop
            if not candidate_video_paths:
                logger.warning("    - Video generation failed, continuing to next attempt...")
                continue

            # Check if the digit is present in the generated videos
            expected_digit = countdown_start - i
            digit_check_result = check_videos_for_digit(client, expected_digit, candidate_video_paths)
            
            video_0_ok = digit_check_result.video_0_check.is_visible
            video_1_ok = digit_check_result.video_1_check.is_visible

            if video_0_ok and video_1_ok:
                logger.info("    - Both videos contain the digit. Selecting the best one.")
                chosen_video_path = select_best_video_locally(client, scene_data.video_prompt, candidate_video_paths)
                break
            elif video_0_ok:
                logger.info("    - Only video 0 contains the digit. Selecting it.")
                chosen_video_path = candidate_video_paths[0]
                break
            elif video_1_ok:
                logger.info("    - Only video 1 contains the digit. Selecting it.")
                chosen_video_path = candidate_video_paths[1]
                break
            else:
                logger.info("    - Neither video contains the digit. Retrying...")
        
        if not chosen_video_path:
            logger.warning(f"  - WARNING: Failed to generate a valid video for scene {scene_data.scene_number} after {max_attempts} attempts. Selecting best from last attempt.")
            # Fallback: if no valid video was found after retries, still select the "best" from the last attempt
            chosen_video_path = select_best_video_locally(client, scene_data.video_prompt, candidate_video_paths)

        # Cleanup unselected videos for the current scene
        for p in candidate_video_paths:
            if p != chosen_video_path:
                try:
                    os.remove(p)
                    logger.info(f"  - Deleted unselected video: {p}")
                except OSError as e:
                    logger.warning(f"  - Error deleting unselected video {p}: {e}")

        chosen_video_paths.append(chosen_video_path)

        # Extract the last frame of the chosen video for continuity in the next scene
        last_frame_path = f"{scene_output_prefix}_chosen_last_frame.png"
        extract_last_frame(chosen_video_path, last_frame_path)
        
    # Final video composition
    final_video_path = str(base_output_dir / f"{company_name.replace(' ', '_')}_countdown.mp4")
    create_final_video(chosen_video_paths, final_video_path, speed_factor=4, fade_duration=1)

    logger.info("\n--- All steps completed successfully! ---")

if __name__ == "__main__":
    # This block is for standalone testing of generate_countdown_logic.py
    # In the full pipeline, this function is called from main.py
    
    # Parameters for the service
    _company_name_param = "The Burger Company"
    _countdown_start_param = 20
    
    # Constants
    _COUNTDOWN_END_NUMBER = 1
    _EXAMPLE_SCRIPT_PATH = os.path.join(config.ENGINEERED_PROMPTS_OUTPUT_DIR, "Google I⧸O '25 Keynote_analysis.txt")

    if not os.path.exists(_EXAMPLE_SCRIPT_PATH):
        logger.fatal(f"FATAL: Example script file not found at '{_EXAMPLE_SCRIPT_PATH}'.")
        logger.fatal("Please run 'main.py' first to generate the reverse-engineered prompts.")
    else:
        generate_video_from_prompts_service(
            company_name=_company_name_param,
            countdown_range=(_countdown_start_param, _COUNTDOWN_END_NUMBER),
            example_script_path=_EXAMPLE_SCRIPT_PATH
        )
