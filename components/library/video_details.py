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
"""Component for displaying video details."""

import os
from datetime import datetime
from typing import Callable

import mesop as me

from common.metadata import MediaItem
from common.utils import gcs_uri_to_https_url
from components.download_button.download_button import download_button
from components.pill import pill
from ..video_thumbnail.video_thumbnail import video_thumbnail


@me.component
def video_details(
    item: MediaItem,
    on_click_permalink: Callable,
    selected_url: str,
    on_thumbnail_click: Callable,
):
    """Renders the details for a video item, including a gallery for multiple videos."""

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=12,
        )
    ):
        # Main video player
        if selected_url and not item.error_message:
            me.video(
                key=selected_url, # Add key to force re-render
                src=gcs_uri_to_https_url(selected_url),
                style=me.Style(
                    width="100%",
                    max_height="40vh",
                    border_radius=8,
                    background="#000",
                    display="block",
                    margin=me.Margin(bottom=16),
                ),
            )

        # Thumbnail strip for multiple videos
        if item.gcs_uris and len(item.gcs_uris) > 1:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=16,
                    justify_content="center",
                    margin=me.Margin(top=16, bottom=16),
                    flex_wrap="wrap",
                )
            ):
                for url in item.gcs_uris:
                    is_selected = url == selected_url
                    with me.box(style=me.Style(height="90px", width="160px")):
                        video_thumbnail(
                            key=url,
                            video_src=gcs_uri_to_https_url(url),
                            selected=is_selected,
                            on_click=on_thumbnail_click,
                        )

        if item.error_message:
            me.text(
                f"Error: {item.error_message}",
                style=me.Style(
                    color=me.theme_var("error"),
                    font_style="italic",
                    padding=me.Padding.all(8),
                    background=me.theme_var("error-container"),
                    border_radius=4,
                    margin=me.Margin(bottom=10),
                ),
            )

        me.text(f"Model: {item.raw_data['model']}")
        me.text(f'Prompt: "{item.prompt or "N/A"}"')
        if item.negative_prompt:
            me.text(f'Negative Prompt: "{item.negative_prompt}"')
        if item.enhanced_prompt_used:
            me.text(f'Enhanced Prompt: "{item.enhanced_prompt_used}"')

        dialog_timestamp_str_detail = "N/A"
        if item.timestamp:
            try:
                ts_str_detail = item.timestamp
                if isinstance(item.timestamp, datetime):
                    ts_str_detail = item.timestamp.isoformat()
                dialog_timestamp_str_detail = datetime.fromisoformat(
                    ts_str_detail.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M:%S %Z")
            except Exception:
                dialog_timestamp_str_detail = str(item.timestamp)
        me.text(f"Generated: {dialog_timestamp_str_detail}")

        if item.generation_time is not None:
            me.text(f"Generation Time: {round(item.generation_time, 2)} seconds")

        if item.model is not None:
            me.text(f"Model: {item.model}")

        if item.aspect:
            me.text(f"Aspect Ratio: {item.aspect}")
        if item.duration is not None:
            me.text(f"Duration: {item.duration} seconds")
        
        # Display resolution with a pill
        res_label = item.resolution or "720p"
        with me.box(style=me.Style(display="flex", align_items="center", gap=8)):
            me.text("Resolution: ")
            pill(label=res_label, pill_type="resolution_4k" if res_label == "4k" else "resolution")

        if item.reference_image:
            ref_url = gcs_uri_to_https_url(item.reference_image)
            me.text(
                "Reference Image:",
                style=me.Style(
                    font_weight="500",
                    margin=me.Margin(top=8),
                ),
            )
            me.image(
                src=ref_url,
                style=me.Style(
                    max_width="250px",
                    height="auto",
                    border_radius=6,
                    margin=me.Margin(top=4),
                ),
            )
        if item.last_reference_image:
            last_ref_url = gcs_uri_to_https_url(item.last_reference_image)
            me.text(
                "Last Reference Image:",
                style=me.Style(font_weight="500", margin=me.Margin(top=8)),
            )
            me.image(
                src=last_ref_url,
                style=me.Style(
                    max_width="250px",
                    height="auto",
                    border_radius=6,
                    margin=me.Margin(top=4),
                ),
            )

        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=10, margin=me.Margin(top=16)
            )
        ):
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

            # Download button should download the selected video
            if selected_url:
                filename = os.path.basename(selected_url.split("?")[0])
                download_button(url=selected_url, filename=filename)
