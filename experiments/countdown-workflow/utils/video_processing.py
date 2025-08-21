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

import pathlib
import logging
from typing import List, Optional
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import MultiplySpeed, FadeOut

# Set up logging for this module
logger = logging.getLogger(__name__)

def create_final_video(
    video_paths: List[str], 
    output_path: str,
    speed_factor: float = 4.0, 
    fade_duration: float = 1.0
) -> Optional[str]:
    """
    Speeds up, concatenates video clips, adds a fade-out, and adds music.

    Args:
        video_paths (List[str]): A list of paths to the video clips to concatenate.
        output_path (str): The path where the final video will be saved.
        speed_factor (float): The factor by which to speed up each video clip.
        fade_duration (float): The duration of the fade-out transition in seconds.

    Returns:
        Optional[str]: The path to the created final video, or None if an error occurred.
    """
    logger.info("\n--- Creating Final Video ---")
    sped_up_clips: List[VideoFileClip] = []
    speed_effect = MultiplySpeed(factor=speed_factor)
    fade_effect = FadeOut(duration=fade_duration)
    final_clip: Optional[VideoFileClip] = None

    try:
        # Process clips
        for path in video_paths:
            try:
                clip = VideoFileClip(str(path))
                sped_up_clip = speed_effect.apply(clip)
                sped_up_clips.append(sped_up_clip)
                logger.info(f"Processed and sped up: {path}")
            except Exception as e:
                logger.error(f"Error processing file {path} with moviepy: {e}")
                # Ensure all opened clips are closed in case of an error during processing
                for c in sped_up_clips:
                    c.close()
                return None

        if not sped_up_clips:
            logger.warning("No clips were processed.")
            return None

        final_clip = concatenate_videoclips(sped_up_clips)
        final_clip_with_fade = fade_effect.apply(final_clip)

        # Add music to clip
        # Assuming music.mp3 is in the same directory as this script (utils/)
        SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
        audio_path = SCRIPT_DIR / "music.mp3"

        final_clip_with_music: VideoFileClip
        if not audio_path.exists():
            logger.warning(f"Warning: Music file not found at {audio_path}. Proceeding without music.")
            final_clip_with_music = final_clip_with_fade
        else:
            audio_clip = AudioFileClip(str(audio_path))
            if audio_clip.duration > final_clip_with_fade.duration:
                audio_clip = audio_clip.subclipped(0, final_clip_with_fade.duration)
            final_clip_with_music = final_clip_with_fade.with_audio(audio_clip)

        final_clip_with_music.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            logger=None # Suppress MoviePy's internal logging to avoid duplicate messages
        )
        
        logger.info(f"Successfully created final video: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"An error occurred during final video creation: {e}")
        return None
    finally:
        # Ensure all clips are closed to release resources
        for clip in sped_up_clips:
            clip.close()
        if final_clip:
            final_clip.close()
