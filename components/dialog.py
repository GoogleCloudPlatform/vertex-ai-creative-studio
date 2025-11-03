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
"""Dialog mesop component"""

from typing import Optional

import mesop as me


@me.content_component
def dialog(is_open: bool, dialog_style: Optional[me.Style] = None, key: Optional[str] = None):
    """Render a dialog component.

    Args:
      is_open: Whether the dialog is visible or not.
      dialog_style: Optional style to apply to the main dialog box container,
                    allowing overrides for width, max_width, etc.
    """
    # NOTE: Do NOT use `if not is_open: return`. A content component must always
    # have a path that calls `me.slot()`. Visibility is handled by the `display`
    # style property on the outer box.

    # Define default style values in a dictionary for clarity.
    # Use theme variables to make the component theme-aware.
    # Add overflow_y to handle long content.
    defaults = {
        "background": me.theme_var("surface"),
        "border_radius": 12,
        "box_shadow": me.theme_var("shadow_elevation_2"),
        "display": "flex",
        "flex_direction": "column",
        "max_height": "90vh",
        "overflow_y": "auto",  # Added to handle content overflow
        "padding": me.Padding.all(24),
        "pointer_events": "auto",
        "width": 500,
        "max_width": "90vw",
    }

    # Manually create the final style, allowing `dialog_style` to override defaults.
    # This is necessary because me.Style objects are immutable and have no merge method.
    final_style = me.Style(
        background=dialog_style.background if dialog_style and dialog_style.background is not None else defaults["background"],
        border_radius=dialog_style.border_radius if dialog_style and dialog_style.border_radius is not None else defaults["border_radius"],
        box_shadow=dialog_style.box_shadow if dialog_style and dialog_style.box_shadow is not None else defaults["box_shadow"],
        display=dialog_style.display if dialog_style and dialog_style.display is not None else defaults["display"],
        flex_direction=dialog_style.flex_direction if dialog_style and dialog_style.flex_direction is not None else defaults["flex_direction"],
        max_height=dialog_style.max_height if dialog_style and dialog_style.max_height is not None else defaults["max_height"],
        overflow_y=dialog_style.overflow_y if dialog_style and dialog_style.overflow_y is not None else defaults["overflow_y"],
        padding=dialog_style.padding if dialog_style and dialog_style.padding is not None else defaults["padding"],
        pointer_events=dialog_style.pointer_events if dialog_style and dialog_style.pointer_events is not None else defaults["pointer_events"],
        width=dialog_style.width if dialog_style and dialog_style.width is not None else defaults["width"],
        max_width=dialog_style.max_width if dialog_style and dialog_style.max_width is not None else defaults["max_width"],
    )

    with me.box(
        key=key,
        style=me.Style(
            background="rgba(0,0,0,0.4)",
            display="block" if is_open else "none",
            height="100%",
            left=0,
            top=0,
            overflow_x="hidden",
            overflow_y="auto",
            position="fixed",
            width="100%",
            z_index=1000,
        )
    ):
        with me.box(
            style=me.Style(
                display="flex",
                align_items="center",
                justify_content="center",
                height="100%",
                width="100%",
                padding=me.Padding.all(20),
            )
        ):
            with me.box(style=final_style):
                me.slot()


@me.content_component
def dialog_actions():
    """Helper component for rendering action buttons so they are right aligned."""
    with me.box(
        style=me.Style(
            display="flex", justify_content="flex-end", margin=me.Margin(top=24), gap=8
        )
    ):
        me.slot()