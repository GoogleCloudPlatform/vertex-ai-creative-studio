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

from components.side_nav import sidenav
from components.styles import (
    SIDENAV_MAX_WIDTH,
    SIDENAV_MIN_WIDTH,
)

@me.content_component
def page_scaffold():
    """page scaffold component"""

    app_state = me.state(AppState)

    sidenav("")

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
            margin=me.Margin(
                left=SIDENAV_MAX_WIDTH if app_state.sidenav_open else SIDENAV_MIN_WIDTH,
            ),
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
            me.slot()


@me.content_component
def page_frame():
    """Page Frame"""
    with me.box(style=MAIN_COLUMN_STYLE):
        with me.box(style=PAGE_BACKGROUND_STYLE):
            with me.box(style=PAGE_BACKGROUND_PADDING_STYLE):
                me.slot()


MAIN_COLUMN_STYLE = me.Style(
    display="flex",
    flex_direction="column",
    height="100%",
)

PAGE_BACKGROUND_STYLE = me.Style(
    background=me.theme_var("background"),
    height="100%",
    overflow_y="scroll",
    margin=me.Margin(bottom=20),
)

PAGE_BACKGROUND_PADDING_STYLE = me.Style(
    background=me.theme_var("background"),
    padding=me.Padding(top=24, left=24, right=24, bottom=24),
    display="flex",
    flex_direction="column",
)
