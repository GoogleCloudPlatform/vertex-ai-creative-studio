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
import math
import logging
from moviepy import VideoFileClip
from typing import Optional

# Set up logging for this module
logger = logging.getLogger(__name__)

def split_video_into_chunks(
    input_filepath: str, 
    chunk_duration_seconds: int = 5, 
    output_dir: Optional[str] = None
) -> None:
    """
    Splits a video file into smaller, equal-duration chunks.

    Args:
        input_filepath (str): The path to the input video file.
        chunk_duration_seconds (int): The desired duration of each video chunk in seconds.
        output_dir (Optional[str]): The directory where the video chunks will be saved.
                                     If None, chunks will not be saved.
    """
    if not os.path.exists(input_filepath):
        logger.error(f"Error: Input video file not found at {input_filepath}")
        return

    if output_dir is None:
        logger.error("Error: output_dir must be provided to save video chunks.")
        return

    try:
        with VideoFileClip(input_filepath) as clip:
            duration = clip.duration
            if duration is None:
                logger.error("Could not determine video duration.")
                return

            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(input_filepath))[0]
            extension = os.path.splitext(input_filepath)[1]

            num_chunks = math.ceil(duration / chunk_duration_seconds)
            # Adjust num_chunks to stop at n-1, effectively skipping the last chunk
            # If num_chunks is 1, this will result in 0, meaning no chunks are processed.
            # If num_chunks is 0 (e.g., video too short), this will also result in 0.
            num_chunks_to_process = max(0, num_chunks - 1) 
            logger.info(f"Splitting '{input_filepath}' (Duration: {duration:.2f}s) into {num_chunks_to_process} chunks (skipping the last one) of {chunk_duration_seconds}s...")

            # Iterate through chunks, stopping at n-1
            for i in range(num_chunks_to_process):
                start_time = i * chunk_duration_seconds
                end_time = min(duration, start_time + chunk_duration_seconds) # Ensure end_time does not exceed video duration

                output_filename = os.path.join(output_dir, f"{base_name}_chunk_{i+1:03d}{extension}")
                
                logger.info(f"Processing chunk {i+1}/{num_chunks_to_process}: {output_filename} (from {start_time:.2f}s to {end_time:.2f}s)")
                try:
                    subclip = clip.subclipped(start_time, end_time) # Use subclip for precise start/end
                    subclip.write_videofile(output_filename, codec="libx264", audio_codec="aac", logger=None)
                    logger.info(f"Successfully created {output_filename}")
                except Exception as e:
                    logger.error(f"Error splitting chunk {i+1}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error loading video with MoviePy. Ensure FFmpeg is installed and the video file is valid: {e}")
        return
