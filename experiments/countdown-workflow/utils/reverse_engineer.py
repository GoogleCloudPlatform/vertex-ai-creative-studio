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
import logging
import config
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Import the function from the new file
from utils.extract_frame import extract_first_frame

# Set up logging for this module
logger = logging.getLogger(__name__)

# --- Pydantic Schemas for Structured Output ---

class PromptAnalysis(BaseModel):
    """Schema for the inferred prompts for a single video chunk."""
    scene_number: int = Field(description="The sequential number of the video chunk, starting from 1.")
    image_prompt: Optional[str] = Field(default=None, description="The inferred Imagen prompt for the first frame of the entire video. This should only be present for the first scene.")
    video_prompt: str = Field(description="The inferred Veo prompt for this specific video chunk, including action, camera movement, and art style.")

class FullAnalysisResponse(BaseModel):
    """The root schema for the entire analysis, containing a list of chunk analyses."""
    analysis_results: List[PromptAnalysis]

def reverse_engineer_prompts(
    full_video_filepath: str, 
    chunks_dir: str, 
    output_dir: str = "engineered_prompts"
) -> Optional[Dict[str, Any]]:
    """
    Analyzes a full video and its chunks in a single multimodal prompt
    to infer the creative prompts that might have generated them.

    Args:
        full_video_filepath (str): Path to the original full video file.
        chunks_dir (str): Directory containing the video chunks.
        output_dir (str): Directory where the analysis results will be saved.

    Returns:
        Optional[Dict[str, Any]]: The parsed analysis data as a dictionary, or None if an error occurred.
    """
    if not os.path.exists(full_video_filepath):
        logger.error(f"Error: Full video file not found at {full_video_filepath}")
        return None
    if not os.path.exists(chunks_dir):
        logger.error(f"Error: Chunks directory not found at {chunks_dir}")
        return None

    # Initialize client for Vertex AI
    client = genai.Client(vertexai=True, project=config.GOOGLE_CLOUD_PROJECT, location=config.GOOGLE_CLOUD_LOCATION)

    logger.info(f"Starting prompt reverse engineering for videos in '{chunks_dir}' using model '{config.REVERSE_ENGINEERING_MODEL}' via Vertex AI...")

    video_files = [f for f in os.listdir(chunks_dir) if f.endswith(('.mp4', '.webm', '.mov'))]
    if not video_files:
        logger.warning(f"No video files found in '{chunks_dir}'.")
        return None

    video_files.sort()
    
    try:
        # --- Construct the single, large multimodal prompt ---
        contents: List[Any] = [
            "You are an expert in video generation models, specifically the Veo and Imagen models. "
            "Your task is to analyze a full video and a sequence of its 5-second chunks to infer the creative text prompts that would have generated them. "
            "For the very first chunk, analyze its first frame and generate a suitable prompt for an image generation model like Imagen. "
            "Then, for each 5-second chunk, provide a detailed Veo prompt that includes a description of the action, camera movement, and art style, using both the chunk's video content and its first frame for context. "
            "The final output must be a single JSON object that adheres to the provided schema.",
            "\n--- CONTEXT: FULL VIDEO ---",
        ]

        # 1. Add the full video for context
        logger.info(f"Preparing full video '{full_video_filepath}' for context...")
        with open(full_video_filepath, "rb") as f:
            video_bytes = f.read()
        contents.append(types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"))

        # 2. Add each chunk and its first frame sequentially
        for i, video_filename in enumerate(video_files):
            video_filepath = os.path.join(chunks_dir, video_filename)
            logger.info(f"Preparing chunk '{video_filename}'...")
            
            # Add the video chunk itself
            with open(video_filepath, "rb") as f:
                chunk_bytes = f.read()
            contents.extend([f"\n--- ANALYSIS TASK: CHUNK {i+1} ({video_filename}) ---", types.Part.from_bytes(data=chunk_bytes, mime_type="video/mp4")])

            # Extract and add the first frame of the chunk
            frame_image_path = f"temp_frame_{i}.jpg"
            if extract_first_frame(video_filepath, frame_image_path):
                logger.info(f"  - Preparing first frame image '{frame_image_path}'...")
                with open(frame_image_path, "rb") as f:
                    image_bytes = f.read()
                contents.extend(["  - First frame of this chunk for detailed analysis:", types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")])
                os.remove(frame_image_path)
            else:
                logger.warning(f"  - Could not extract the first frame for chunk {video_filename}.")


        # 4. Generate content with the single prompt
        logger.info("\nRequesting full analysis from the model...")
        response = client.models.generate_content(
            model=config.REVERSE_ENGINEERING_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FullAnalysisResponse,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=-1
                )
            )
        )

        # 5. Parse and save the structured response
        logger.info("\n--- Full Reverse Engineering Results ---")
        analysis_data = json.loads(response.text)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Determine output filenames based on the input video name
        base_filename = os.path.splitext(os.path.basename(full_video_filepath))[0]
        json_output_path = os.path.join(output_dir, f"{base_filename}_analysis.json")
        txt_output_path = os.path.join(output_dir, f"{base_filename}_analysis.txt")
        
        # Save the results to a JSON file
        with open(json_output_path, "w") as f:
            json.dump(analysis_data, f, indent=2)
        logger.info(f"Analysis complete. Results saved to '{json_output_path}'")

        # Save the results to a text file for easy reading
        with open(txt_output_path, "w") as f:
            for res in analysis_data["analysis_results"]:
                f.write(f"--- Scene Number: {res['scene_number']} ---\n")
                if res.get("image_prompt"):
                    f.write(f"Image Prompt: {res['image_prompt']}\n")
                f.write(f"Video Prompt: {res['video_prompt']}\n\n")
        logger.info(f"Results also saved to '{txt_output_path}'")
        
        return analysis_data

    except genai.errors.APIError as e:
        logger.error(f"API Error during generation: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    
    return None

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Example usage for standalone testing
    _full_video_filepath = "video/Google I⧸O '25 Keynote.mp4" # Replace with a valid path
    _chunks_dir = "chunks" # Replace with a valid path

    if os.path.exists(_full_video_filepath) and os.path.exists(_chunks_dir):
        reverse_engineer_prompts(_full_video_filepath, _chunks_dir)
    else:
        logger.warning(f"Cannot run standalone example: Video file '{_full_video_filepath}' or chunks directory '{_chunks_dir}' not found.")
