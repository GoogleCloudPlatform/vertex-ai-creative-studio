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

"""Backend logic for the Starter Pack page."""

import random
import json
from pathlib import Path

import models.gemini as gemini
from models.image_models import generate_virtual_models
from models.virtual_model_generator import VirtualModelGenerator, DEFAULT_PROMPT

def generate_starter_pack_from_look(look_image_uri: str) -> str:
    """Generates a starter pack from a look image."""
    prompt = "Analyze the image to extract the featured products for a mood board. Lay out only the articles / items, and not the person."
    alt_prompt = "Ultra-realistic 8K flat-lay photo in strict knolling style. Top-down 90º shot of the object from the attached image, fully disassembled into 8–12 key parts and arranged in a clean grid or radial pattern on a minimalist wooden or matte gray table. Even spacing, perfect alignment, no overlaps, no extra objects. Soft, diffused multi-source lighting with subtle shadows, neutral color balance and crisp focus across the whole frame. Highly detailed real-world materials (metal, plastic, rubber grips, circuit boards, screws). For every part, add a thin white rectangular frame and a short, sharp English label in clean sans-serif text, placed beside the component without covering it; annotations must be legible but unobtrusive."
    generated_images, _, _, _ = gemini.generate_image_from_prompt_and_images(
        prompt=prompt,
        images=[look_image_uri],
        aspect_ratio="1:1",
        gcs_folder="starter_pack_generations",
        file_prefix="starter_pack_from_look",
    )
    if generated_images:
        return generated_images[0]
    return ""

def generate_look_from_starter_pack(
    starter_pack_uri: str, model_image_uri: str
) -> str:
    """Generates a look from a starter pack and model image."""
    prompt = "Try this ensemble on the given model."
    generated_images, _, _, _ = gemini.generate_image_from_prompt_and_images(
        prompt=prompt,
        images=[starter_pack_uri, model_image_uri],
        aspect_ratio="1:1",
        gcs_folder="starter_pack_generations",
        file_prefix="look_from_starter_pack",
    )
    if generated_images:
        return generated_images[0]
    return ""

def generate_virtual_model() -> str:
    """Generates a virtual model image."""
    config_path = Path(__file__).parent.parent / "config/virtual_model_options.json"
    with open(config_path, "r") as f:
        options = json.load(f)

    selected_gender_obj = random.choice(options.get("genders", []))
    selected_silhouette_obj = random.choice(options.get("silhouette_presets", []))
    selected_mst_obj = random.choice(options.get("MST", []))
    selected_variant_obj = random.choice(options.get("variants", []))

    generator = VirtualModelGenerator(DEFAULT_PROMPT)
    generator.set_value("gender", selected_gender_obj["prompt_fragment"])
    generator.set_value("silhouette", selected_silhouette_obj["prompt_fragment"])
    generator.set_value("MST", selected_mst_obj["prompt_fragment"])
    generator.set_value("variant", selected_variant_obj["prompt_fragment"])
    prompt = generator.build_prompt()

    image_urls = generate_virtual_models(prompt=prompt, num_images=1)
    if image_urls:
        return image_urls[0]
    return ""