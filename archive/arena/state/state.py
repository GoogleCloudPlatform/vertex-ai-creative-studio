# Copyright 2024 Google LLC
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

from config.default import Default
from models.set_up import load_default_models

cnfg = Default()


@me.stateclass
class AppState:
    """Mesop Application State"""

    theme_mode: str = "light"
    sidenav_open: bool = True
    
    welcome_message: str = "Welcome to Arena!"

    name: str = "Google Cloud Next 2025 Attendee"  # Default name for the user
    study: str = "live"
    study_prompts_location: str = "prompts/imagen_prompts.json"
    study_models: list[str] = field(default_factory=list)
    track_study_in_spanner: bool = False
