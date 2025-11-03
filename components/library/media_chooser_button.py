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

"""A generic, stateless media chooser button component."""

from collections.abc import Callable
from typing import Optional

import mesop as me


@me.component
def media_chooser_button(
    *,
    on_click: Callable[[me.ClickEvent], None],
    media_type: str,  # "video", "audio", or "image"
    button_label: Optional[str] = None,
    button_type: str = "stroked",
    key: str,
):
    """
    Renders a simple, stateless button for choosing media.
    It emits an on_click event and does not manage its own state or dialog.
    """
    icon_name = "image"
    if media_type == "video":
        icon_name = "video_library"
    elif media_type == "audio":
        icon_name = "audio_file"

    with me.content_button(on_click=on_click, type=button_type, key=key):
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=8, align_items="center"
            )
        ):
            me.icon(icon_name)
            if button_label:
                me.text(button_label)
