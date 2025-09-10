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
"""Component for displaying character consistency details."""

import mesop as me
from common.metadata import MediaItem
from common.utils import gcs_uri_to_https_url
import os
from components.download_button.download_button import download_button

from typing import Callable


@me.component
def character_consistency_details(item: MediaItem, on_click_permalink: Callable):
    """Renders the details for a character consistency item."""
    gcs_uri = item.gcsuri if item.gcsuri else (item.gcs_uris[0] if item.gcs_uris else None)
    item_display_url = gcs_uri_to_https_url(gcs_uri)
    
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=12,

        )
    ):

        if item.media_type == "character_consistency" and item.best_candidate_image:
            me.video(
                src=item_display_url,
                style=me.Style(
                    width="100%",
                    max_height="40vh",
                    border_radius=8,
                    background="#000",
                    display="block",
                    margin=me.Margin(bottom=16),
                ),
            )
            best_candidate_url = gcs_uri_to_https_url(item.best_candidate_image)
            me.text(
                "Best Candidate Image:",
                style=me.Style(
                    font_weight="500", margin=me.Margin(top=8)
                ),
            )
            me.image(
                src=best_candidate_url,
                style=me.Style(
                    max_width="250px",
                    height="auto",
                    border_radius=6,
                    margin=me.Margin(top=4),
                ),
            )
            if item.source_character_images:
                me.text(
                    "Source Images:",
                    style=me.Style(
                        font_weight="500", margin=me.Margin(top=8)
                    ),
                )
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=10
                    )
                ):
                    for src_image_uri in item.source_character_images[
                        :3
                    ]:
                        src_url = gcs_uri_to_https_url(src_image_uri)
                        me.image(
                            src=src_url,
                            style=me.Style(
                                max_width="150px",
                                height="auto",
                                border_radius=6,
                                margin=me.Margin(top=4),
                            ),
                        )
            with me.box(style=me.Style(display="flex", flex_direction="row", gap=10, margin=me.Margin(top=16))):
                with me.content_button(
                    on_click=on_click_permalink,
                    key=item.id or "",  # Ensure key is not None
                ):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            align_items="center",
                            gap=5,
                        )
                    ):
                        me.icon(icon="link")
                        me.text("permalink")

                if item.gcsuri:
                    filename = os.path.basename(item.gcsuri.split('?')[0])
                    download_button(url=item.gcsuri, filename=filename)