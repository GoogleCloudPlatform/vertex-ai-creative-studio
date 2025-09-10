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

import mesop as me

from components.dialog import dialog, dialog_actions
from components.header import header
from components.imagen.advanced_controls import advanced_controls
from components.imagen.generation_controls import generation_controls
from components.imagen.image_output import image_output
from components.imagen.modifier_controls import modifier_controls
from components.page_scaffold import page_frame, page_scaffold
from config.default import ABOUT_PAGE_CONTENT
from state.imagen_state import PageState


@me.page(path="/imagen", title="GenMedia Creative Studio - Imagen")
def imagen_page():
    with page_scaffold(page_name="imagen"):  # pylint: disable=E1129:not-context-manager
        imagen_content(me.state(PageState))


def imagen_content(app_state: me.state):
    """Imagen Mesop Page"""
    state = me.state(PageState)

    if state.info_dialog_open:
        with dialog(is_open=state.info_dialog_open):  # pylint: disable=not-context-manager
            me.text("About Imagen Creative Studio", type="headline-6")
            me.markdown(ABOUT_PAGE_CONTENT["sections"][0]["description"])
            me.divider()
            me.text("Current Settings", type="headline-6")
            me.text(f"Prompt: {state.image_prompt_input}")
            me.text(f"Negative Prompt: {state.image_negative_prompt_input}")
            me.text(f"Model: {state.image_model_name}")
            me.text(f"Aspect Ratio: {state.image_aspect_ratio}")
            with dialog_actions():  # pylint: disable=not-context-manager
                me.button("Close", on_click=close_info_dialog, type="flat")

    with page_frame():  # pylint: disable=not-context-manager
            header(
                "Imagen Creative Studio",
                "image",
                show_info_button=True,
                on_info_click=open_info_dialog,
            )
            with me.box(
                style=me.Style(
                    width="100%", display="flex", flex_direction="column", align_items="center",
                ),
            ):
                with me.box(
                    style=me.Style(
                        width="80vw",
                        display="flex", flex_direction="column"
                    ),
                ):
                    generation_controls()
                    modifier_controls()
                    advanced_controls()
            image_output()

    with dialog(is_open=state.show_dialog):  # pylint: disable=not-context-manager
        me.text(
            "Generation Error",
            type="headline-6",
            style=me.Style(color=me.theme_var("error")),
        )
        me.text(state.dialog_message, style=me.Style(margin=me.Margin(top=16)))
        with dialog_actions():  # pylint: disable=not-context-manager
            me.button("Close", on_click=on_close_dialog, type="flat")


def on_close_dialog(e: me.ClickEvent):
    """Handler to close the dialog."""
    state = me.state(PageState)
    state.show_dialog = False
    yield


def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = True
    yield


def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = False
    yield
