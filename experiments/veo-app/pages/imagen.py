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
"""Interpolation"""
import mesop as me

from components.header import header
from components.page_scaffold import (
    page_scaffold,
    page_frame,
)

from models.lyria import generate_music_with_lyria


@me.stateclass
class PageState:
    """Local Page State"""

    is_loading: bool = False

    music_prompt_input: str = ""
    music_prompt_placeholder: str = ""
    music_prompt_textarea_key: int = 0
    music_upload_uri: str = ""


def imagen_content(app_state: me.state):
    """Imagen Mesop Page"""

    pagestate = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Imagen", "image")

            with me.box(style=_BOX_STYLE):
                me.text(
                    "Prompt for scene ideation",
                    style=me.Style(font_weight=500),
                )
                me.box(style=me.Style(height=16))
                subtle_imagen_input()
                me.box(style=me.Style(height=24))

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


@me.component
def subtle_imagen_input():
    """imagen input"""
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
                placeholder="enter a scene description",
                style=me.Style(
                    padding=me.Padding(top=16, left=16, right=16),
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
            )
        ):
            # do the lyria
            with me.content_button(
                type="icon",
                on_click=on_click_lyria,
            ):
                with me.box(style=icon_style):
                    me.icon("play_arrow")
                    me.text("Generate Images")

            me.box(style=me.Style(height=5))
            # rewriter
            with me.content_button(
                type="icon",
                on_click=on_click_lyria,
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
    try:
        destination_blob_name = generate_music_with_lyria(state.music_prompt_input)

        # set the state var for the audio file uri
        state.music_upload_uri = (
            f"https://storage.mtls.cloud.google.com/{destination_blob_name}"
        )

        print(state.music_upload_uri)
    except ValueError as err:
        state.modal_open = True
        state.modal_message = str(err)

    state.is_loading = False
    yield


def clear_music(e: me.ClickEvent):
    """Clears music input"""
    state = me.state(PageState)
    state.music_prompt_input = ""
    state.music_prompt_placeholder = ""
    state.music_prompt_textarea_key += 1
    state.music_upload_uri = ""
    state.is_loading = False


_BOX_STYLE = me.Style(
    flex_basis="max(480px, calc(50% - 48px))",
    # background="#fff",
    background=me.theme_var("background"),
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
)
