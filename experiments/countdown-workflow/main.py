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
import os
import logging
from yt_dlp import YoutubeDL
import config
from utils.download_utils import download_ranges_callback, my_progress_hook, get_downloaded_filepath
from utils.split_video import split_video_into_chunks
from utils.reverse_engineer import reverse_engineer_prompts
from utils.generate_countdown_logic import generate_video_from_prompts_service

# Set up logging for this module
logger = logging.getLogger(__name__)

def main():
    # Setup logging as configured in config.py
    config.setup_logging()
    logger.info("Starting the AI-Powered Branded Countdown Video Generator.")

    if not config.SKIP_REVERSE_ENGINEERING:

        # --- Stage 1: Configuration for Video Style Analysis ---
        video_url = "https://www.youtube.com/watch?v=o8NiE3XMPrM"
        start_time = "00:00:10"
        end_time = "00:00:55"
        chunk_duration = 5
        
        # --- Stage 1: 1. Download Video Segment ---
        logger.info("--- Stage 1: Step 1: Downloading video segment ---")
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'download_ranges': download_ranges_callback,
            'force_keyframes_at_cuts': True,
            'outtmpl': os.path.join(config.VIDEO_OUTPUT_DIR, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [my_progress_hook],
            'overwrites': True,
            # Pass custom params to the callback
            'start_time': start_time,
            'end_time': end_time,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(video_url, download=True)
        except Exception as e:
            logger.error(f"Error during video download: {e}")
            return

        downloaded_filepath = get_downloaded_filepath()
        if not downloaded_filepath:
            logger.error("Download failed. Aborting Stage 1.")
            return

        # --- Stage 1: 2. Split Video into Chunks ---
        logger.info("\n--- Stage 1: Step 2: Splitting video into chunks ---")
        split_video_into_chunks(downloaded_filepath, chunk_duration, config.CHUNKS_OUTPUT_DIR)

        # --- Stage 1: 3. Reverse Engineer Prompts ---
        logger.info("\n--- Stage 1: Step 3: Reverse engineering prompts from chunks ---")
        reverse_engineer_prompts(downloaded_filepath, config.CHUNKS_OUTPUT_DIR, config.ENGINEERED_PROMPTS_OUTPUT_DIR)

        logger.info("\n--- Stage 1: All steps completed successfully! ---")
    
    # --- Stage 2: Configuration for Branded Video Generation ---
    company_name_param = "CocaCola"
    countdown_start_param = 20
    COUNTDOWN_END_NUMBER = 1

    # --- Stage 2: Generate Branded Countdown Video ---
    logger.info("\n--- Stage 2: Generating Branded Countdown Video ---")

    EXAMPLE_SCRIPT_PATH = os.path.join(config.ENGINEERED_PROMPTS_OUTPUT_DIR, "Google I⧸O '25 Keynote_analysis.txt")

    generate_video_from_prompts_service(
        company_name=company_name_param,
        countdown_range=(countdown_start_param, COUNTDOWN_END_NUMBER),
        example_script_path=EXAMPLE_SCRIPT_PATH
    )

    logger.info("\n--- All pipelines completed successfully! ---")

if __name__ == "__main__":
    main()
