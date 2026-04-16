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

"""This module defines the global application state for the Promptlandia application.

It includes the `AppState` class, which is a Mesop state class that holds the
global state of the application. This includes the state of the side
navigation, the current page, and the theme mode.
"""

import mesop as me


@me.stateclass
class AppState:
    """Global application state.

    This class holds the global state of the application, which is shared across
    all pages.

    Attributes:
        sidenav_open: Whether the side navigation is open or closed.
        name: The name of the user.
        current_page: The route of the currently active page.
        theme_mode: The current theme mode (e.g., "light" or "dark").
        trimmer_input: The user's input prompt for the trimmer page.
        trimmer_output: The final trimmed prompt.
        trimmer_analysis: The intermediate analysis from the deconstructor.
        trimmer_loading: Whether the trimmer process is currently running.
        trimmer_duration: The time taken (in seconds) for the last trim operation.
    """

    sidenav_open: bool = False

    name: str = "World"
    current_page: str = "/"
    theme_mode: str = "light"

    # Trimmer Page State
    trimmer_input: str = ""
    trimmer_output: str = ""
    trimmer_analysis: str = ""
    trimmer_loading: bool = False
    trimmer_duration: float = 0.0
