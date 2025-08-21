# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you mayn# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import typing

import mesop as me


@me.component
def header(
    title: str,
    icon: str,
    show_info_button: bool = False,
    on_info_click: typing.Callable[..., None] | None = None,
    current_status: str = None,
):
    """Header component."""
    with me.box(
        style=me.Style(
            display="flex",
            justify_content="space-between",
            align_items="center",
        ),
    ):
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=5,
                align_items="baseline",
            ),
        ):
            me.icon(icon=icon)
            me.text(
                title,
                type="headline-5",
                style=me.Style(font_family="Google Sans"),
            )

        if show_info_button and on_info_click:
            with me.content_button(
                type="icon",
                on_click=on_info_click,
                style=me.Style(margin=me.Margin(left="auto")),
            ), me.tooltip(message="About this page"):
                me.icon(icon="info_outline")

        if current_status and len(current_status) > 0:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    justify_content="flex-end",
                    align_items="top",
                )
            ):

                me.text(current_status)
