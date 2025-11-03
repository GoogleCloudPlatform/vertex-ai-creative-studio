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
"""Welcome page"""

from typing import Optional

import mesop as me


def go_to_page(e: me.ClickEvent):
    """go to  page"""
    me.navigate(e.key)


@me.component
def media_tile(label: str, icon: str, route: str | None, icon_family: str | None = None, mode: str | None = None):
    """Media component"""

    is_clickable = bool(route)

    box_style = me.Style(
        display="flex",
        flex_direction="row",
        gap=5,
        align_items="center",
        border=me.Border().all(
            me.BorderSide(style="solid", color=me.theme_var("tertiary-fixed-variant"))
        ),
        border_radius=12,
        height=160,
        width=160,
        justify_content="center",
        background=me.theme_var("secondary-container"),
        cursor="pointer",
    )

    if is_clickable:
        box_style.cursor = "pointer"
    else:
        # Optionally, style non-clickable items differently
        box_style.opacity = 0.6  # Example: make it look disabled
        box_style.cursor = "default"
    with me.box(
        style=box_style,
        key=route if is_clickable else f"tile_{label}_{icon}",
        on_click=go_to_page if is_clickable else None,
    ):
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                align_items="center",
                font_size="18px",
                gap=5,
            ),
        ):
            icon_style = me.Style(
                font_size="38pt",
                width="50px",
                height="60px",
                color=me.theme_var("on-surface"),
            )
            if icon_family:
                print(f"changing icon family for {label} to: {icon_family}")
                icon_style.font_family = icon_family
            me.icon(
                icon,
                style=icon_style,
            )
            me.text(label, style=me.Style(font_weight="medium", text_align="center"))

            with me.box():
                me.text(mode)
