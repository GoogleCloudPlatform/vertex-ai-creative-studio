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

import time

import mesop as me

from common.analytics import track_click
from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from common.utils import create_display_url, https_url_to_gcs_uri
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.pill import pill
from components.snackbar import snackbar
from models.upscale import UPSCALE_MODEL, get_image_resolution, upscale_image
from state.state import AppState

IMAGE_BOX_STYLE = me.Style(
    width=512,
    height=512,
    border=me.Border.all(
        me.BorderSide(width=2, style="dashed", color=me.theme_var("outline-variant")),
    ),
    border_radius=12,
    display="flex",
    align_items="center",
    justify_content="center",
    flex_direction="column",
    gap=8,
    margin=me.Margin(top=16),
    background=me.theme_var("surface-container-lowest"),
)


@me.stateclass
class PageState:
    input_image_gcs: str = ""
    input_image_url: str = ""
    input_resolution: str = ""

    output_image_gcs: str = ""
    output_image_url: str = ""
    output_resolution: str = ""

    upscale_factor: str = "x2"
    is_loading: bool = False

    snackbar_message: str = ""
    show_snackbar: bool = False


def on_upload(e: me.UploadEvent):
    state = me.state(PageState)
    gcs_uri = store_to_gcs(
        "upscale_inputs", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.input_image_gcs = gcs_uri
    state.input_image_url = create_display_url(gcs_uri)
    state.input_resolution = get_image_resolution(e.file.getvalue())
    yield


def on_library_select(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    state.input_image_gcs = e.gcs_uri
    state.input_image_url = create_display_url(e.gcs_uri)
    # We need to fetch resolution for library images too
    state.input_resolution = get_image_resolution(e.gcs_uri)
    yield


def on_factor_change(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.upscale_factor = e.value
    yield


@track_click(element_id="upscale_button")
def on_upscale(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)

    if not state.input_image_gcs:
        yield from show_snackbar("Please select an input image first.")
        return

    state.is_loading = True
    state.output_image_gcs = ""
    state.output_image_url = ""
    state.output_resolution = ""
    yield

    try:
        start_time = time.time()
        output_gcs, original_res, upscaled_res = upscale_image(
            state.input_image_gcs, state.upscale_factor
        )
        generation_time = time.time() - start_time

        state.output_image_gcs = output_gcs
        state.output_image_url = create_display_url(output_gcs)
        state.output_resolution = upscaled_res
        # Update input resolution just in case it wasn't set correctly before
        if not state.input_resolution or state.input_resolution == "Unknown":
            state.input_resolution = original_res

        # Save to Firestore
        item = MediaItem(
            user_email=app_state.user_email,
            model=UPSCALE_MODEL,
            mime_type="image/png",
            gcsuri=output_gcs,
            source_images_gcs=[state.input_image_gcs],
            generation_time=generation_time,
            original_resolution=original_res,
            upscale_factor=state.upscale_factor,
            resolution=upscaled_res,
            media_type="image",
            comment="Upscaled image",
        )
        add_media_item_to_firestore(item)
        yield from show_snackbar("Image upscaled and saved to library.")

    except Exception as ex:
        print(f"Upscale error: {ex}")
        yield from show_snackbar(f"Error: {ex}")
    finally:
        state.is_loading = False
        yield


def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.input_image_gcs = ""
    state.input_image_url = ""
    state.input_resolution = ""
    state.output_image_gcs = ""
    state.output_image_url = ""
    state.output_resolution = ""
    yield


def show_snackbar(message: str):
    state = me.state(PageState)
    state.snackbar_message = message
    state.show_snackbar = True
    yield
    time.sleep(3)
    state.show_snackbar = False
    yield


@me.page(path="/imagen-upscale", title="Imagen 4 Upscale")
def page():
    state = me.state(PageState)

    with page_scaffold(page_name="imagen-upscale"):  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Imagen 4 Upscale", "zoom_in", current_status="Preview")

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=24,
                    padding=me.Padding.all(24),
                )
            ):
                # Input Column
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="column", gap=16, flex=1
                    )
                ):
                    me.text("Input Image", type="headline-6")

                    with me.box(style=IMAGE_BOX_STYLE):
                        if state.input_image_url:
                            me.image(
                                src=state.input_image_url,
                                style=me.Style(
                                    max_width="100%",
                                    max_height="100%",
                                    object_fit="contain",
                                ),
                            )
                        else:
                            me.icon(
                                "image",
                                style=me.Style(
                                    font_size=48, color=me.theme_var("outline")
                                ),
                            )
                            me.text("No image selected")

                    if state.input_resolution:
                        pill(
                            label=f"Resolution: {state.input_resolution}",
                            pill_type="resolution",
                        )

                    # controls at bottom of input image
                    with me.box(style=me.Style(display="flex", gap=8)):
                        me.uploader(
                            label="Upload Image",
                            on_upload=on_upload,
                            accepted_file_types=[
                                "image/jpeg",
                                "image/png",
                                "image/webp",
                            ],
                        )
                        library_chooser_button(
                            on_library_select=on_library_select,
                            button_label="Choose from Library",
                        )
                        # Controls Row
                        me.select(
                            label="Upscale Factor",
                            options=[
                                me.SelectOption(label="x2", value="x2"),
                                me.SelectOption(label="x3", value="x3"),
                                me.SelectOption(label="x4", value="x4"),
                            ],
                            value=state.upscale_factor,
                            on_selection_change=on_factor_change,
                            style=me.Style(width="100%"),
                            appearance="outline",
                        )

                    with me.box(
                        style=me.Style(flex_direction="row", display="flex", gap=8)
                    ):
                        me.button(
                            "Upscale",
                            on_click=on_upscale,
                            type="raised",
                            disabled=state.is_loading or not state.input_image_gcs,
                            style=me.Style(width="100%"),
                        )

                        if state.is_loading:
                            me.progress_spinner()

                        me.button(
                            "Clear",
                            on_click=on_clear,
                            type="stroked",
                            style=me.Style(width="100%"),
                        )

                # Output Column
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="column", gap=16, flex=1
                    )
                ):
                    me.text("Upscaled Image", type="headline-6")
                    with me.box(style=IMAGE_BOX_STYLE):
                        if state.output_image_url:
                            me.image(
                                src=state.output_image_url,
                                style=me.Style(
                                    max_width="100%",
                                    max_height="100%",
                                    object_fit="contain",
                                ),
                            )
                        elif state.is_loading:
                            me.progress_spinner()
                        else:
                            me.icon(
                                "image",
                                style=me.Style(
                                    font_size=48, color=me.theme_var("outline")
                                ),
                            )
                            me.text("Output will appear here")

                    if state.output_resolution:
                        pill(
                            label=f"Resolution: {state.output_resolution}",
                            pill_type="resolution",
                        )

            snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)
