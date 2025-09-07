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
from typing import List, Optional

@dataclass
class VeoModelConfig:
    """Configuration for a specific VEO model version."""
    version_id: str
    model_name: str
    display_name: str
    supported_modes: List[str]
    supported_aspect_ratios: List[str]
    resolutions: List[str]
    min_duration: int
    max_duration: int
    default_duration: int
    max_samples: int
    default_samples: int
    supports_prompt_enhancement: bool

# This list is the single source of truth for all VEO model configurations.
VEO_MODELS: List[VeoModelConfig] = [
    VeoModelConfig(
        version_id="2.0",
        model_name="veo-2.0-generate-001",
        display_name="Veo 2.0",
        supported_modes=["t2v", "i2v", "interpolation"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p"],
        min_duration=5,
        max_duration=8,
        default_duration=5,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
    ),
    VeoModelConfig(
        version_id="3.0",
        model_name="veo-3.0-generate-001",
        display_name="Veo 3.0",
        supported_modes=["t2v", "i2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p"],
        min_duration=8,
        max_duration=8,
        default_duration=8,
        max_samples=2,
        default_samples=1,
        supports_prompt_enhancement=False,
    ),
    VeoModelConfig(
        version_id="3.0-fast",
        model_name="veo-3.0-fast-generate-001",
        display_name="Veo 3.0 Fast",
        supported_modes=["t2v", "i2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p"],
        min_duration=8,
        max_duration=8,
        default_duration=8,
        max_samples=2,
        default_samples=1,
        supports_prompt_enhancement=False,
    ),
]

# Helper function to easily find a model's config by its version_id.
def get_veo_model_config(version_id: str) -> Optional[VeoModelConfig]:
    """Finds and returns the configuration for a given VEO model version_id."""
    for model in VEO_MODELS:
        if model.version_id == version_id:
            return model
    return None
