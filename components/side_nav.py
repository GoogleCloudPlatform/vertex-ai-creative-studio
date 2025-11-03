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

from typing import Optional

import mesop as me

from config.default import get_welcome_page_config, Default
from components.styles import (
    _FANCY_TEXT_GRADIENT,
    DEFAULT_MENU_STYLE,
    SIDENAV_MAX_WIDTH,
    SIDENAV_MIN_WIDTH,
)
from components.svg_icon.svg_icon import svg_icon
from state.state import AppState

cfg = Default()


def on_sidenav_menu_click(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Side navigation menu click handler"""
    state = me.state(AppState)
    state.sidenav_open = not state.sidenav_open


def on_click_title(e: me.ClickEvent):
    """Navigate to the welcome page."""
    me.navigate(url="/welcome")
    yield


def navigate_to(e: me.ClickEvent):
    """navigate to a specific page"""
    s = me.state(AppState)
    route_to_navigate = e.key  # The key of the content_button is the route
    if route_to_navigate:
        print(f"Navigating to: {route_to_navigate}")
        s.current_page = route_to_navigate
        me.navigate(route_to_navigate)
    else:
        print("Warning: handle_menu_navigation called with no route in e.key")
    yield


@me.component
def sidenav(current_page: Optional[str]):
    """Render side navigation"""
    app_state = me.state(AppState)

    WELCOME_PAGE = get_welcome_page_config()
    # Partition the list based on the 'align' key
    top_nav_items = [p for p in WELCOME_PAGE if p.get("route") and p.get("align") != "bottom"]
    bottom_nav_items = [p for p in WELCOME_PAGE if p.get("route") and p.get("align") == "bottom"]

    with me.sidenav(
        opened=True,
        style=me.Style(
            width=SIDENAV_MAX_WIDTH if app_state.sidenav_open else SIDENAV_MIN_WIDTH,
            background=me.theme_var("secondary-container"),
            transition="width 0.3s ease-in-out",
        ),
    ):
        with me.box(
            style=me.Style(
                margin=me.Margin(top=16, left=16, right=16, bottom=16),
                display="flex",
                flex_direction="column",
                gap=5,
                height="calc(100% - 32px)", # Adjust height for margin
            ),
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="center",
                ),
            ):
                with me.content_button(
                    type="icon",
                    on_click=on_sidenav_menu_click,
                ):
                    with me.box():
                        with me.tooltip(message="Expand menu"):
                            me.icon(icon="menu")
                if app_state.sidenav_open:
                    with me.box(on_click=on_click_title, style=me.Style(cursor="pointer")):
                        me.text("GENMEDIA STUDIO", style=_FANCY_TEXT_GRADIENT)
            
            me.box(style=me.Style(height=16)) # spacer

            # Render top navigation items
            for page in top_nav_items:
                item_id = f"{page.get('id', '')}_{page.get('display').lower().replace(' ', '_')}"
                menu_item(
                    item_id=item_id,
                    icon=page.get("icon"),
                    text=page.get("display"),
                    route=page.get("route"),
                    minimized=not app_state.sidenav_open,
                )

            # Bottom section
            with me.box(style=MENU_BOTTOM):
                theme_toggle_icon(
                    9,
                    "light_mode",
                    "Theme",
                    not app_state.sidenav_open,
                )
                # Render bottom navigation items
                for page in bottom_nav_items:
                    item_id = f"{page.get('id', '')}_{page.get('display').lower().replace(' ', '_')}"
                    menu_item(
                        item_id=item_id,
                        icon=page.get("icon"),
                        text=page.get("display"),
                        route=page.get("route"),
                        minimized=not app_state.sidenav_open,
                    )


def menu_item(
    item_id: str,
    icon: str,
    text: str,
    route: Optional[str],
    minimized: bool = True,
    content_style: me.Style = DEFAULT_MENU_STYLE,
):
    """render menu item"""

    is_clickable = bool(route)
    button_key = route if is_clickable else f"item_{item_id}"

    # List of custom icons that should use the svg_icon component
    custom_icons = ["spark", "style", "scene"]

    def render_icon(icon_name: str):
        if icon_name in custom_icons:
            with me.box(style=me.Style(width=24, height=24)):
                svg_icon(icon_name=icon_name)
        else:
            me.icon(icon=icon_name)

    if minimized:  # minimized
        with me.tooltip(message=text):
            with me.content_button(
                key=button_key,
                on_click=navigate_to if is_clickable else None,
                style=content_style,
                type="icon",
                disabled=not is_clickable,
            ):
                render_icon(icon)

    else:  # expanded
        with me.content_button(
            key=button_key,
            on_click=navigate_to,
            style=content_style,
            disabled=not is_clickable,
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="center",
                ),
            ):
                render_icon(icon)
                me.text(text, style=me.Style(text_align="left"))


def toggle_theme(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Toggle theme event"""
    s = me.state(AppState)
    if me.theme_brightness() == "light":
        me.set_theme_mode("dark")
        s.theme_mode = "dark"
    else:
        me.set_theme_mode("light")
        s.theme_mode = "light"


def theme_toggle_icon(key: int, icon: str, text: str, min: bool = True):
    """Theme toggle icon"""
    if min:  # minimized
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=5,
                align_items="center",
            ),
        ):
            with me.content_button(
                key=str(key),
                on_click=toggle_theme,
                type="icon",
            ):
                with me.tooltip(message=text):
                    me.icon(
                        "light_mode" if me.theme_brightness() == "dark" else "dark_mode"
                    )

    else:  # expanded
        with me.content_button(
            key=str(key),
            on_click=toggle_theme,
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="center",
                ),
            ):
                me.icon(
                    "light_mode" if me.theme_brightness() == "dark" else "dark_mode"
                )
                me.text(
                    "Light mode" if me.theme_brightness() == "dark" else "Dark mode"
                )


MENU_BOTTOM = me.Style(
    margin=me.Margin(top="auto"), # Pushes the container to the bottom
    padding=me.Padding(bottom=12),
)