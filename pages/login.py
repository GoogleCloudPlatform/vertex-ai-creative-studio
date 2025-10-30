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

import json
import mesop as me
from state.state import AppState, set_authenticated, set_login_error
from config.default import Default

def login_form():
    """Login form component."""
    state = me.state(AppState)
    
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            align_items="center",
            justify_content="center",
            min_height="100vh",
            padding=me.Padding.all(20),
            background=me.theme_var("surface"),
        )
    ):
        with me.box(
            style=me.Style(
                max_width="400px",
                width="100%",
                padding=me.Padding.all(32),
                border=me.Border.all(
                    me.BorderSide(style="solid", width=1, color=me.theme_var("outline"))
                ),
                border_radius=12,
                background=me.theme_var("surface-container"),
            )
        ):
            # Logo/Title
            with me.box(
                style=me.Style(
                    text_align="center",
                    margin=me.Margin(bottom=24),
                )
            ):
                me.text("GenMedia Creative Studio", type="headline-4")
                me.text("Please enter the password to continue", type="body-1", 
                       style=me.Style(color=me.theme_var("on-surface-variant")))
            
            # Error message
            if state.login_error:
                with me.box(
                    style=me.Style(
                        background="#ffebee",
                        border=me.Border.all(
                            me.BorderSide(style="solid", width=1, color="#f44336")
                        ),
                        border_radius=4,
                        padding=me.Padding.all(12),
                        margin=me.Margin(bottom=16),
                    )
                ):
                    me.text(state.login_error, 
                           style=me.Style(color="#d32f2f"))
            
            # Password input
            with me.box(style=me.Style(margin=me.Margin(bottom=24))):
                me.input(
                    label="Password",
                    type="password",
                    on_input=on_password_input,
                    style=me.Style(width="100%"),
                )
            
            # Login button
            with me.box(style=me.Style(text_align="center")):
                me.button(
                    "Login",
                    on_click=on_login_click,
                    type="flat",
                    style=me.Style(
                        background=me.theme_var("primary"),
                        color=me.theme_var("on-primary"),
                        padding=me.Padding(top=12, bottom=12, left=24, right=24),
                        border_radius=6,
                        width="100%",
                    ),
                )

def on_password_input(e: me.InputEvent):
    """Handle password input."""
    state = me.state(AppState)
    # Store password temporarily (in real app, you might want to handle this more securely)
    if not hasattr(state, 'temp_password'):
        state.temp_password = ""
    state.temp_password = e.value
    yield

def on_login_click(e: me.ClickEvent):
    """Handle login button click."""
    from common.simple_auth import verify_password
    
    state = me.state(AppState)
    
    # Get password from state
    password = getattr(state, 'temp_password', '')
    
    if not password:
        set_login_error("Please enter a password")
        yield
        return
    
    # Verify password directly (since we're in the same process)
    try:
        if verify_password(password):
            # Login successful
            set_authenticated(True)
            # Clear temp password
            state.temp_password = ""
            # Navigate to home page
            me.navigate("/home")
            yield
        else:
            # Login failed
            set_login_error("Invalid password. Please try again.")
            yield
    
    except Exception as ex:
        set_login_error(f"Login failed: {str(ex)}")
        yield

@me.page(
    path="/login",
    title="Login - GenMedia Creative Studio",
)
def login_page():
    """Login page."""
    login_form()