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

from dataclasses import dataclass, field

import mesop as me

from config.imagen_models import IMAGEN_MODELS


@dataclass
@me.stateclass
class PageState:
    """Local Page State"""

    # Image generation model selection and output
    image_output: list[str] = field(default_factory=list)
    image_commentary: str = ""
    image_model_name: str = "imagen-4.0-generate-001"

    # General UI state
    is_loading: bool = False
    show_advanced: bool = False
    error_message: str = ""
    show_dialog: bool = False
    dialog_message: str = ""

    info_dialog_open: bool = False

    # Image prompt and related settings
    image_prompt_input: str = ""
    image_prompt_placeholder: str = ""
    image_textarea_key: int = 0  # Used as str(key) for component

    image_negative_prompt_input: str = ""
    image_negative_prompt_placeholder: str = ""
    image_negative_prompt_key: int = 0  # Used as str(key) for component

    # Image generation parameters
    imagen_watermark: bool = True  # SynthID notice implies watermark is active
    imagen_seed: int = 0
    imagen_image_count: int = 4

    # Image style modifiers
    image_content_type: str = "Photo"
    image_color_tone: str = "Cool tone"
    image_lighting: str = "Golden hour"
    image_composition: str = "Wide angle"
    image_aspect_ratio: str = "1:1"

    timing: str = ""  # For displaying generation time
