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

from dataclasses import field
import mesop as me

@me.stateclass
class PageState:
    """Storyboarder Page State"""
    
    # Input
    prompt: str = ""
    uploaded_image_gcs_uris: list[str] = field(default_factory=list)
    uploaded_image_display_urls: list[str] = field(default_factory=list)
    
    # Image Generation
    generated_image_urls: list[str] = field(default_factory=list)
    generated_image_gcs_uris: list[str] = field(default_factory=list)
    image_captions: list[str] = field(default_factory=list)
    is_generating_images: bool = False
    
    # Video Generation
    is_generating_video: bool = False
    video_generation_status: str = ""
    generated_video_clips: list[str] = field(default_factory=list) # List of GCS URIs
    final_video_uri: str = ""
    final_video_display_url: str = ""
    
    # Audio/Voiceover
    voiceover_script: str = ""
    voiceover_audio_uri: str = ""
    is_generating_script: bool = False
    is_generating_audio: bool = False
    final_video_with_audio_uri: str = ""
    final_video_with_audio_display_url: str = ""
    
    # Settings
    aspect_ratio: str = "16:9"
    num_images: int = 4
    
    # UI
    show_snackbar: bool = False
    snackbar_message: str = ""
    info_dialog_open: bool = False
