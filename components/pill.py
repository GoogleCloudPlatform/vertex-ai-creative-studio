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
"""Pill mesop component"""

from typing import List, Optional

import mesop as me


@me.component
def pill(label: str, pill_type: str):
    background_color = me.theme_var("on-secondary-fixed-variant")
    text_color = me.theme_var("onsurface")

    if pill_type == "gen_i2v":
        background_color = me.theme_var("tertiary-container")
        text_color = me.theme_var("on-tertiary-container")
    elif pill_type == "gen_t2v":
        background_color = me.theme_var("secondary-container")
        text_color = me.theme_var("on-secondary-container")
    elif pill_type == "aspect":
        background_color = me.theme_var("primary-container")
        text_color = me.theme_var("on-primarycontainer")
    elif pill_type == "duration" or pill_type == "fps" or pill_type == "multi_image_count":
        background_color = me.theme_var("surface-variant")
        text_color = me.theme_var("on-surface-variant")
    elif pill_type == "resolution":
        background_color = me.theme_var("surface-container-high")
        text_color = me.theme_var("on-surface")
    elif pill_type == "resolution_4k":
        # A distinctive gold-themed style for 4K
        background_color = "#FFD700"  # Gold
        text_color = "#000000"  # Black for high contrast
    elif (
        pill_type == "media_type_audio"
        or pill_type == "media_type_video"
        or pill_type == "media_type_image"
    ):
        background_color = me.theme_var("inverse-primary")
        text_color = me.theme_var("on-surface-variant")
    elif pill_type == "error_present":
        background_color = me.theme_var("error-container")
    elif pill_type == "genre":
        background_color = me.theme_var("secondary-container")
        text_color = me.theme_var("on-scecondary-container")
    elif pill_type == "stage":
        background_color = me.theme_var("secondary-container")
        text_color = me.theme_var("on-scecondary-container")
    elif pill_type == "multi_video":
        background_color = me.theme_var("secondary-container")
        text_color = me.theme_var("on-scecondary-container")

    me.text(
        str(label),  # Ensure label is a string
        style=me.Style(
            background=background_color,
            color=text_color,
            border_radius="16px",
            text_align="center",
            font_size="0.75rem",
            font_weight="medium",
            display="inline-flex",
            padding=me.Padding(top=4, bottom=4, left=8, right=8),
            line_height="1",
        ),
    )
