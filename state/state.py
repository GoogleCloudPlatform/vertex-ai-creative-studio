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
from flask import request


@me.stateclass
class AppState:
    """Mesop Application State"""

    sidenav_open: bool = False
    theme_mode: str = "dark"
    user_email: str = "anonymous@google.com"
    session_id: str = ""
    current_page: str = ""

    def __init__(self):
        """Initializes the AppState, reading user info from the request context."""
        if "HTTP_X_GOOG_AUTHENTICATED_USER_EMAIL" in request.environ:
            user_email = request.environ["HTTP_X_GOOG_AUTHENTICATED_USER_EMAIL"]
            if user_email.startswith("accounts.google.com:"):
                user_email = user_email.split(":")[-1]
            self.user_email = user_email
            self.session_id = request.environ.get("MESOP_SESSION_ID", "")
        elif "MESOP_USER_EMAIL" in request.environ:
            self.user_email = request.environ["MESOP_USER_EMAIL"]
            self.session_id = request.environ["MESOP_SESSION_ID"]


def theme_toggle_button():
    """Theme toggle button"""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            align_items="center",
            justify_content="center",
            border=me.Border.all(
                me.BorderSide(
                    width=1,
                    style="solid",
                    color=me.theme_var("outline-variant"),
                )
            ),
            border_radius=9999,
            padding=me.Padding(top=8, right=16, bottom=8, left=16),
            gap=8,
            cursor="pointer",
        ),
        on_click=toggle_theme,
    ):
        me.text(me.state(AppState).theme_mode)
        me.icon(
            "dark_mode" if me.state(AppState).theme_mode == "light" else "light_mode"
        )


def toggle_theme(event: me.ClickEvent):
    """Toggles the theme mode between light and dark.

    Args:
        event: The Mesop click event.
    """
    app_state = me.state(AppState)
    if app_state.theme_mode == "light":
        app_state.theme_mode = "dark"
    else:
        app_state.theme_mode = "light"

    yield

def get_app_state() -> AppState:
    """-
    Returns the current application state.
    """
    return me.state(AppState)

def get_user_email() -> str:
    """
    Returns the current user's email.
    """
    return me.state(AppState).user_email

def get_session_id() -> str:
    """
    Returns the current session ID.
    """
    return me.state(AppState).session_id

def is_sidenav_open() -> bool:
    """
    Returns whether the sidenav is open.
    """
    return me.state(AppState).sidenav_open

def set_sidenav_open(is_open: bool):
    """
    Sets the sidenav open state.
    """
    me.state(AppState).sidenav_open = is_open

def toggle_sidenav():
    """
    Toggles the sidenav open state.
    """
    me.state(AppState).sidenav_open = not me.state(AppState).sidenav_open
    yield

def get_theme_mode() -> str:
    """
    Returns the current theme mode.
    """
    return me.state(AppState).theme_mode

def set_theme_mode(mode: str):
    """
    Sets the theme mode.
    """
    me.state(AppState).theme_mode = mode
    yield

def get_user_and_session_info() -> tuple[str, str]:
    """
    Returns the current user's email and session ID.
    """
    app_state = me.state(AppState)
    return app_state.user_email, app_state.session_id

def update_user_and_session_info(user_email: str, session_id: str):
    """
    Updates the user's email and session ID in the application state.
    """
    app_state = me.state(AppState)
    app_state.user_email = user_email
    app_state.session_id = session_id
    yield

def is_logged_in() -> bool:
    """
    Returns whether the user is logged in.
    """
    return me.state(AppState).user_email != "anonymous@google.com"

def get_current_user_id() -> str:
    """
    Returns the current user's ID.
    """
    return me.state(AppState).user_email

def get_current_session_id() -> str:
    """
    Returns the current session ID.
    """
    return me.state(AppState).session_id

def set_current_user_id(user_id: str):
    """
    Sets the current user's ID.
    """
    me.state(AppState).user_email = user_id
    yield

def set_current_session_id(session_id: str):
    """
    Sets the current session ID.
    """
    me.state(AppState).session_id = session_id
    yield

def reset_app_state():
    """
    Resets the application state.
    """
    app_state = me.state(AppState)
    app_state.sidenav_open = False
    app_state.theme_mode = "light"
    app_state.user_email = "anonymous@google.com"
    app_state.session_id = ""
    yield

def initialize_app_state():
    """
    Initializes the application state.
    """
    reset_app_state()
    yield

def get_state():
    """
    Returns the current application state.
    """
    return me.state(AppState)

def update_state(new_state: AppState):
    """
    Updates the application state.
    """
    app_state = me.state(AppState)
    app_state.sidenav_open = new_state.sidenav_open
    app_state.theme_mode = new_state.theme_mode
    app_state.user_email = new_state.user_email
    app_state.session_id = new_state.session_id
    yield