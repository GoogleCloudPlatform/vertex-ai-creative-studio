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
""" Lyria 2 mesop ui page """
import time

import mesop as me

from common.metadata import add_music_metadata
from components.dialog import dialog, dialog_actions
from components.header import header
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from config.default import Default
from config.rewriters import MUSIC_REWRITER
from models.gemini import rewriter
from models.lyria import generate_music_with_lyria

cfg = Default()

@me.stateclass
class PageState:
    """Local Page State"""

    is_loading: bool = False

    music_prompt_input: str = ""
    music_prompt_placeholder: str = ""
    music_prompt_textarea_key: int = 0
    music_upload_uri: str = ""
    
    timing: str

    show_error_dialog: bool = False
    error_message: str = ""


def lyria_content(app_state: me.state):
    """Lyria Mesop Page"""

    pagestate = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Lyria", "music_note")

            with me.box(style=_BOX_STYLE):
                me.text(
                    "Prompt for music generation",
                    style=me.Style(font_weight=500),
                )
                me.box(style=me.Style(height=16))
                subtle_lyria_input()
                #me.box(style=me.Style(height=24))

            me.box(style=me.Style(height=24))

            if pagestate.is_loading:
                with me.box(
                    style=me.Style(
                        display="grid",
                        justify_content="center",
                        justify_items="center",
                    )
                ):
                    me.progress_spinner()
            if pagestate.music_upload_uri:
                with me.box(
                    style=me.Style(
                        display="grid",
                        justify_content="center",
                        justify_items="center",
                    )
                ):
                    me.audio(src=pagestate.music_upload_uri)

            with dialog(is_open=pagestate.show_error_dialog):  # pylint: disable=not-context-manager
                # Content within the dialog box
                me.text(
                    "Generation Error",
                    type="headline-6",
                    style=me.Style(color=me.theme_var("error")),
                )
                me.text(pagestate.error_message, style=me.Style(margin=me.Margin(top=16)))
                # Use the dialog_actions component for the button
                with dialog_actions():  # pylint: disable=not-context-manager
                    me.button("Close", on_click=on_close_error_dialog, type="flat")


@me.component
def subtle_lyria_input():
    """lyria input"""
    pagestate = me.state(PageState)

    icon_style = me.Style(
        display="flex",
        flex_direction="column",
        gap=2,
        font_size=10,
        align_items="center",
    )
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=me.theme_var("secondary-container"),
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
                min_rows=8,
                placeholder="enter a musical audio description",
                style=me.Style(
                    padding=me.Padding(top=16, left=16, right=16, bottom=16),
                    background=me.theme_var("secondary-container"),
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_lyria_prompt,
                key=str(pagestate.music_prompt_textarea_key),
                value=pagestate.music_prompt_placeholder,
            )
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=10,
                padding=me.Padding( left=16, right=16, bottom=16),
            )
        ):
            # do the lyria
            with me.content_button(
                type="icon",
                on_click=on_click_lyria,
            ):
                with me.box(style=icon_style):
                    me.icon("music_note")
                    me.text("Generate Audio")

            me.box(style=me.Style(height=5))
            # rewriter
            with me.content_button(
                type="icon",
                on_click=on_click_lyria_rewriter,
            ):
                with me.box(style=icon_style):
                    me.icon("auto_awesome")
                    me.text("Rewrite")

            # clear all of this
            with me.content_button(type="icon", on_click=clear_music):
                with me.box(style=icon_style):
                    me.icon("clear")
                    me.text("Clear")


def on_blur_lyria_prompt(e: me.InputBlurEvent):
    """Music prompt blur event"""
    me.state(PageState).music_prompt_input = e.value


def on_click_lyria_rewriter(e: me.ClickEvent):
    """Rewrite the given prompt"""
    state = me.state(PageState)
    rewritten_prompt = rewriter(state.music_prompt_input, MUSIC_REWRITER)
    state.music_prompt_input = rewritten_prompt

    state.music_prompt_placeholder = rewritten_prompt
    yield


def on_click_lyria(e: me.ClickEvent):  # pylint: disable=unused-argument
    """generate music"""
    state = me.state(PageState)
    state.is_loading = True
    state.music_upload_uri = ""
    state.show_error_dialog = False  # Reset error state
    state.error_message = ""
    yield

    print(f"Let's make music!: {state.music_prompt_input}")

    # invoke lyria & get base64 encoded bytes
    start_time = time.time()  # Record the starting time
    try:
        destination_blob_name = generate_music_with_lyria(state.music_prompt_input)

        # set the state var for the audio file uri
        state.music_upload_uri = (
            f"https://storage.mtls.cloud.google.com/{destination_blob_name}"
        )

        print(state.music_upload_uri)

    except ValueError as err:
        state.error_message = str(err)
        state.show_error_dialog = True
    finally:
        end_time = time.time()  # Record the ending time
        execution_time = end_time - start_time  # Calculate the elapsed time
        print(f"Execution time: {execution_time} seconds")  # Print the execution time
        state.timing = f"Generation time: {round(execution_time)} seconds"
        
        try:
            add_music_metadata(
                model=cfg.LYRIA_MODEL_VERSION,
                gcsuri=state.music_upload_uri,
                prompt=state.music_prompt_input,
                generation_time=execution_time,
            )
        except Exception as meta_err:
            # Handle potential errors during metadata storage itself
            print(f"CRITICAL: Failed to store metadata: {meta_err}")

    state.is_loading = False
    yield


def clear_music(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clears music input"""
    state = me.state(PageState)
    state.music_prompt_input = ""
    state.music_prompt_placeholder = ""
    state.music_prompt_textarea_key += 1
    state.music_upload_uri = ""
    state.is_loading = False
    state.show_error_dialog = False
    state.error_message = ""


def on_close_error_dialog(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handler to close the error dialog."""
    state = me.state(PageState)
    state.show_error_dialog = False
    yield


_BOX_STYLE = me.Style(
    #flex_basis="max(480px, calc(50% - 48px))",
    # background="#fff",
    background=me.theme_var("background"),
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
)
