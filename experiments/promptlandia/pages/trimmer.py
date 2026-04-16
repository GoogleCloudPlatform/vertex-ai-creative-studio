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

"""This module defines the prompt trimmer page."""

from typing import Callable, Optional
import mesop as me
from state.state import AppState
from services.trimmer import PromptTrimmer
from components.styles import PAGE_BACKGROUND_PADDING_STYLE
from components.header import header


def on_input_blur(e: me.InputBlurEvent):
    """Updates the trimmer input state on blur."""
    state = me.state(AppState)
    state.trimmer_input = e.value


def on_click_clear(e: me.ClickEvent):
    """Clears all trimmer state."""
    state = me.state(AppState)
    state.trimmer_input = ""
    state.trimmer_output = ""
    state.trimmer_analysis = ""
    state.trimmer_duration = 0.0


def on_click_trim(e: me.ClickEvent):
    """Handles the trim button click, executing the two-step trim process."""
    state = me.state(AppState)
    state.trimmer_loading = True
    state.trimmer_output = ""
    state.trimmer_analysis = ""
    state.trimmer_duration = 0.0
    yield
    
    try:
        trimmer = PromptTrimmer()
        result = trimmer.trim_prompt(state.trimmer_input)
        state.trimmer_output = result.trimmed_prompt
        state.trimmer_analysis = result.analysis_xml
        state.trimmer_duration = result.duration_seconds
    except Exception as ex:
        state.trimmer_output = f"Error during trimming: {ex}"
    finally:
        state.trimmer_loading = False
    yield


METADATA_STYLE = me.Style(color=me.theme_var("on-surface-variant"), font_size=12)
BACKGROUND_COLOR = me.theme_var("on-secondary")


@me.component
def styled_textarea(
    label: str,
    value: str,
    on_blur: Optional[Callable[[me.InputBlurEvent], None]] = None,
    readonly: bool = False,
    key: Optional[str] = None,
    min_rows: int = 10,
    max_rows: int = 30,
):
    """Renders a styled textarea component similar to promptlandia page."""
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=BACKGROUND_COLOR,
            display="flex",
            width="100%",
        )
    ):
        with me.box(style=me.Style(flex_grow=1)):
            me.native_textarea(
                autosize=True,
                min_rows=min_rows,
                max_rows=max_rows,
                placeholder=label,
                value=value,
                readonly=readonly,
                on_blur=on_blur,
                key=key,
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=BACKGROUND_COLOR,
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(me.BorderSide(style="none")),
                    color=me.theme_var("foreground"),
                ),
            )

def trimmer_page_content():
    """Renders the content for the trimmer page."""
    state = me.state(AppState)
    with me.box(style=PAGE_BACKGROUND_PADDING_STYLE):
        header("Prompt Trimmer", "content_cut")
        me.text(
            "Remove general best practices while keeping task-specific requirements."
        )

        # Main content container (Flex Row)
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=20,
                margin=me.Margin(top=20, bottom=20),
                width="100%",
            )
        ):
            # --- Left Column: Input ---
            # If output exists, take 50% width. Otherwise take 100%.
            input_width = "50%" if state.trimmer_output else "100%"
            with me.box(
                style=me.Style(
                    flex_basis=input_width, flex_grow=1, display="flex", flex_direction="column"
                )
            ):
                me.text("Original Prompt", type="headline-5", style=me.Style(margin=me.Margin.all(0)))
                me.box(style=me.Style(height=10))

                styled_textarea(
                    label="Enter your prompt here",
                    value=state.trimmer_input,
                    on_blur=on_input_blur,
                    key=f"trimmer_input_{state.trimmer_loading}", # Force re-render on loading state change if needed
                )
                # Input character count
                if state.trimmer_input:
                    me.text(
                        f"Character count: {len(state.trimmer_input)}",
                        style=METADATA_STYLE,
                    )

                # Action Buttons Row
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=10,
                        margin=me.Margin(top=10),
                        align_items="center",
                    )
                ):
                    me.button(
                        label="Trim Prompt",
                        on_click=on_click_trim,
                        type="flat",
                        disabled=state.trimmer_loading or not state.trimmer_input,
                    )
                    me.button(
                        label="Clear",
                        on_click=on_click_clear,
                        type="stroked",
                        disabled=state.trimmer_loading,
                    )

                # Loading Indicator
                if state.trimmer_loading:
                    with me.box(
                        style=me.Style(
                            margin=me.Margin(top=20),
                            display="flex",
                            flex_direction="row",
                            gap=10,
                            align_items="center",
                        )
                    ):
                        me.progress_spinner(diameter=30, stroke_width=3)
                        me.text(
                            "Trimming prompt... this may take a moment (two-step process)."
                        )

            # --- Right Column: Output (Conditional) ---
            if state.trimmer_output:
                with me.box(
                    style=me.Style(
                        flex_basis="50%",
                        flex_grow=1,
                        display="flex",
                        flex_direction="column",
                    )
                ):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            justify_content="space-between",
                            align_items="baseline",
                            margin=me.Margin(bottom=10) # Align with input box top
                        )
                    ):
                        me.text("Trimmed Prompt", type="headline-5", style=me.Style(margin=me.Margin.all(0)))
                        if state.trimmer_duration > 0:
                            me.text(
                                f"Generated in {state.trimmer_duration:.2f}s",
                                style=METADATA_STYLE,
                            )

                    styled_textarea(
                        label="Result",
                        value=state.trimmer_output,
                        readonly=True,
                        key="trimmer_output",
                    )
                    # Output character count
                    me.text(
                        f"Character count: {len(state.trimmer_output)}",
                        style=METADATA_STYLE,
                    )

        # --- Bottom Row: Analysis ---
        if state.trimmer_analysis:
            with me.box(style=me.Style(margin=me.Margin(top=20))):
                with me.expansion_panel(title="View Analysis (Deconstruction)"):
                    # Render analysis as markdown so the XML block is formatted
                    me.markdown(f"```xml\n{state.trimmer_analysis}\n```")
