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
from typing import Dict, List, Optional


@dataclass
class ModeOverride:
    """Defines specific overrides for a particular mode."""

    supported_durations: Optional[List[int]] = None
    default_duration: Optional[int] = None
    supports_style_reference: bool = True
    supported_aspect_ratios: Optional[List[str]] = None


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
    requires_prompt_enhancement: bool = False
    default_prompt_enhancement: bool = True
    supported_durations: Optional[List[int]] = None
    mode_overrides: Optional[Dict[str, ModeOverride]] = None
    supports_video_extension: bool = False
    supported_extension_durations: Optional[List[int]] = None


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
        default_prompt_enhancement=True,
        supports_video_extension=True,
        supported_extension_durations=[7],
    ),
    VeoModelConfig(
        version_id="2.0-exp",
        model_name="veo-2.0-generate-exp",
        display_name="Veo 2.0 Exp",
        supported_modes=["t2v", "i2v", "interpolation", "r2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p"],
        min_duration=5,
        max_duration=8,
        default_duration=5,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=False,
        default_prompt_enhancement=False,
        mode_overrides={
            "r2v": ModeOverride(supported_durations=[8], default_duration=8)
        },
    ),
    VeoModelConfig(
        version_id="3.0",
        model_name="veo-3.0-generate-001",
        display_name="Veo 3.0",
        supported_modes=["t2v", "i2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p"],
        min_duration=4,
        max_duration=8,
        default_duration=8,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
        requires_prompt_enhancement=True,
        default_prompt_enhancement=True,
        supported_durations=[4, 6, 8],
    ),
    VeoModelConfig(
        version_id="3.0-fast",
        model_name="veo-3.0-fast-generate-001",
        display_name="Veo 3.0 Fast",
        supported_modes=["t2v", "i2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p"],
        min_duration=4,
        max_duration=8,
        default_duration=8,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
        requires_prompt_enhancement=True,
        default_prompt_enhancement=True,
        supported_durations=[4, 6, 8],
    ),
    VeoModelConfig(
        version_id="3.1-fast",
        model_name="veo-3.1-fast-generate-001",
        display_name="Veo 3.1 Fast",
        supported_modes=["t2v", "i2v", "interpolation"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p", "4k"],
        min_duration=4,
        max_duration=8,
        default_duration=8,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
        requires_prompt_enhancement=True,
        default_prompt_enhancement=True,
        supported_durations=[4, 6, 8],
    ),
    VeoModelConfig(
        version_id="3.1-fast-preview",
        model_name="veo-3.1-fast-generate-preview",
        display_name="Veo 3.1 Fast Preview",
        supported_modes=["t2v", "i2v", "interpolation", "r2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p", "4k"],
        min_duration=4,
        max_duration=8,
        default_duration=8,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
        requires_prompt_enhancement=True,
        default_prompt_enhancement=True,
        supported_durations=[4, 6, 8],
        supports_video_extension=True,
        supported_extension_durations=[7],
        mode_overrides={
            "r2v": ModeOverride(
                supported_durations=[8],
                default_duration=8,
                supports_style_reference=True,
                supported_aspect_ratios=["16:9", "9:16"],
            ),
        },
    ),
    VeoModelConfig(
        version_id="3.1",
        model_name="veo-3.1-generate-001",
        display_name="Veo 3.1",
        supported_modes=["t2v", "i2v", "interpolation"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p", "4k"],
        min_duration=4,
        max_duration=8,
        default_duration=8,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
        requires_prompt_enhancement=True,
        default_prompt_enhancement=True,
        supported_durations=[4, 6, 8],
    ),
    VeoModelConfig(
        version_id="3.1-preview",
        model_name="veo-3.1-generate-preview",
        display_name="Veo 3.1 preview",
        supported_modes=["t2v", "i2v", "interpolation", "r2v"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p", "1080p", "4k"],
        min_duration=4,
        max_duration=8,
        default_duration=8,
        max_samples=4,
        default_samples=1,
        supports_prompt_enhancement=True,
        requires_prompt_enhancement=True,
        default_prompt_enhancement=True,
        supported_durations=[4, 6, 8],
        supports_video_extension=True,
        supported_extension_durations=[7],
        mode_overrides={
            "r2v": ModeOverride(
                supported_durations=[8],
                default_duration=8,
                supports_style_reference=True,
                supported_aspect_ratios=["16:9", "9:16"],
            ),
        },
    ),
]

# Helper function to easily find a model's config by its version_id.
def get_veo_model_config(version_id: str) -> Optional[VeoModelConfig]:
    """Finds and returns the configuration for a given VEO model version_id."""
    for model in VEO_MODELS:
        if model.version_id == version_id:
            return model
    return None
