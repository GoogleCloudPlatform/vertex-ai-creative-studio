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
""" Default Configuration for Creative Studio """

import os
from dataclasses import dataclass, field
from vertexai.generative_models import HarmBlockThreshold

from models.image_models import ImageModel


@dataclass
class GeminiModelConfig:
    """Configuration specific to Gemini models."""

    generation: dict = field(default_factory=dict)
    safety_settings: dict = field(default_factory=dict)
    tools: dict = field(default_factory=dict)
    grounding_source: object = None

    def __repr__(self):
        params = []
        for k, v in self.generation.items():
            params.append(f"generation_{k}={v}")
        for k, v in self.safety_settings.items():
            params.append(f"safety_{k}={v}")
        for k, v in self.tools.items():
            params.append(f"tools_{k}={v}")
        if self.grounding_source:
            params.append("grounding=ON")
        return f"ModelConfig({', '.join(params)})"


@dataclass
class Config:
    """All configuration variables for this solution should be managed here."""

    TITLE = "IMAGEN CREATIVE STUDIO"
    IMAGE_CREATION_BUCKET = os.environ.get("IMAGE_CREATION_BUCKET", "")
    PROJECT_ID = os.environ.get("PROJECT_ID", "")
    LOCATION = os.getenv("LOCATION", "us-central1")
    MODEL_GEMINI_MULTIMODAL = "gemini-1.5-flash"
    MODEL_IMAGEN2 = "imagegeneration@006"
    MODEL_IMAGEN_NANO = "imagegeneration@004"
    MODEL_IMAGEN3_FAST = "imagen-3.0-fast-generate-001"
    MODEL_IMAGEN3 = "imagen-3.0-generate-001"
    TEMPERATURE = 0.8
    TOP_P = 0.97
    TOP_K = 40
    MAX_OUTPUT_TOKENS = 2048
    IMAGEN_PROMPTS_JSON = "prompts/imagen_prompts.json"
    image_modifiers: list[str] = field(
        default_factory=lambda: [
            "aspect_ratio",
            "content_type",
            "color_tone",
            "lighting",
            "composition",
        ]
    )
    gemini_settings: GeminiModelConfig = field(
        default_factory=GeminiModelConfig, init=False
    )
    display_image_models: list[ImageModel] = field(
        default_factory=lambda: [
            {"display": "Imagen 3 Fast", "model_name": Config.MODEL_IMAGEN3_FAST},
            {"display": "Imagen 3", "model_name": Config.MODEL_IMAGEN3},
        ]
    )

    def __post_init__(self):
        """Initialize fields that depend on other fields or require complex logic."""
        self.gemini_settings.generation["temperature"] = self.TEMPERATURE
        self.gemini_settings.generation["top_p"] = self.TOP_P
        self.gemini_settings.generation["top_k"] = self.TOP_K
        self.gemini_settings.generation["max_output_tokens"] = self.MAX_OUTPUT_TOKENS
        self.gemini_settings.generation["candidate_count"] = 1
        self.gemini_settings.generation["stop_sequences"] = []
        self.gemini_settings.safety_settings["HARASSMENT"] = (
            HarmBlockThreshold.BLOCK_ONLY_HIGH
        )
        self.gemini_settings.safety_settings["HATE_SPEECH"] = (
            HarmBlockThreshold.BLOCK_ONLY_HIGH
        )
        self.gemini_settings.safety_settings["SEXUALLY_EXPLICIT"] = (
            HarmBlockThreshold.BLOCK_ONLY_HIGH
        )
        self.gemini_settings.safety_settings["DANGEROUS_CONTENT"] = (
            HarmBlockThreshold.BLOCK_ONLY_HIGH
        )
