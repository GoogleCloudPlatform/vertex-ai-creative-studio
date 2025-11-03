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
from state.veo_state import PageState

@me.component
def prompt_inputs(on_click_generate, on_click_rewrite, on_click_clear, on_blur_prompt, on_blur_negative_prompt):
    """A component for all VEO prompt inputs and actions."""
    state = me.state(PageState)

    # Main prompt input
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=me.theme_var("secondary-container"),
            display="flex",
            width="100%",
        )
    ):
        with me.box(style=me.Style(flex_grow=1)):
            me.native_textarea(
                autosize=True,
                min_rows=10,
                max_rows=13,
                placeholder="video creation instructions",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=me.theme_var("secondary-container"),
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(me.BorderSide(style="none")),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_prompt,
                key=str(state.veo_prompt_textarea_key),
                value=state.veo_prompt_input,
            )
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=15)):
            icon_style = me.Style(
                display="flex",
                flex_direction="column",
                gap=3,
                font_size=10,
                align_items="center",
            )
            with me.content_button(
                type="icon", on_click=on_click_generate, disabled=state.is_loading
            ):
                with me.box(style=icon_style):
                    me.icon("play_arrow")
                    me.text("Create")
            with me.content_button(
                type="icon",
                on_click=on_click_rewrite,
                disabled=state.is_loading,
            ):
                with me.box(style=icon_style):
                    me.icon("auto_awesome")
                    me.text("Rewriter")
            with me.content_button(
                type="icon", on_click=on_click_clear, disabled=state.is_loading
            ):
                with me.box(style=icon_style):
                    me.icon("clear")
                    me.text("Clear")

    me.box(style=me.Style(height="16px"))

    # Negative prompt input
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=me.theme_var("secondary-container"),
            display="flex",
            width="100%",
        )
    ):
        with me.box(style=me.Style(flex_grow=1)):
            me.native_textarea(
                placeholder="Enter concepts to avoid (negative prompt)",
                on_blur=on_blur_negative_prompt,
                value=state.negative_prompt,
                autosize=True,
                min_rows=1,
                max_rows=3,
                style=me.Style(
                    background="transparent",
                    outline="none",
                    width="100%",
                    border=me.Border.all(me.BorderSide(style="none")),
                    color=me.theme_var("foreground"),
                ),
            )
