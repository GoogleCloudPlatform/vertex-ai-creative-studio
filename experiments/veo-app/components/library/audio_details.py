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
"""Component for displaying audio details."""

import json
import mesop as me
from common.metadata import MediaItem
from common.utils import gcs_uri_to_https_url
from datetime import datetime
import os
from components.download_button.download_button import download_button

from typing import Callable

@me.component
def audio_details(item: MediaItem, on_click_permalink: Callable):
    """Renders the details for an audio item."""
    gcs_uri = item.gcsuri if item.gcsuri else (item.gcs_uris[0] if item.gcs_uris else None)
    item_display_url = gcs_uri_to_https_url(gcs_uri)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=12,
            width="100%",
            max_height="80vh",  # Max viewport height
            overflow_y="auto",  # Scroll if content exceeds max height
        )
    ):

        if item_display_url and not item.error_message:
            me.audio(
                src=item_display_url,
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
        if item.rewritten_prompt:
            me.text(f'Rewritten Prompt: "{item.rewritten_prompt}"')

        dialog_timestamp_str_detail = "N/A"
        if item.timestamp:
            try:
                ts_str_detail = item.timestamp
                if isinstance(item.timestamp, datetime):
                    ts_str_detail = item.timestamp.isoformat()
                dialog_timestamp_str_detail = datetime.fromisoformat(
                    ts_str_detail.replace("Z", "+00:00")
                ).strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                )
            except Exception:
                dialog_timestamp_str_detail = str(item.timestamp)
        me.text(f"Generated: {dialog_timestamp_str_detail}")

        if item.generation_time is not None:
            me.text(f"Generation Time: {round(item.generation_time, 2)} seconds")

        if item.model is not None:
            me.text(f"Model: {item.model}")

        if item.duration is not None:
            me.text(f"Duration: {item.duration} seconds")
        
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