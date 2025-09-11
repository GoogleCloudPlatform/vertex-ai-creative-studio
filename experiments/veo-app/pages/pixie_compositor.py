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

"""A test page for concatenating videos using moviepy."""

from dataclasses import field
import datetime

import mesop as me

from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from common.metadata import MediaItem, add_media_item_to_firestore
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.video_chooser_button import video_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from models.video_processing import process_videos, convert_mp4_to_gif
from state.state import AppState


@me.stateclass
class PageState:
    # Using a dict to store selected videos, keyed by chooser id (e.g., "video_1")
    selected_videos: dict[str, str] = field(default_factory=dict) # pylint: disable=invalid-field-call
    concatenated_video_url: str = ""
    gif_url: str = ""
    is_loading: bool = False
    is_converting_gif: bool = False
    error_message: str = ""
    selected_transition: str = "concat"


VIDEO_PLACEHOLDER_STYLE = me.Style(
    width=360,
    height=200,
    border=me.Border.all(
        me.BorderSide(width=2, style="dashed", color=me.theme_var("outline-variant")),
    ),
    border_radius=8,
    display="flex",
    align_items="center",
    justify_content="center",
    flex_direction="column",
    gap=8,
)

@me.page(
    path="/pixie_compositor",
    title="Pixie Compositor",
)
def pixie_compositor_page():
    with page_scaffold(page_name="pixie_compositor"):  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Pixie Compositor", "auto_fix_high")
            page_content()


def page_content():
    state = me.state(PageState)

    with me.box(style=me.Style(display="flex", flex_direction="column", gap=20)):
        me.text("Select two videos from the library to process.")

        # Video Selection Area
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=20, justify_content="center")):
            # Video 1 Selector
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=10)):
                me.text("Video 1")
                with me.box(style=me.Style(display="flex", flex_direction="row", gap=8, align_items="center")):
                    me.uploader(
                        label="Upload Video",
                        on_upload=on_upload_video_1,
                        accepted_file_types=["video/mp4", "video/quicktime"],
                        style=me.Style(width="100%"),
                    )
                    video_chooser_button(
                        key="video_1", on_library_select=on_video_select
                    )
                with me.box(style=VIDEO_PLACEHOLDER_STYLE):
                    if "video_1" in state.selected_videos:
                        me.video(
                            key=state.selected_videos["video_1"], # Add key to force re-render
                            src=gcs_uri_to_https_url(state.selected_videos["video_1"]),
                            style=me.Style(height="100%", width="100%", border_radius=8),
                        )
                    else:
                        me.icon("movie")
                        me.text("Select Video 1")

            # Video 2 Selector
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=10)):
                me.text("Video 2")
                with me.box(style=me.Style(display="flex", flex_direction="row", gap=8, align_items="center")):
                    me.uploader(
                        label="Upload Video",
                        on_upload=on_upload_video_2,
                        accepted_file_types=["video/mp4", "video/quicktime"],
                        style=me.Style(width="100%"),
                    )
                    video_chooser_button(
                        key="video_2", on_library_select=on_video_select
                    )
                with me.box(style=VIDEO_PLACEHOLDER_STYLE):
                    if "video_2" in state.selected_videos:
                        me.video(
                            key=state.selected_videos["video_2"], # Add key to force re-render
                            src=gcs_uri_to_https_url(state.selected_videos["video_2"]),
                            style=me.Style(height="100%", width="100%", border_radius=8),
                        )
                    else:
                        me.icon("movie")
                        me.text("Select Video 2")

        # Controls
        with me.box(
            style=me.Style(
                display="flex", gap=16, flex_direction="row",  align_items="center", justify_content="center"
            ),
        ):
            # Transition Selector
            me.select(
                label="Transition",
                options=[
                    me.SelectOption(label="Concatenate", value="concat"),
                    me.SelectOption(label="Crossfade", value="x-fade"),
                    me.SelectOption(label="Wipe", value="wipe"),
                    me.SelectOption(label="Dip to Black", value="dipToBlack"),
                ],
                value=state.selected_transition,
                on_selection_change=on_transition_change,
            )

            # Process Button
            me.button(
                "Process Videos",
                on_click=on_process_click,
                disabled=len(state.selected_videos) < 2 or state.is_loading,
                type="raised",
            )

        # Result Area
        if state.is_loading:
            with me.box(style=me.Style(display="flex", justify_content="center")):
                me.progress_spinner()
        
        if state.error_message:
            me.text(state.error_message, style=me.Style(color="red"))

        # result video
        if state.concatenated_video_url:
            with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center", gap=10)):
                me.video(
                    src=gcs_uri_to_https_url(state.concatenated_video_url),
                    style=me.Style(width="100%", max_width="720px", border_radius=8),
                )
                me.button("Convert to GIF", on_click=on_convert_to_gif_click, disabled=state.is_converting_gif)

        if state.is_converting_gif:
            with me.box(style=me.Style(display="flex", justify_content="center")):
                me.progress_spinner()

        if state.gif_url:
            with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center", gap=10)):
                me.text("Video as GIF:", type="headline-5")
                me.image(
                    src=gcs_uri_to_https_url(state.gif_url),
                    style=me.Style(width="100%", max_width="480px", border_radius=8),
                )


def on_upload_video_1(e: me.UploadEvent):
    """Upload video 1 handler."""
    state = me.state(PageState)
    gcs_url = store_to_gcs(
        "pixie_compositor_uploads", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.selected_videos["video_1"] = gcs_url
    yield

def on_upload_video_2(e: me.UploadEvent):
    """Upload video 2 handler."""
    state = me.state(PageState)
    gcs_url = store_to_gcs(
        "pixie_compositor_uploads", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.selected_videos["video_2"] = gcs_url
    yield

def on_video_select(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    # The key of the chooser button tells us which video slot to fill.
    state.selected_videos[e.chooser_id] = e.gcs_uri
    yield

def on_transition_change(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.selected_transition = e.value
    yield

def on_process_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_loading = True
    state.concatenated_video_url = ""
    state.gif_url = ""
    state.error_message = ""
    yield

    try:
        # Ensure videos are in order before processing
        video_uris_to_process = [
            state.selected_videos["video_1"],
            state.selected_videos["video_2"],
        ]
        processed_uri = process_videos(video_uris_to_process, state.selected_transition)
        state.concatenated_video_url = processed_uri

        # Log to Firestore
        add_media_item_to_firestore(
            MediaItem(
                gcsuri=processed_uri,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                mime_type="video/mp4",
                source_images_gcs=video_uris_to_process,
                comment=f"Produced by Pixie Compositor with {state.selected_transition} transition",
                model="pixie-compositor-v1",
            )
        )

    except Exception as ex:
        state.error_message = f"An error occurred: {ex}"
    finally:
        state.is_loading = False
        yield

def on_convert_to_gif_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_converting_gif = True
    state.gif_url = ""
    state.error_message = ""
    yield

    try:
        gif_uri = convert_mp4_to_gif(state.concatenated_video_url)
        state.gif_url = gif_uri

        # Log to Firestore
        add_media_item_to_firestore(
            MediaItem(
                gcsuri=gif_uri,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                mime_type="image/gif",
                source_images_gcs=[state.concatenated_video_url], # Source is the concatenated video
                comment="Produced by Pixie Compositor",
                model="pixie-compositor-v1-gif",
            )
        )

    except Exception as ex:
        state.error_message = f"An error occurred during GIF conversion: {ex}"
    finally:
        state.is_converting_gif = False
        yield