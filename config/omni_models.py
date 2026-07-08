# Copyright 2026 Google LLC
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

from dataclasses import dataclass
from typing import Optional


@dataclass
class OmniModelConfig:
    """Configuration for a specific Gemini Omni model version."""

    version_id: str
    model_name: str
    display_name: str
    supported_modes: list[str]
    supported_aspect_ratios: list[str]
    resolutions: list[str]
    min_duration: int
    max_duration: int
    default_duration: int
    max_samples: int
    default_samples: int


# Single source of truth for all Omni model configurations.
OMNI_MODELS: list[OmniModelConfig] = [
    OmniModelConfig(
        version_id="gemini-omni-flash-preview",
        model_name="gemini-omni-flash-preview",
        display_name="Gemini Omni Flash (Preview)",
        supported_modes=["t2v", "i2v", "ref2v", "edit"],
        supported_aspect_ratios=["16:9", "9:16"],
        resolutions=["720p"],
        min_duration=3,
        max_duration=10,
        default_duration=10,
        max_samples=1,  # Quota limits focus on 1 sample
        default_samples=1,
    ),
]


def get_omni_model_config(version_id: str) -> Optional[OmniModelConfig]:
    """Finds and returns the configuration for a given Omni model version_id."""
    for model in OMNI_MODELS:
        if model.version_id == version_id:
            return model
    return None


def get_models_by_mode(mode: str) -> list[OmniModelConfig]:
    """Finds and returns all model configurations that support a specific mode."""
    return [model for model in OMNI_MODELS if mode in model.supported_modes]


def get_version_id_by_model_name(model_name: str) -> Optional[str]:
    """Finds the version_id corresponding to a specific model_name."""
    for model in OMNI_MODELS:
        if model.model_name == model_name:
            return model.version_id
    return None


from config.default import Default

cfg = Default()
DEFAULT_OMNI_VERSION_ID = (
    get_version_id_by_model_name(cfg.DEFAULT_OMNI_MODEL_NAME)
    or "gemini-omni-flash-preview"
)
