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

import mesop as me
from typing import Callable
from common.utils import gcs_uri_to_https_url

@me.component
def image_thumbnail(image_uri: str, index: int, on_remove: Callable, icon_size: int = 18):
    # Calculate the container dimension based on the icon size.
    # This creates a consistent 4px "padding" on all sides.
    box_dimension = icon_size + 8
    
    with me.box(style=me.Style(position="relative", width=100, height=100)):
        me.image(src=gcs_uri_to_https_url(image_uri), style=me.Style(width="100%", height="100%", border_radius=8, object_fit="cover"))
        with me.box(
            on_click=on_remove,
            key=str(index),
            style=me.Style(
                background="rgba(0, 0, 0, 0.5)",
                color="white",
                position="absolute",
                top=4,
                right=4,
                border_radius="50%",  # Use 50% for a perfect circle
                cursor="pointer",
                display="flex",
                align_items="center",
                justify_content="center",
                width=box_dimension,
                height=box_dimension,
            ),
        ):
            me.icon("close", style=me.Style(font_size=icon_size, transform="translate(2px, 3px)",))