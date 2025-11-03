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

import mesop as me
from dataclasses import field

@me.stateclass
class CharacterConsistencyState:
    """State for the Character Consistency page."""
    uploaded_image_urls: list[str] = field(default_factory=list)
    scene_prompt: str = ""
    candidate_image_urls: list[str] = field(default_factory=list)
    best_image_url: str = ""
    outpainted_image_url: str = ""
    final_video_url: str = ""
    status_message: str = "Ready."
    is_generating: bool = False
