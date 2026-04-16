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
"""
This module defines the side navigation component for the Promptlandia application.

It includes the navigation links, event handlers for clicks, and the logic for
rendering the side navigation in both expanded and minimized states.
"""
import mesop as me
from state.state import AppState
from components.styles import (
    SIDENAV_MAX_WIDTH,
    SIDENAV_MIN_WIDTH,
    _FANCY_TEXT_GRADIENT,
    DEFAULT_MENU_STYLE,
)


# primary page nav
page_json = [
    {"display": "Promptlandia", "icon": "try", "route": "/"},
    {"display": "Checklist", "icon": "fact_check", "route": "/checklist"},
    {"display": "Video Checklist", "icon": "movie", "route": "/video_checklist"},
    {"display": "Trimmer", "icon": "content_cut", "route": "/trimmer"},
    {"display": "Prompt", "icon": "question_answer", "route": "/prompt"},
    # {"display": "Playground", "icon": "auto_awesome", "route": "/playground"},
]

# bottom-aligned nav pages
page_json_bottom = [
    {
        "id": 10,
        "display": "Settings",
        "icon": "settings",
        "route": "/settings",
        "align": "bottom",
    },
]


def on_sidenav_menu_click(e: me.ClickEvent):  # pylint: disable=unused-argument
    """
    Handles the click event for the side navigation menu button.

    This function toggles the `sidenav_open` state in the application's state,
    which controls whether the side navigation is expanded or minimized.

    Args:
        e: The Mesop ClickEvent.
    """
    state = me.state(AppState)
    state.sidenav_open = not state.sidenav_open


def navigate_to(e: me.ClickEvent):
    """
    Navigates to the selected page.

    This function is called when a navigation item in the side navigation is
    clicked. It determines the target route based on the key of the clicked
    element and then navigates to that page.

    Args:
        e: The Mesop ClickEvent.
    """
    s = me.state(AppState)
    idx = int(e.key)
    print(f"idx: {idx}")

    if idx < len(page_json):
        page = page_json[idx]
    else:
        # Search page_json_bottom by ID
        page = None
        for item in page_json_bottom:
            if item["id"] == idx:
                page = item
                break  # Found the page, exit the loop

        if page is None:
            print(f"index {idx} is in neither main or bottom-aligned page navs")
            yield
            return

    # page = page_json[idx]
    print(f"navigating to: {page}")
    s.current_page = page["route"]
    me.navigate(s.current_page)
    yield


@me.component
def sidenav(current_page: str):
    """
    Renders the side navigation component.

    This component displays the main navigation links for the application. It can
    be in either an expanded or minimized state, which is controlled by the
    `sidenav_open` state.

    Args:
        current_page: The route of the currently active page.
    """
    app_state = me.state(AppState)
    # print(f"received current page: {current_page}")

    with me.sidenav(
        opened=True,
        style=me.Style(
            width=SIDENAV_MAX_WIDTH if app_state.sidenav_open else SIDENAV_MIN_WIDTH,
            background=me.theme_var("secondary-container"),
        ),
    ):
        with me.box(
            style=me.Style(
                margin=me.Margin(top=16, left=16, right=16, bottom=16),
                display="flex",
                flex_direction="column",
                gap=5,
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
                    me.text("Promptlandia", style=_FANCY_TEXT_GRADIENT)
            me.box(style=me.Style(height=16))

            # primary page nav
            for idx, page in enumerate(page_json):
                menu_item(
                    idx, page["icon"], page["display"], not app_state.sidenav_open
                )

            # bottom-aligned page nav
            # settings & theme toggle
            with me.box(style=MENU_BOTTOM):
                theme_toggle_icon(
                    9,
                    "light_mode",
                    "Theme",
                    not app_state.sidenav_open,
                )
                menu_item(10, "settings", "Settings", not app_state.sidenav_open)


def menu_item(
    key: int,
    icon: str,
    text: str,
    minimized: bool = True,
    content_style: me.Style = DEFAULT_MENU_STYLE,
):
    """
    Renders a single menu item in the side navigation.

    This function can render the menu item in either an expanded or minimized
    state. In the minimized state, it only shows an icon with a tooltip. In the
    expanded state, it shows both an icon and text.

    Args:
        key: The key to use for the menu item, used for navigation.
        icon: The name of the Material Icon to display.
        text: The text to display for the menu item.
        minimized: Whether the menu item should be rendered in its minimized state.
        content_style: The style to apply to the menu item.
    """
    if minimized:  # minimized
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
                on_click=navigate_to,
                style=content_style,
                type="icon",
            ):
                with me.tooltip(message=text):
                    me.icon(icon=icon)

    else:  # expanded
        with me.content_button(
            key=str(key),
            on_click=navigate_to,
            style=content_style,
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="center",
                ),
            ):
                me.icon(icon=icon)
                me.text(text)


def toggle_theme(e: me.ClickEvent):  # pylint: disable=unused-argument
    """
    Toggles the theme between light and dark mode.

    This function is called when the theme toggle button is clicked. It checks the
    current theme brightness and sets it to the opposite value.

    Args:
        e: The Mesop ClickEvent.
    """
    s = me.state(AppState)
    if me.theme_brightness() == "light":
        me.set_theme_mode("dark")
        s.theme_mode = "dark"
    else:
        me.set_theme_mode("light")
        s.theme_mode = "light"


def theme_toggle_icon(key: int, icon: str, text: str, min: bool = True):
    """
    Renders the theme toggle icon.

    This function can render the theme toggle icon in either an expanded or
    minimized state. In the minimized state, it only shows an icon with a
    tooltip. In the expanded state, it shows both an icon and text.

    Args:
        key: The key to use for the theme toggle icon.
        icon: The name of the Material Icon to display.
        text: The text to display for the theme toggle icon.
        min: Whether the theme toggle icon should be rendered in its minimized
            state.
    """
    # THEME_TOGGLE_STYLE = me.Style(position="absolute", bottom=50, align_content="left")
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
                # style=THEME_TOGGLE_STYLE,
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
            # style=THEME_TOGGLE_STYLE,
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
    display="flex",
    flex_direction="column",
    position="absolute",
    bottom=8,
    align_content="left",
)