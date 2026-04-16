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

"""This module defines the settings page of the application.

It displays the underlying prompts that the application itself uses for the
improvement and evaluation tasks, providing transparency into its own workings.
"""

import html

import mesop as me

from components.header import header
from config.default import Default
from models.prompts import (
    PROMPT_IMPROVEMENT_INSTRUCTIONS,
    PROMPT_IMPROVEMENT_PLANNING_INSTRUCTIONS,
    PROMPT_HEALTH_CHECKLIST,
    VIDEO_PROMPT_HEALTH_CHECKLIST,
    TRIMMER_DECONSTRUCTOR,
    TRIMMER_REWRITER,
)


@me.stateclass
class PageState:
    """Local page state for the settings page."""


def settings_page_content(app_state: me.state):
    """Renders the main content of the settings page.

    Args:
        app_state: The global application state.
    """

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
                header("Settings", "settings")

                me.text("Settings for Promptlandia")
                me.box(style=me.Style(height=32))
                
                with me.box():
                    me.text(
                        "Promptlandia settings",
                        style=me.Style(font_weight="bold"),
                    )
                    me.box(style=me.Style(height=8))
                    me.text(f"Model: {Default.MODEL_ID}")
                    me.text(f"Location: {Default.LOCATION}")

                me.box(style=me.Style(height=32))

                with me.expansion_panel(title="Prompt Improvement Instructions"):
                    with me.box(style=PROMPT_BOX_STYLE):
                        me.markdown(text=html.escape(PROMPT_IMPROVEMENT_INSTRUCTIONS))

                me.box(style=me.Style(height=16))

                with me.expansion_panel(title="Prompt Planning Instructions"):
                    with me.box(style=PROMPT_BOX_STYLE):
                        me.markdown(
                            text=html.escape(PROMPT_IMPROVEMENT_PLANNING_INSTRUCTIONS)
                        )

                me.box(style=me.Style(height=16))

                with me.expansion_panel(title="Prompt Health Checklist"):
                    with me.box(style=PROMPT_BOX_STYLE):
                        me.markdown(text=html.escape(PROMPT_HEALTH_CHECKLIST))

                me.box(style=me.Style(height=16))

                with me.expansion_panel(title="Video Prompt Health Checklist"):
                    with me.box(style=PROMPT_BOX_STYLE):
                        me.markdown(text=html.escape(VIDEO_PROMPT_HEALTH_CHECKLIST))

                me.box(style=me.Style(height=16))

                with me.expansion_panel(title="Trimmer Deconstructor Prompt"):
                    with me.box(style=PROMPT_BOX_STYLE):
                        me.markdown(text=html.escape(TRIMMER_DECONSTRUCTOR))

                me.box(style=me.Style(height=16))

                with me.expansion_panel(title="Trimmer Rewriter Prompt"):
                    with me.box(style=PROMPT_BOX_STYLE):
                        me.markdown(text=html.escape(TRIMMER_REWRITER))


PROMPT_BOX_STYLE = me.Style(
    display="grid",
    flex_direction="row",
    gap=5,
    align_items="center",
    width="100%",
    background=me.theme_var("on-secondary"),
    border_radius=16,
    padding=me.Padding.all(8),
)