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
import mesop as me

from state.state import AppState
from components.styles import (
    SIDENAV_MAX_WIDTH,
    SIDENAV_MIN_WIDTH,
    _FANCY_TEXT_GRADIENT,
    DEFAULT_MENU_STYLE,
)


page_json = [
    {"id": 0, "display": "Arena", "icon": "stadium", "route": "/"},
    {"id": 1, "display": "Leaderboard", "icon": "leaderboard", "route": "/leaderboard"},
    {"id": 2, "display": "History", "icon": "history", "route": "/history"},
    {
        "id": 10,
        "display": "Settings",
        "icon": "settings",
        "route": "/settings",
        "align": "bottom",
    },
]


def on_sidenav_menu_click(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Side navigation menu click handler"""
    state = me.state(AppState)
    state.sidenav_open = not state.sidenav_open


def navigate_to(e: me.ClickEvent):
    """navigate to a specific page"""
    s = me.state(AppState)
    idx = int(e.key)
    print(f"idx: {idx}")

    page = get_page_by_id(idx)
    if page is None:
        print(f"requested {idx}, but couldn't find page with that id.")
        return

    print(f"navigating to: {page}")
    s.current_page = page["route"]
    me.navigate(s.current_page)
    yield


def get_page_by_id(page_id):
    """Gets the page object with the given ID.

    Args:
      page_json: A list of page objects (dictionaries).
      page_id: The ID of the page to retrieve.

    Returns:
      The page object (dictionary) if found, or None if not found.
    """
    for page in page_json:
        if page["id"] == page_id:
            return page
    return None


@me.component
def sidenav(current_page: str):
    """Render side navigation"""
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
                    me.text("IMAGE ARENA", style=_FANCY_TEXT_GRADIENT)
            # spacer
            me.box(style=me.Style(height=16))
            # standard pages
            for idx, page in enumerate(page_json):
                if "align" not in page:  # ignore pages with alignment, handle elsewhere
                    menu_item(
                        idx, page["icon"], page["display"], not app_state.sidenav_open
                    )
            # settings & theme toggle
            with me.box(style=MENU_BOTTOM):
                theme_toggle_icon(
                    9,
                    "light_mode",
                    "Theme",
                    not app_state.sidenav_open,
                )
                menu_item(10, "settings", "Settings", not app_state.sidenav_open)


MENU_BOTTOM = me.Style(
    display="flex",
    flex_direction="column",
    position="absolute",
    bottom=8,
    align_content="left",
)


def menu_item(
    key: int,
    icon: str,
    text: str,
    minimized: bool = True,
    content_style: me.Style = DEFAULT_MENU_STYLE,
):
    """render menu item"""
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
