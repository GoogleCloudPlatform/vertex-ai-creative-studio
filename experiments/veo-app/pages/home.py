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
"""Welcome page"""
import mesop as me

from components.header import header


def go_to_page(e: me.ClickEvent):
    """go to  page"""
    me.navigate(e.key)


def home_page_content(app_state: me.state):  # pylint: disable=unused-argument
    """Home Page"""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
        ),
    ):
        with me.box(
            style=me.Style(
                background=me.theme_var("background"),
                height="100%",
                overflow_y="scroll",
                margin=me.Margin(bottom=20),
            )
        ):
            with me.box(
                style=me.Style(
                    background=me.theme_var("background"),
                    padding=me.Padding(top=24, left=24, right=24, bottom=24),
                    display="flex",
                    flex_direction="column",
                )
            ):
                header("Welcome", "home")

                me.text(
                    "Welcome to the Veo module, a component of Vertex AI GenMedia Creative Studio"
                )

                me.box(style=me.Style(height=16))

                with me.box(
                    style=me.Style(
                        align_items="center",
                        display="flex",
                        flex_direction="row",
                        align_content="center",
                        justify_content="center",
                        gap=15,
                    ),
                ):
                    media_tile("Veo 2", "movie", "/veo")
                    media_tile("Motion Portraits", "portrait", "/motion_portraits")
                    media_tile("Library", "perm_media", "/library")
                    media_tile("Settings", "settings", "/config")


@me.component
def media_tile(label: str, icon: str, route: str):
    """Media component"""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            gap=5,
            align_items="center",
            border=me.Border().all(me.BorderSide(style="solid", color=me.theme_var("tertiary-fixed-variant"))),
            border_radius=12,
            height=200,
            width=200,
            justify_content="center",
            background=me.theme_var("secondary-container"),
            cursor="pointer"
        ),
        on_click=go_to_page,
        key=route,
    ):
        with me.content_button(
            #on_click=go_to_page,
            #key=route,
            style=me.Style(font_size="18px"),
        ):
            me.icon(
                icon, style=me.Style(font_size="48pt", width="100px", height="60px")
            )
            me.text(label)
