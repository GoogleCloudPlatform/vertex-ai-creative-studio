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

from models.shop_the_look_models import (
    CatalogRecord,
    GeneratedImageAccuracyWrapper,
    ModelRecord,
    ProgressionImages,
)


@me.stateclass
class PageState:
    """Mesop Page State"""

    # TAB NAV
    selected_tab_index: int = 0
    disabled: bool = False
    disabled_tab_indexes: set[int] = field(default_factory=lambda: {-1})
    mode = "/workflows-retail/lool"

    aspect_ratio: str = "9:16"
    video_length: int = 8  # 5-8

    # I2V reference Image
    reference_image_file_clothing: me.UploadedFile = None
    reference_image_file_key_clothing: int = 0
    reference_image_gcs_clothing: list[str] = field(default_factory=list)
    reference_image_uri_clothing: list[str] = field(default_factory=list)

    reference_image_file_model: me.UploadedFile = None
    reference_image_file_key_model: int = 0
    reference_image_gcs_model: str
    reference_image_uri_model: str

    is_loading: bool = False
    show_error_dialog: bool = False
    error_message: str = ""
    result_image: str
    timing: str
    look: int = 0
    catalog: list[CatalogRecord] = field(default_factory=list)
    models: list[ModelRecord] = field(default_factory=list)
    before_image_uri: str
    normal_accordion: dict[str, bool] = field(
        default_factory=lambda: {
            "retry_progression": True,
            "progression": True,
            "alternate": True,
        }
    )
    progression_images: list[ProgressionImages] = field(default_factory=list)
    retry_progression_images: list[ProgressionImages] = field(default_factory=list)
    alternate_progression_images: list[str] = field(default_factory=list)
    alternate_images: list[str] = field(default_factory=list)
    veo_prompt_input: str = (
        "Wide angle shot from a high-angle ceiling perspective captures a sleek model confidently striding down a brightly lit runway. Her full figure is elegantly presented, with every detail of her avant-garde ensemble visible, but the primary focus is drawn to her meticulously designed footwear. The shoes, perhaps gleaming architectural platforms or intricately embellished heels, are highlighted by the stark, dramatic spotlights illuminating the pristine runway below. The long, clean lines of the catwalk stretch into the distance, with the blurred, indistinct forms of the audience fading into the background, ensuring all attention remains on the model's powerful stride and the striking statement of her shoes. The elevated viewpoint offers a unique, almost abstract, composition that emphasizes the geometry of the runway and the singular importance of the footwear. The camera shot should be from 20 feet away."
    )
    result_video: str
    generate_alternate_views: bool
    selected_model: ModelRecord
    generate_video: bool = True
    result_images: list[str] = field(default_factory=list)
    veo_model = "2.0"
    current_status: str = ""
    vto_sample_count: str = "4"
    veo_sample_count: str = "2"
    look_description: str = ""
    final_accuracy: bool
    final_critic: GeneratedImageAccuracyWrapper = None
    tryon_started: bool = False
    articles: list[CatalogRecord] = field(default_factory=list)
    retry_counter: int = 0
    max_retry: str = "3"
    upload_everyone: bool = False
