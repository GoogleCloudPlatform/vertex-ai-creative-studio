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

"""This module defines the prompt explorer page of the application.

It includes the UI components for the prompt explorer page, as well as the logic
for handling user input, interacting with the generative AI model, and
displaying the results.
"""

import mesop as me
from google.genai.types import GenerateContentConfig

from components.header import header
from config.default import Default
from services.llm_client import LLMClient


@me.stateclass
class PageState:
    """Local page state for the prompt explorer page."""

    temp_name: str = ""

    processing: bool = False

    prompt_input: str = ""
    prompt_textarea_key: int = 0
    prompt_placeholder: str = ""
    prompt_response: str = ""


def prompt_page_content(app_state: me.state):
    """Renders the main content of the prompt explorer page.

    Args:
        app_state: The global application state.
    """

    state = me.state(PageState)

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
                header("Prompt", "question_answer")

                # me.text(f"Hello, {app_state.name}!")
                me.box(style=me.Style(height=16))
                with me.box(
                    style=me.Style(
                        display="grid",
                        flex_direction="row",
                        gap=5,
                        align_items="center",
                        width="100%",
                    )
                ):
                    gemini_prompt_input()

                me.box(style=me.Style(height=16))

                if state.processing:
                    with me.box(
                        style=me.Style(
                            display="grid",
                            justify_content="center",
                            justify_items="center",
                        )
                    ):
                        me.progress_spinner()
                elif state.prompt_response:
                    me.text("Response", style=me.Style(font_weight="bold"))
                    me.box(style=me.Style(height=8))
                    with me.box(
                        style=me.Style(
                            display="grid",
                            flex_direction="row",
                            gap=5,
                            align_items="center",
                            width="100%",
                            background=BACKGROUND_COLOR,
                            border_radius=16,
                            padding=me.Padding.all(8),
                        )
                    ):
                        me.markdown(text=state.prompt_response)


@me.component
def gemini_prompt_input():
    """Renders the Gemini prompt input text area and buttons."""
    page_state = me.state(PageState)
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=BACKGROUND_COLOR,
            display="flex",
            width="100%",
        )
    ):
        with me.box(
            style=me.Style(
                flex_grow=1,
            )
        ):
            me.native_textarea(
                autosize=True,
                min_rows=10,
                placeholder="prompt",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=BACKGROUND_COLOR,
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                ),
                on_blur=on_blur_prompt,
                key=str(page_state.prompt_textarea_key),
                value=page_state.prompt_placeholder,
            )
        # with me.content_button(type="icon"):
        #  me.icon("upload")
        # with me.content_button(type="icon"):
        #  me.icon("photo")
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
            )
        ):
            with me.content_button(type="icon", on_click=on_click_clear_prompt):
                me.icon("clear")
            with me.content_button(type="icon", on_click=on_click_generate_content):
                me.icon("send")


def on_blur_prompt(e: me.InputBlurEvent):
    """Handles the blur event for the prompt input.

    Args:
        e: The Mesop InputBlurEvent.
    """
    me.state(PageState).prompt_input = e.value


BACKGROUND_COLOR = me.theme_var("on-secondary")


def on_click_generate_content(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handles the click event for the generate content button.

    This function is called when the user clicks the generate content button. It
    sends the user's prompt to the generative AI model and displays the
    response.

    Args:
        e: The Mesop ClickEvent.
    """
    page_state = me.state(PageState)
    page_state.prompt_response = ""
    page_state.processing = True
    yield
    print(f"using prompt: {page_state.prompt_input}")
    
    try:
        client = LLMClient()
        config = Default()
        response = client.generate_content(
            model=config.MODEL_ID,
            contents=page_state.prompt_input,
            config=GenerateContentConfig(response_modalities=["TEXT"]),
        )
        page_state.prompt_response = response.text
    except Exception as ex:
        page_state.prompt_response = f"Error: {ex}"
        
    page_state.processing = False
    yield


def on_click_clear_prompt(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handles the click event for the clear prompt button.

    This function is called when the user clicks the clear prompt button. It
    clears the prompt input and the response.

    Args:
        e: The Mesop ClickEvent.
    """
    state = me.state(PageState)
    state.prompt_input = ""
    state.prompt_placeholder = ""
    state.prompt_textarea_key += 1
    # state.music_upload_uri = ""
    state.processing = False