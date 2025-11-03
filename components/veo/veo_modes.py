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

from common.analytics import log_ui_click
from state.state import AppState
from state.veo_state import PageState
from components.library.library_chooser_button import library_chooser_button
from config.veo_models import get_veo_model_config


@me.component
def veo_modes(
    on_upload_image,
    on_upload_last_image,
    on_library_select,
    on_r2v_asset_add,
    on_r2v_asset_remove,
    on_r2v_style_add,
    on_r2v_style_remove,
    on_clear_first_image,
    on_clear_last_image,
    on_click_clear,
):
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
            _image_uploader(
                last_image=False,
                on_upload_image=on_upload_image,
                on_upload_last_image=on_upload_last_image,
                on_library_select=on_library_select,
                on_clear_first_image=on_clear_first_image,
                on_clear_last_image=on_clear_last_image,
            )
        elif state.veo_mode == "interpolation":
            _image_uploader(
                last_image=True,
                on_upload_image=on_upload_image,
                on_upload_last_image=on_upload_last_image,
                on_library_select=on_library_select,
                on_clear_first_image=on_clear_first_image,
                on_clear_last_image=on_clear_last_image,
            )
        elif state.veo_mode == "r2v":
            _r2v_uploader(
                on_r2v_asset_add=on_r2v_asset_add,
                on_r2v_asset_remove=on_r2v_asset_remove,
                on_r2v_style_add=on_r2v_style_add,
                on_r2v_style_remove=on_r2v_style_remove,
                on_library_select=on_library_select,
            )


from common.utils import gcs_uri_to_https_url
from components.image_thumbnail import image_thumbnail


@me.component
def _r2v_uploader(
    on_r2v_asset_add,
    on_r2v_asset_remove,
    on_r2v_style_add,
    on_r2v_style_remove,
    on_library_select,
):
    """Uploader for the Reference-to-Video (r2v) mode."""
    state = me.state(PageState)
    MAX_ASSET_IMAGES = 3

    # Determine if uploaders should be disabled
    style_uploader_disabled = bool(state.r2v_reference_images)
    asset_uploader_disabled = state.r2v_style_image is not None

    with me.box(style=me.Style(display="flex", flex_direction="row", gap=15)):
        # --- Assets Section ---
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
            me.text("Asset references", style=me.Style(font_size="10pt"))
            with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
                for i in range(MAX_ASSET_IMAGES):
                    if i < len(state.r2v_reference_images):
                        image_uri = state.r2v_reference_images[i]
                        image_thumbnail(
                            image_uri=image_uri,
                            index=i,
                            on_remove=on_r2v_asset_remove,
                            icon_size=16,
                        )
                    elif not asset_uploader_disabled and i == len(
                        state.r2v_reference_images
                    ):
                        _uploader_placeholder(
                            on_upload=on_r2v_asset_add,
                            on_library_select=on_library_select,
                            key_prefix="r2v_asset",
                            disabled=asset_uploader_disabled,
                        )
                    else:
                        _empty_placeholder()
        # --- Style Section ---
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
            me.text("Style reference", style=me.Style(font_size="10pt"))
            with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
                if state.r2v_style_image:
                    image_thumbnail(
                        image_uri=state.r2v_style_image,
                        index=0,  # Only one style image
                        on_remove=on_r2v_style_remove,
                        icon_size=16,
                    )
                else:
                    _uploader_placeholder(
                        on_upload=on_r2v_style_add,
                        on_library_select=on_library_select,
                        key_prefix="r2v_style",
                        disabled=style_uploader_disabled,
                    )


@me.component
def _uploader_placeholder(on_upload, on_library_select, key_prefix: str, disabled: bool):
    """A placeholder box with uploader and library chooser buttons."""
    with me.box(
        style=me.Style(
            height=100,
            width=100,
            border=me.Border.all(
                me.BorderSide(
                    width=1,
                    style="dashed",
                    color=me.theme_var("outline"),
                )
            ),
            border_radius=8,
            display="flex",
            flex_direction="column",
            align_items="center",
            justify_content="center",
            gap=8,
            opacity=0.5 if disabled else 1.0,
        )
    ):
        me.uploader(
            label="Add Image",
            on_upload=on_upload,
            accepted_file_types=["image/jpeg", "image/png"],
            key=f"{key_prefix}_uploader",
            disabled=disabled,
        )
        with me.box(style=me.Style(pointer_events="none" if disabled else "auto")):
            library_chooser_button(
                key=f"{key_prefix}_library_chooser",
                on_library_select=on_library_select,
                button_type="icon",
            )


@me.component
def _empty_placeholder():
    """An empty, non-interactive placeholder box."""
    me.box(
        style=me.Style(
            height=100,
            width=100,
            border=me.Border.all(
                me.BorderSide(
                    width=1, style="dashed", color=me.theme_var("outline")
                )
            ),
            border_radius=8,
            opacity=0.5,
        )
    )




@me.component
def _image_uploader(
    last_image: bool,
    on_upload_image,
    on_upload_last_image,
    on_library_select,
    on_clear_first_image,
    on_clear_last_image,
):
    state = me.state(PageState)
    with me.box(style=me.Style(display="flex", flex_direction="row", gap=15)):
        # First Frame
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
            me.text("First Frame", style=me.Style(font_size="10pt"))
            if state.reference_image_uri:
                image_thumbnail(
                    image_uri=state.reference_image_gcs,
                    index=0,
                    on_remove=on_clear_first_image,
                    icon_size=16,
                )
            else:
                _uploader_placeholder(
                    on_upload=on_upload_image,
                    on_library_select=on_library_select,
                    key_prefix="i2v",
                    disabled=False,
                )

        # Last Frame (for interpolation)
        if last_image:
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
                me.text("Last Frame", style=me.Style(font_size="10pt"))
                if state.last_reference_image_uri:
                    image_thumbnail(
                        image_uri=state.last_reference_image_gcs,
                        index=0,
                        on_remove=on_clear_last_image,
                        icon_size=16,
                    )
                else:
                    _uploader_placeholder(
                        on_upload=on_upload_last_image,
                        on_library_select=on_library_select,
                        key_prefix="interpolation_last",
                        disabled=False,
                    )


def on_selection_change_veo_mode(e: me.ButtonToggleChangeEvent):
    """toggle veo mode and validate/update settings."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="veo_mode",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.veo_mode = e.value

    # Yield immediately to allow the UI to rebuild with the new mode.
    yield

    # Get the config for the current model
    model_config = get_veo_model_config(state.veo_model)
    if not model_config:
        yield
        return

    # Check if the new mode has a duration override and update the state if needed.
    if model_config.mode_overrides and e.value in model_config.mode_overrides:
        override = model_config.mode_overrides[e.value]
        if override.default_duration:
            state.video_length = override.default_duration
    yield

def on_click_clear_reference_image(e: me.ClickEvent):
    """Clear reference image"""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="veo_clear_reference_image",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
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
    state.r2v_reference_images = []