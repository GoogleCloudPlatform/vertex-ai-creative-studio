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

import re

import mesop as me

from components.header import header
from services.improver import PromptImprover


@me.stateclass
class PageState:
    """Local page state for the prompt improvement page."""

    temp_name: str = ""

    processing: bool = False
    processing_status: str = ""
    error_message: str = ""

    system_prompt_input: str = ""
    system_prompt_textarea_key: int = 0
    system_prompt_placeholder: str = ""

    prompt_input: str = ""
    prompt_textarea_key: int = 0
    prompt_placeholder: str = ""

    extracted_parameters: str = ""

    improvement_prompt_input: str = ""
    improvement_prompt_textarea_key: int = 0
    improvement_prompt_placeholder: str = ""
    improvement_prompt_response: str = ""

    improved_prompt_response: str = ""


def promptlandia_page_content(app_state: me.state):
    """Renders the main content of the prompt improvement page.

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
                header("Promptlandia", "try")
                me.text("Improve an existing prompt")
                me.box(style=me.Style(height=32))

                if state.error_message:
                    with me.box(
                        style=me.Style(
                            background=me.theme_var("error-container"),
                            color=me.theme_var("on-error-container"),
                            padding=me.Padding.all(16),
                            border_radius=8,
                            margin=me.Margin(bottom=16),
                        )
                    ):
                        me.text(state.error_message)

                # Existing prompt entry
                if not state.processing_status:
                    with me.box(
                        style=me.Style(
                            width="100%",
                            # padding=me.Padding().all(16),
                            # margin=me.Margin().all(20),
                        )
                    ):
                        me.text("Existing prompt", style=me.Style(font_weight="bold"))
                        me.box(style=me.Style(height=8))
                        with me.box(
                            style=me.Style(
                                display="grid",
                                flex_direction="row",
                                gap=5,
                                align_items="center",
                                width="100%",
                            )
                        ):
                            gemini_system_prompt_input()
                            gemini_prompt_input()

                        me.box(style=me.Style(height=16))
                        if state.extracted_parameters:
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_direction="row",
                                    gap=4,
                                    padding=me.Padding(left=16),
                                )
                            ):
                                me.text(
                                    "Detected parameters:",
                                    style=me.Style(
                                        color=me.theme_var("on-tertiary-container"),
                                    ),
                                )
                                me.text(
                                    f"{state.extracted_parameters}",
                                    style=me.Style(
                                        color=me.theme_var("on-secondary-container"),
                                    ),
                                )

                    me.box(style=me.Style(height=16))

                    me.text(
                        "What would you like to improve",
                        style=me.Style(font_weight="bold"),
                    )
                    me.box(style=me.Style(height=8))
                    gemini_improvement_prompt_input()

                    me.box(style=me.Style(height=16))

                    with me.box(
                        style=me.Style(
                            align_items="center",
                            display="flex",
                            flex_direction="row",
                            justify_content="center",
                        ),
                    ):
                        me.button("Clear", on_click=on_click_clear_prompt)
                        me.button(
                            "Improve prompt",
                            on_click=on_click_generate_content,
                            color="primary",
                            type="flat",
                        )

                else:
                    with me.box(
                        style=me.Style(display="flex", flex_direction="column")
                    ):
                        if state.processing:
                            me.text(
                                "Improving prompt", style=me.Style(font_weight="bold")
                            )
                            me.box(style=me.Style(height=8))
                            with me.box(
                                style=me.Style(display="flex", flex_direction="row", gap=5)
                            ):
                                me.progress_spinner(diameter=16)
                                me.text(state.processing_status)

                        else:
                            me.text("USER", style=me.Style(font_weight="bold"))
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
                                me.markdown(text=state.improved_prompt_response)

                            me.box(style=me.Style(height=8))

                            with me.box(
                                style=me.Style(
                                    align_items="center",
                                    display="flex",
                                    flex_direction="row",
                                    justify_content="center",
                                ),
                            ):
                                me.button("Clear", on_click=on_click_clear_prompt)
                                me.button(
                                    "Redo improvement",
                                    on_click=on_click_generate_content,
                                    type="stroked",
                                )


@me.component
def gemini_prompt_input():
    """Renders the Gemini prompt input text area."""
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

        # with me.box(
        #     style=me.Style(
        #         display="flex",
        #         flex_direction="column",
        #     )
        # ):
        #     with me.content_button(type="icon", on_click=on_click_clear_prompt):
        #         me.icon("clear")
        #     with me.content_button(type="icon", on_click=on_click_generate_content):
        #         me.icon("send")


def extract_double_braces(text):
    """
    Extracts all phrases enclosed in double curly braces from a string.

    Args:
      text: The input string.

    Returns:
      A list of strings containing the extracted phrases, or an empty list if none are found.
    """
    pattern = r"\{\{(.*?)\}"  # Non-greedy matching
    matches = re.findall(pattern, text)
    return matches

def on_blur_prompt(e: me.InputBlurEvent):
    """Handles the blur event for the prompt input.

    Args:
        e: The Mesop InputBlurEvent.
    """
    page_state = me.state(PageState)
    page_state.extracted_parameters = extract_double_braces(e.value)
    page_state.prompt_input = e.value


@me.component
def gemini_system_prompt_input():
    """Renders the Gemini system prompt input text area."""
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
                min_rows=4,
                placeholder="system prompt",
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
                on_blur=on_blur_system_prompt,
                key=str(page_state.system_prompt_textarea_key),
                value=page_state.system_prompt_placeholder,
            )
        # with me.content_button(type="icon"):
        #  me.icon("upload")
        # with me.content_button(type="icon"):
        #  me.icon("photo")

        # with me.box(
        #     style=me.Style(
        #         display="flex",
        #         flex_direction="column",
        #     )
        # ):
        #     with me.content_button(type="icon", on_click=on_click_clear_prompt):
        #         me.icon("clear")
        #     with me.content_button(type="icon", on_click=on_click_generate_content):
        #         me.icon("send")


def on_blur_system_prompt(e: me.InputBlurEvent):
    """Handles the blur event for the system prompt input.

    Args:
        e: The Mesop InputBlurEvent.
    """
    me.state(PageState).system_prompt_input = e.value


@me.component
def gemini_improvement_prompt_input():
    """Renders the Gemini improvement prompt input text area."""
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
                min_rows=4,
                # placeholder="system prompt",
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
                on_blur=on_blur_improvement_prompt,
                key=str(page_state.improvement_prompt_textarea_key),
                value=page_state.improvement_prompt_placeholder,
            )
        # with me.content_button(type="icon"):
        #  me.icon("upload")
        # with me.content_button(type="icon"):
        #  me.icon("photo")

        # with me.box(
        #     style=me.Style(
        #         display="flex",
        #         flex_direction="column",
        #     )
        # ):
        #     with me.content_button(type="icon", on_click=on_click_clear_prompt):
        #         me.icon("clear")
        #     with me.content_button(type="icon", on_click=on_click_generate_content):
        #         me.icon("send")


def on_blur_improvement_prompt(e: me.InputBlurEvent):
    """Handles the blur event for the improvement prompt input.

    Args:
        e: The Mesop InputBlurEvent.
    """
    me.state(PageState).improvement_prompt_input = e.value


BACKGROUND_COLOR = me.theme_var("on-secondary")


def on_click_generate_content(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handles the click event for the improve prompt button.

    This function is called when the user clicks the improve prompt button. It
    sends the user's prompt and improvement instructions to the generative AI
    model and displays the improved prompt.

    Args:
        e: The Mesop ClickEvent.
    """
    page_state = me.state(PageState)
    page_state.improved_prompt_response = ""
    page_state.error_message = ""
    yield
    page_state.processing = True
    yield
    page_state.processing_status = "Planning ..."
    yield

    try:
        prompt = page_state.prompt_input
        system_prompt = page_state.system_prompt_input
        prompt_improvement_instructions = page_state.improvement_prompt_input

        improver = PromptImprover()

        plan_object = improver.generate_plan(
            system_prompt=system_prompt,
            prompt=prompt,
            instructions=prompt_improvement_instructions,
        )
        print(f"plan:\n{plan_object.generated_plan}")
        yield

        page_state.processing_status = "Improving ..."
        result = improver.improve_prompt(plan=plan_object)
        print(f"improved prompt:\n{result.improved_prompt}")
        yield

        page_state.improved_prompt_response = result.improved_prompt
        page_state.processing_status = "improved"
    except Exception as e:
        page_state.error_message = f"An error occurred: {str(e)}"
        page_state.processing_status = ""
    finally:
        page_state.processing = False
        yield


