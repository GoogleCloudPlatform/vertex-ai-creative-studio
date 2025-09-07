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

"""Test page for the Pixie Compositor component."""

import base64
import uuid

import mesop as me

from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.video_chooser_button import video_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.pixie_compositor.pixie_compositor import pixie_compositor
from state.state import AppState


@me.stateclass
class PageState:
    logs: str = ""
    result_gif: str = ""
    start_encode: bool = False
    ffmpeg_loaded: bool = False
    is_encoding: bool = False
    selected_video_gcs_uri: str = ""
    selected_video_url: str = ""  # For the component
    selected_video_display_url: str = ""  # For the video player
    snackbar_message: str = ""


@me.page(
    path="/test_pixie_compositor",
    title="Test Pixie Compositor",
)
def test_pixie_compositor_page():
    state = me.state(PageState)
    with page_scaffold(page_name="test_pixie_compositor"):  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Pixie Compositor Test", "movie")

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=20)):
                with me.box(
                    style=me.Style(display="flex", flex_direction="column", gap=10)
                ):
                    me.text("Select a video from the library:")
                    video_chooser_button(on_library_select=on_video_select)

                    if state.selected_video_display_url:
                        me.video(
                            src=state.selected_video_display_url,
                            style=me.Style(height="200px"),
                        )

                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="column", gap=10, flex_grow=1
                    )
                ):
                    with me.content_button(
                        on_click=on_start_click,
                        disabled=not state.ffmpeg_loaded
                        or state.is_encoding
                        or not state.selected_video_url,
                        type="flat",
                    ):
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="row",
                                align_items="center",
                                gap=8,
                            )
                        ):
                            if state.is_encoding:
                                me.progress_spinner(diameter=20, stroke_width=3)
                                me.text("Encoding...")
                            else:
                                me.text("Start Encoding")

                    me.text("Logs:")
                    with me.box(
                        style=me.Style(
                            height="200px",
                            width="100%",
                            border=me.Border.all(me.BorderSide(width=1)),
                            overflow_y="scroll",
                        )
                    ):
                        me.text(state.logs, style=me.Style(white_space="pre-wrap"))

            me.text("Result:")
            if state.result_gif:
                me.image(src=state.result_gif)
                me.button("Save to Library", on_click=on_save_to_library_click)
            else:
                me.text("GIF will appear here")

            if state.snackbar_message:
                me.text(
                    state.snackbar_message,
                    style=me.Style(
                        padding=me.Padding.all(12),
                        background="#e0e0e0",
                        border_radius=6,
                    ),
                )

            pixie_compositor(
                video_url=state.selected_video_url,
                config={"fps": 15, "scale": 0.5},
                start_encode=state.start_encode,
                on_log=on_log,
                on_encode_complete=on_encode_complete,
                on_load_complete=on_load_complete,
            )


def on_video_select(e: LibrarySelectionChangeEvent):
    print(f"on_video_select event received in Python: {e}")
    state = me.state(PageState)
    state.selected_video_gcs_uri = e.gcs_uri
    state.selected_video_url = e.gcs_uri  # Pass the gs:// URI to the component
    state.selected_video_display_url = e.gcs_uri.replace(
        "gs://", "https://storage.mtls.cloud.google.com/"
    )
    yield


def on_start_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.is_encoding = True
    state.start_encode = True
    state.logs = ""
    state.result_gif = ""
    yield
    state.start_encode = False
    yield


def on_log(e: me.WebEvent):
    state = me.state(PageState)
    state.logs += e.value + "\n"
    yield


def on_encode_complete(e: me.WebEvent):
    state = me.state(PageState)
    state.result_gif = e.value
    state.is_encoding = False
    yield


def on_load_complete(e: me.WebEvent):
    print("on_load_complete event received in Python:", e)
    state = me.state(PageState)
    state.ffmpeg_loaded = True
    yield


def on_save_to_library_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)

    if not state.result_gif:
        return

    try:
        # Decode the Base64 data URL
        header, encoded = state.result_gif.split(",", 1)
        data = base64.b64decode(encoded)

        # Generate a unique filename
        filename = f"pixie-compositor-gif-{uuid.uuid4()}.gif"

        # Upload to GCS
        gcs_uri = store_to_gcs("generated_gifs", filename, "image/gif", data)

        # Add metadata to Firestore
        add_media_item_to_firestore(
            MediaItem(
                gcs_uris=[gcs_uri],  # Use gcs_uris to be consistent with the library
                prompt="a GIF generated by Pixie Compositor",
                mime_type="image/gif",
                user_email=app_state.user_email,
                source_images_gcs=[state.selected_video_gcs_uri],
                comment="Generated by Pixie Compositor",
                model="aaie-pixie-compositor",
            )
        )

        # Optionally, show a success message
        state.snackbar_message = "GIF saved to library successfully!"

    except Exception as ex:
        state.snackbar_message = f"Error saving GIF: {ex}"

    yield
