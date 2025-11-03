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

from typing import Callable

import mesop as me


@me.component
def stepper(
    steps: list[str],
    current_step: int,
    max_completed_step: int,
    on_change: Callable[[int], None],
):
    """A custom stepper component styled to look like Angular Material."""
    with me.box(style=me.Style(display="flex", flex_direction="row", align_items="center")):
        for i, step_label in enumerate(steps):
            step_number = i + 1
            is_active = step_number == current_step
            is_completed = step_number <= max_completed_step

            def on_click_step(e: me.ClickEvent, i=i):
                on_change(i)

            with me.box(
                on_click=on_click_step if is_completed else None,
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    align_items="center",
                    cursor="pointer" if is_completed else "default",
                    padding=me.Padding.all(8),
                ),
            ):
                with me.box(
                    style=me.Style(
                        width=24,
                        height=24,
                        border_radius="50%",
                        background=(
                            me.theme_var("primary")
                            if is_active or is_completed
                            else me.theme_var("outline")
                        ),
                        color=me.theme_var("on-primary")
                        if is_active or is_completed
                        else me.theme_var("on-primary-container"),
                        display="flex",
                        justify_content="center",
                        align_items="center",
                    )
                ):
                    me.text(str(step_number), style=me.Style(font_size=12, font_weight="bold"))
                me.text(
                    step_label,
                    style=me.Style(
                        margin=me.Margin(left=8),
                        font_weight="bold" if is_active else "normal",
                        color=(
                            me.theme_var("primary")
                            if is_active
                            else me.theme_var("on-surface")
                        ),
                    ),
                )

            if i < len(steps) - 1:
                with me.box(
                    style=me.Style(
                        flex_grow=1,
                        height=1,
                        background=me.theme_var("outline"),
                        margin=me.Margin.symmetric(horizontal=8),
                    ),
                ):
                    pass