def gemini_plan_and_improve(
    system_prompt: str = "",
    prompt: str = "",
    prompt_improvement_instructions: str = "",
) -> str:
    """Generates a plan and improves a prompt using the Gemini model.

    This function first generates a plan for improving the prompt and then uses
    that plan to generate an improved version of the prompt.

    Args:
        system_prompt: An optional system prompt to guide the model.
        prompt: The prompt to improve.
        prompt_improvement_instructions: Instructions for the improvement.

    Returns:
        The improved prompt as a string.
    """
    improver = PromptImprover()
    result = improver.run(
        system_prompt=system_prompt,
        prompt=prompt,
        instructions=prompt_improvement_instructions,
    )
    return result.improved_prompt


def on_click_clear_prompt(e: me.ClickEvent):
    """Handles the click event for the clear prompt button.

    This function is called when the user clicks the clear prompt button. It
    clears all the input fields and the response.

    Args:
        e: The Mesop ClickEvent.
    """
    state = me.state(PageState)

    state.prompt_input = ""
    state.prompt_placeholder = ""
    state.prompt_textarea_key += 1

    state.system_prompt_input = ""
    state.system_prompt_placeholder = ""
    state.system_prompt_textarea_key += 1

    state.improvement_prompt_input = ""
    state.improvement_prompt_placeholder = ""
    state.improvement_prompt_textarea_key += 1

    state.extracted_parameters = ""

    state.improved_prompt_response = ""

    state.processing = False
    state.processing_status = ""

    yield
