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

import functools

import mesop as me

from state.veo_state import PageState
from components.library.library_chooser_button import library_chooser_button
from config.veo_models import get_veo_model_config

@me.component
def file_uploader(on_upload_image, on_upload_last_image, on_library_select):
    """File uploader for I2V and interpolation, driven by model configuration."""
    state = me.state(PageState)
    selected_config = get_veo_model_config(state.veo_model)

    if not selected_config:
        return

    # Dynamically create the buttons based on the supported modes for the selected model.
    veo_mode_buttons = [
        me.ButtonToggleButton(label=mode, value=mode)
        for mode in selected_config.supported_modes
    ]

    me.button_toggle(
        value=state.veo_mode,
        buttons=veo_mode_buttons,
        multiple=False,
        hide_selection_indicator=True,
        on_change=on_selection_change_veo_mode,
    )
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            align_items="center",
            flex_basis="max(480px, calc(50% - 48px))",
            padding=me.Padding(bottom=15),
            margin=me.Margin(top=6),
        ),
    ):
        if state.veo_mode == "t2v":
            me.image(src=None, style=me.Style(height=250))
        elif state.veo_mode == "i2v":
            _image_uploader(last_image=False, on_upload_image=on_upload_image, on_upload_last_image=on_upload_last_image, on_library_select=on_library_select)
        elif state.veo_mode == "interpolation":
            _image_uploader(last_image=True, on_upload_image=on_upload_image, on_upload_last_image=on_upload_last_image, on_library_select=on_library_select)


@me.component
def _image_uploader(last_image: bool, on_upload_image, on_upload_last_image, on_library_select):
    state = me.state(PageState)
    if state.reference_image_uri:
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
            me.image(
                src=state.reference_image_uri,
                style=me.Style(
                    height=150,
                    border_radius=12,
                ),
                key=str(state.reference_image_file_key),
            )
            if last_image and state.last_reference_image_uri:
                me.image(
                    src=state.last_reference_image_uri,
                    style=me.Style(
                        height=150,
                        border_radius=12,
                    ),
                    key=str(state.last_reference_image_file_key),
                )
    else:
        me.image(src=None, style=me.Style(height=200))
    with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
        if last_image:
            me.uploader(
                label="Upload first",
                accepted_file_types=["image/jpeg", "image/png"],
                on_upload=on_upload_image,
                type="raised",
                color="primary",
                style=me.Style(font_weight="bold"),
            )
            library_chooser_button(key="first_frame_library_chooser", on_library_select=on_library_select, button_type="icon")
            me.uploader(
                label="Upload last",
                key="last",
                accepted_file_types=["image/jpeg", "image/png"],
                on_upload=on_upload_last_image,
                type="raised",
                color="primary",
                style=me.Style(font_weight="bold"),
            )
            library_chooser_button(key="last_frame_library_chooser", on_library_select=on_library_select, button_type="icon")
        else:
            me.uploader(
                label="Upload",
                accepted_file_types=["image/jpeg", "image/png"],
                on_upload=on_upload_image,
                type="raised",
                color="primary",
                style=me.Style(font_weight="bold"),
            )
            library_chooser_button(key="i2v_library_chooser", on_library_select=on_library_select, button_type="icon")
        me.button(label="Clear", on_click=on_click_clear_reference_image)


def on_selection_change_veo_mode(e: me.ButtonToggleChangeEvent):
    """toggle veo mode"""
    state = me.state(PageState)
    state.veo_mode = e.value


def on_click_clear_reference_image(e: me.ClickEvent):
    """Clear reference image"""
    state = me.state(PageState)
    state.reference_image_file = None
    state.reference_image_file_key += 1
    state.reference_image_uri = None
    state.reference_image_gcs = None

    state.last_reference_image_file = None
    state.last_reference_image_file_key += 1
    state.last_reference_image_uri = None
    state.last_reference_image_gcs = None
    state.is_loading = False