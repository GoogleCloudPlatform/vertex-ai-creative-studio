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

"""Main application file for the Promptlandia web application."""

import mesop as me

from state.state import AppState
from components.page_scaffold import page_scaffold
from pages.promptlandia import promptlandia_page_content
from pages.generate import prompt_page_content
from pages.settings import settings_page_content
from pages.playground import playground_page_content
from pages.checklist import checklist_page_content
from pages.video_checklist import video_page
from pages.trimmer import trimmer_page_content


def on_load(e: me.LoadEvent):  # pylint: disable=unused-argument
    """
    Handles the on-load event for all pages.

    This function is called when any page in the application is loaded. It sets
    the theme mode to "system", which will use the user's operating system's
    theme preference (light or dark).

    Args:
        e: The Mesop LoadEvent.
    """
    me.set_theme_mode("system")


@me.page(
    path="/",
    title="Promptlandia",
    on_load=on_load,
)
def promptlandia_page():
    """
    Renders the main prompt improvement page.

    This is the default page of the application and corresponds to the "/" route.
    It uses the `page_scaffold` component to provide a consistent layout and
    renders the `promptlandia_page_content` within it.
    """
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        promptlandia_page_content(state)


@me.page(
    path="/prompt",
    title="Promptlandia: Prompt explorer",
    on_load=on_load,
)
def prompt_page():
    """
    Renders the prompt explorer page.

    This page corresponds to the "/prompt" route and is used for exploring
    and generating content from prompts. It uses the `page_scaffold` component
    and renders the `prompt_page_content`.
    """
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        prompt_page_content(state)


@me.page(
    path="/settings",
    title="Promptlandia: Settings",
    on_load=on_load,
    security_policy=me.SecurityPolicy(
        dangerously_disable_trusted_types=True
    )
)
def settings_page():
    """
    Renders the settings page.

    This page corresponds to the "/settings" route and displays the application's
    settings. It uses the `page_scaffold` component and renders the
    `settings_page_content`.
    """
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        settings_page_content(state)


@me.page(
    path="/playground",
    title="Promptlandia: Playground",
    on_load=on_load,
)
def playground_page():
    """
    Renders the playground page.

    This page corresponds to the "/playground" route and provides a space for
    users to experiment with prompts and models. It uses the `page_scaffold`
    component and renders the `playground_page_content`.
    """
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        playground_page_content(state)


@me.page(
    path="/checklist",
    title="Promptlandia: Prompt Health Check",
    on_load=on_load,
)
def checklist_page():
    """
    Renders the prompt health checklist page.

    This page corresponds to the "/checklist" route and allows users to
    evaluate their prompts against a set of best practices. It uses the
    `page_scaffold` component and renders the `checklist_page_content`.
    """
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        checklist_page_content(state)


@me.page(
    path="/video_checklist",
    title="Promptlandia: Video Prompt Health Check",
    on_load=on_load,
)
def video_checklist_page():
    """
    Renders the video prompt health checklist page.

    This page corresponds to the "/video_checklist" route and allows users to
    evaluate their video prompts against a set of best practices. It uses the
f    `page_scaffold` component and renders the `video_checklist_page_content`.
    """
    with page_scaffold():  # pylint: disable=not-context-manager
        video_page()


@me.page(
    path="/trimmer",
    title="Promptlandia: Prompt Trimmer",
    on_load=on_load,
    security_policy=me.SecurityPolicy(
        dangerously_disable_trusted_types=True
    )
)
def trimmer_page():
    """
    Renders the prompt trimmer page.

    This page corresponds to the "/trimmer" route and allows users to
    trim their prompts by removing general best practices while keeping
    task-specific requirements.
    """
    with page_scaffold():  # pylint: disable=not-context-manager
        trimmer_page_content()