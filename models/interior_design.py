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

"""Data structures for the Interior Design feature."""

from dataclasses import dataclass, field
import datetime


@dataclass
class StoryboardItem:
    room_name: str
    styled_image_uri: str
    # This list will store the history of styled images for this room
    style_history: list[str] = field(default_factory=list)
    transition_prompt: str | None = None


@dataclass
class InteriorDesignStoryboard:
    user_email: str
    timestamp: str
    # These are now optional
    original_floor_plan_uri: str | None = None
    generated_3d_view_uri: str | None = None
    room_names: list[str] = field(default_factory=list)
    storyboard_items: list[StoryboardItem] = field(default_factory=list)
    final_video_uri: str | None = None
