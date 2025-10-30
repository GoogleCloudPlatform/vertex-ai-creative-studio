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

from components.svg_icon.svg_icon import svg_icon


@me.component
def header(
    title: str,
    icon: str,
    show_info_button: bool = False,
    on_info_click: typing.Callable[..., None] | None = None,
    current_status: str = None,
    show_logout_button: bool = False,
):
    """Render header component."""
    # List of custom icons that should use the svg_icon component
    custom_icons = ["spark", "style", "scene", "banana"]

    def render_icon(icon_name: str) -> None:
        if icon_name in custom_icons:
            with me.box(style=me.Style(width=24, height=24)):
                svg_icon(icon_name=icon_name)
        else:
            me.icon(icon=icon_name)

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
            render_icon(icon)
            me.text(
                title,
                type="headline-5",
                style=me.Style(font_family="Google Sans"),
            )

        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=8,
                align_items="center",
                margin=me.Margin(left="auto"),
            )
        ):
            if show_info_button and on_info_click:
                with (
                    me.content_button(
                        type="icon",
                        on_click=on_info_click,
                    ),
                    me.tooltip(message="About this page"),
                ):
                    me.icon(icon="info_outline")
            
            if show_logout_button:
                with (
                    me.content_button(
                        type="icon",
                        on_click=on_logout_click,
                    ),
                    me.tooltip(message="Logout"),
                ):
                    me.icon(icon="logout")

def on_logout_click(e: me.ClickEvent):
    """Handle logout button click."""
    from state.state import logout_user
    from config.default import Default
    
    cfg = Default()
    if cfg.SIMPLE_AUTH_ENABLED:
        logout_user()
        me.navigate("/login")
        yield
