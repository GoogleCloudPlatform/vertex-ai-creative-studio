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
import logging
from moviepy import VideoFileClip

# Set up logging for this module
logger = logging.getLogger(__name__)

def extract_first_frame(video_path: str, output_image_path: str) -> bool:
    """
    Extracts the first frame of a video and saves it as an image.

    Args:
        video_path (str): The path to the input video file.
        output_image_path (str): The path to save the output image file.
    Returns:
        bool: True if the frame was extracted successfully, False otherwise.
    """
    if not os.path.exists(video_path):
        logger.error(f"Error: Video file not found at {video_path}")
        return False

    try:
        logger.info(f"Extracting first frame from '{video_path}'...")
        with VideoFileClip(video_path) as clip:
            clip.save_frame(output_image_path, t=0)  # t=0 saves the very first frame
        logger.info(f"First frame saved successfully to '{output_image_path}'")
        return True
    except Exception as e:
        logger.error(f"An error occurred while extracting the frame: {e}")
        return False

def extract_last_frame(video_path: str, output_image_path: str) -> bool:
    """
    Extracts the last frame of a video and saves it as an image.

    Args:
        video_path (str): The path to the input video file.
        output_image_path (str): The path to save the output image file.
    Returns:
        bool: True if the frame was extracted successfully, False otherwise.
    """
    if not os.path.exists(video_path):
        logger.error(f"Error: Video file not found at {video_path}")
        return False

    try:
        logger.info(f"Extracting last frame from '{video_path}'...")
        with VideoFileClip(video_path) as clip:
            # Calculate the time of the last frame precisely
            if clip.fps:
                last_frame_time = clip.duration - (1 / clip.fps)
            else:
                # Fallback for clips without fps, though less precise
                last_frame_time = clip.duration - 0.01
            
            # Ensure the time is not negative
            last_frame_time = max(0, last_frame_time)

            clip.save_frame(output_image_path, t=last_frame_time)
        logger.info(f"Last frame saved successfully to '{output_image_path}'")
        return True
    except Exception as e:
        logger.error(f"An error occurred while extracting the frame: {e}")
        return False

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Configuration for standalone execution ---
    # This is an example of how to use the functions.
    # You would replace these paths with your actual video file.
    
    # Example: After running main.py, you might use the downloaded video.
    INPUT_VIDEO = "video/Google I⧸O '25 Keynote.mp4"
    OUTPUT_FIRST_FRAME = "first_frame.jpg"
    OUTPUT_LAST_FRAME = "last_frame.jpg"

    if os.path.exists(INPUT_VIDEO):
        logger.info("--- Testing First Frame Extraction ---")
        extract_first_frame(INPUT_VIDEO, OUTPUT_FIRST_FRAME)
        
        logger.info("\n--- Testing Last Frame Extraction ---")
        extract_last_frame(INPUT_VIDEO, OUTPUT_LAST_FRAME)
    else:
        logger.warning(f"Example video not found at '{INPUT_VIDEO}'. Please update the path.")
