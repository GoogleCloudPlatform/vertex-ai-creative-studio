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

import datetime
import time
from dataclasses import field, dataclass
from typing import Callable

import mesop as me

from common.metadata import (
    MediaItem,
    add_media_item_to_firestore,
    get_media_for_chooser,
    db,
    config,
)
from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from components.dialog import dialog
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.media_chooser_button import media_chooser_button
from components.media_tile.media_tile import media_tile, get_pills_for_item
from components.page_scaffold import page_frame, page_scaffold
from components.scroll_sentinel.scroll_sentinel import scroll_sentinel
from components.snackbar import snackbar
from models.video_processing import (
    convert_mp4_to_gif,
    layer_audio_on_video,
    process_videos,
)
from state.state import AppState


@me.stateclass
class PageState:
    # Using a dict to store selected videos, keyed by chooser id (e.g., "video_1")
    selected_videos: dict[str, str] = field(default_factory=dict)
    concatenated_video_url: str = ""
    gif_url: str = ""
    is_loading: bool = False
    is_converting_gif: bool = False
    error_message: str = ""
    selected_transition: str = "concat"
    show_snackbar: bool = False
    snackbar_message: str = ""
    show_error_dialog: bool = False
    dialog_title: str = ""
    dialog_message: str = ""
    active_tab: str = "video_video"
    selected_video_for_audio: str = ""
    selected_audio: str = ""

    # State for the new media chooser dialog
    show_chooser_dialog: bool = False
    chooser_dialog_media_type: str = ""
    chooser_dialog_key: str = ""
    chooser_is_loading: bool = False
    chooser_media_items: list[MediaItem] = field(default_factory=list)
    chooser_last_doc_id: str = ""
    chooser_all_items_loaded: bool = False


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
    with page_scaffold(page_name="pixie_compositor"):
        with page_frame():
            header("Pixie Compositor", "auto_fix_high")
            page_content()
            render_chooser_dialog()  # Add dialog to the page layout


# Adapted from components/tab_nav.py
@dataclass
class Tab:
    key: str
    label: str
    icon: str | None = None


def on_tab_change(e: me.ClickEvent):
    state = me.state(PageState)
    state.active_tab = e.key
    yield


@me.component
def _tab_group(tabs: list[Tab], on_tab_click: Callable, selected_tab_key: str):
    with me.box(
        style=me.Style(
            display="flex",
            border=me.Border(
                bottom=me.BorderSide(
                    width=1, style="solid", color=me.theme_var("outline-variant")
                )
            ),
        )
    ):
        for tab in tabs:
            is_selected = tab.key == selected_tab_key
            with me.box(
                key=tab.key,
                on_click=on_tab_click,
                style=_make_tab_style(is_selected),
            ):
                if tab.icon:
                    me.icon(tab.icon)
                me.text(tab.label)


def _make_tab_style(selected: bool) -> me.Style:
    style = me.Style(
        align_items="center",
        color=me.theme_var("on-surface"),
        display="flex",
        cursor="pointer",
        flex_grow=1,
        justify_content="center",
        line_height=1,
        font_size=14,
        font_weight="medium",
        padding=me.Padding.all(16),
        text_align="center",
        gap=5,
    )
    if selected:
        style.background = me.theme_var("surface-container")
        style.border = me.Border(
            bottom=me.BorderSide(width=2, style="solid", color=me.theme_var("primary"))
        )
        style.cursor = "default"
    return style


def page_content():
    state = me.state(PageState)

    tabs = [
        Tab(key="video_video", label="Video + Video", icon="movie"),
        Tab(key="video_audio", label="Video + Audio", icon="music_video"),
    ]

    _tab_group(tabs=tabs, on_tab_click=on_tab_change, selected_tab_key=state.active_tab)

    # Conditionally render tab content
    if state.active_tab == "video_video":
        render_video_video_tab()
    elif state.active_tab == "video_audio":
        render_video_audio_tab()

    snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)


def open_video_chooser(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_chooser_dialog = True
    state.chooser_dialog_media_type = "video"
    state.chooser_dialog_key = e.key
    state.chooser_is_loading = True
    state.chooser_media_items = []
    state.chooser_all_items_loaded = False
    state.chooser_last_doc_id = ""
    yield

    items, last_doc = get_media_for_chooser(media_type="video", page_size=20)
    state.chooser_media_items = items
    state.chooser_last_doc_id = last_doc.id if last_doc else ""
    if not last_doc:
        state.chooser_all_items_loaded = True
    state.chooser_is_loading = False
    yield


def open_audio_chooser(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_chooser_dialog = True
    state.chooser_dialog_media_type = "audio"
    state.chooser_dialog_key = e.key
    state.chooser_is_loading = True
    state.chooser_media_items = []
    state.chooser_all_items_loaded = False
    state.chooser_last_doc_id = ""
    yield

    items, last_doc = get_media_for_chooser(media_type="audio", page_size=20)
    state.chooser_media_items = items
    state.chooser_last_doc_id = last_doc.id if last_doc else ""
    if not last_doc:
        state.chooser_all_items_loaded = True
    state.chooser_is_loading = False
    yield


def render_video_video_tab():
    state = me.state(PageState)
    with me.box(
        style=me.Style(
            display="flex", flex_direction="column", gap=20, margin=me.Margin(top=20)
        )
    ):
        me.text("Select two videos from the library to process.")

        # Video Selection Area
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=20, justify_content="center"
            )
        ):
            # Video 1 Selector
            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=10)
            ):
                me.text("Video 1")
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=8, align_items="center"
                    )
                ):
                    me.uploader(
                        label="Upload Video",
                        on_upload=on_upload_video_1,
                        accepted_file_types=["video/mp4", "video/quicktime"],
                        style=me.Style(width="100%"),
                    )
                    media_chooser_button(
                        key="video_1", on_click=open_video_chooser, media_type="video"
                    )
                with me.box(style=VIDEO_PLACEHOLDER_STYLE):
                    if "video_1" in state.selected_videos:
                        me.video(
                            key=state.selected_videos["video_1"],  # Add key to force re-render
                            src=gcs_uri_to_https_url(state.selected_videos["video_1"]),
                            style=me.Style(
                                height="100%",
                                width="100%",
                                border_radius=8,
                                object_fit="contain",
                            ),
                        )
                    else:
                        me.icon("movie")
                        me.text("Select Video 1")

            # Video 2 Selector
            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=10)
            ):
                me.text("Video 2")
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=8, align_items="center"
                    )
                ):
                    me.uploader(
                        label="Upload Video",
                        on_upload=on_upload_video_2,
                        accepted_file_types=["video/mp4", "video/quicktime"],
                        style=me.Style(width="100%"),
                    )
                    media_chooser_button(
                        key="video_2", on_click=open_video_chooser, media_type="video"
                    )
                with me.box(style=VIDEO_PLACEHOLDER_STYLE):
                    if "video_2" in state.selected_videos:
                        me.video(
                            key=state.selected_videos["video_2"],  # Add key to force re-render
                            src=gcs_uri_to_https_url(state.selected_videos["video_2"]),
                            style=me.Style(height="100%", width="100%", border_radius=8),
                        )
                    else:
                        me.icon("movie")
                        me.text("Select Video 2")

        # Controls
        with me.box(
            style=me.Style(
                display="flex",
                gap=16,
                flex_direction="row",
                align_items="center",
                justify_content="center",
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
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    gap=10,
                )
            ):
                me.video(
                    src=gcs_uri_to_https_url(state.concatenated_video_url),
                    style=me.Style(width="100%", max_width="720px", border_radius=8),
                )
                me.button(
                    "Convert to GIF",
                    on_click=on_convert_to_gif_click,
                    disabled=state.is_converting_gif,
                )

        if state.is_converting_gif:
            with me.box(style=me.Style(display="flex", justify_content="center")):
                me.progress_spinner()

        if state.gif_url:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    gap=10,
                )
            ):
                me.text("Video as GIF:", type="headline-5")
                me.image(
                    src=gcs_uri_to_https_url(state.gif_url),
                    style=me.Style(width="100%", max_width="480px", border_radius=8),
                )


def render_video_audio_tab():
    state = me.state(PageState)
    with me.box(
        style=me.Style(
            display="flex", flex_direction="column", gap=20, margin=me.Margin(top=20)
        )
    ):
        me.text("Select a video and an audio file to layer.")

        # Media Selection Area
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=20, justify_content="center"
            )
        ):
            # Video Selector
            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=10)
            ):
                me.text("Video")
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=8, align_items="center"
                    )
                ):
                    me.uploader(
                        label="Upload Video",
                        on_upload=on_upload_video_for_audio,
                        accepted_file_types=["video/mp4", "video/quicktime"],
                        style=me.Style(width="100%"),
                    )
                    media_chooser_button(
                        key="video_for_audio",
                        on_click=open_video_chooser,
                        media_type="video",
                    )
                with me.box(style=VIDEO_PLACEHOLDER_STYLE):
                    if state.selected_video_for_audio:
                        me.video(
                            key=state.selected_video_for_audio,  # Add key to force re-render
                            src=gcs_uri_to_https_url(state.selected_video_for_audio),
                            style=me.Style(
                                height="100%",
                                width="100%",
                                border_radius=8,
                                object_fit="contain",
                            ),
                        )
                    else:
                        me.icon("movie")
                        me.text("Select a Video")

            # Audio Selector
            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=10)
            ):
                me.text("Audio")
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=8, align_items="center"
                    )
                ):
                    me.uploader(
                        label="Upload Audio",
                        on_upload=on_upload_audio,
                        accepted_file_types=["audio/mpeg", "audio/wav"],
                        style=me.Style(width="100%"),
                    )
                    media_chooser_button(
                        key="audio_1", on_click=open_audio_chooser, media_type="audio"
                    )
                    # Future: Add audio_chooser_button if created
                with me.box(style=VIDEO_PLACEHOLDER_STYLE):
                    if state.selected_audio:
                        me.audio(
                            src=gcs_uri_to_https_url(state.selected_audio),
                        )
                    else:
                        me.icon("music_note")
                        me.text("Select an Audio File")

        # Controls
        with me.box(
            style=me.Style(
                display="flex",
                gap=16,
                flex_direction="row",
                align_items="center",
                justify_content="center",
            ),
        ):
            me.button(
                "Layer Audio on Video",
                on_click=on_layer_audio_click,
                disabled=not state.selected_video_for_audio
                or not state.selected_audio
                or state.is_loading,
                type="raised",
            )

        # Result Area (reusing components from the other tab)
        if state.is_loading:
            with me.box(style=me.Style(display="flex", justify_content="center")):
                me.progress_spinner()

        if state.error_message:
            me.text(state.error_message, style=me.Style(color="red"))

        if state.concatenated_video_url:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    gap=10,
                )
            ):
                me.video(
                    src=gcs_uri_to_https_url(state.concatenated_video_url),
                    style=me.Style(width="100%", max_width="720px", border_radius=8),
                )


@me.component
def render_chooser_dialog():
    """Renders the single, page-level dialog for choosing media."""
    state = me.state(PageState)

    def handle_item_selected(e: me.ClickEvent):
        gcs_uri = e.key
        # Based on which button opened the dialog, update the correct state variable.
        if state.chooser_dialog_key == "video_1":
            state.selected_videos["video_1"] = gcs_uri
        elif state.chooser_dialog_key == "video_2":
            state.selected_videos["video_2"] = gcs_uri
        elif state.chooser_dialog_key == "video_for_audio":
            state.selected_video_for_audio = gcs_uri
        elif state.chooser_dialog_key == "audio_1":
            state.selected_audio = gcs_uri

        state.show_chooser_dialog = False
        yield

    def handle_load_more(e: me.WebEvent):
        if state.chooser_is_loading or state.chooser_all_items_loaded:
            return

        state.chooser_is_loading = True
        yield

        last_doc_ref = (
            db.collection(config.GENMEDIA_COLLECTION_NAME)
            .document(state.chooser_last_doc_id)
            .get()
        )

        new_items, last_doc = get_media_for_chooser(
            media_type=state.chooser_dialog_media_type,
            page_size=20,
            start_after=last_doc_ref,
        )
        state.chooser_media_items.extend(new_items)
        state.chooser_last_doc_id = last_doc.id if last_doc else ""
        if not last_doc:
            state.chooser_all_items_loaded = True
        state.chooser_is_loading = False
        yield

    dialog_style = me.Style(
        width="95vw", height="80vh", display="flex", flex_direction="column"
    )

    with dialog(is_open=state.show_chooser_dialog, dialog_style=dialog_style):
        if state.show_chooser_dialog:
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="column", gap=16, flex_grow=1
                )
            ):
                # Dialog header with title and close button
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        justify_content="space-between",
                        align_items="center",
                        width="100%",
                    )
                ):
                    me.text(
                        f"Select a {state.chooser_dialog_media_type.capitalize()} from Library",
                        type="headline-6",
                    )
                    with me.content_button(
                        type="icon",
                        on_click=lambda e: setattr(
                            state, "show_chooser_dialog", False
                        ),
                    ):
                        me.icon("close")

                # Main content area with grid and scroller
                with me.box(
                    style=me.Style(
                        flex_grow=1, overflow_y="auto", padding=me.Padding.all(10)
                    )
                ):
                    if state.chooser_is_loading and not state.chooser_media_items:
                        with me.box(
                            style=me.Style(
                                display="flex",
                                justify_content="center",
                                align_items="center",
                                height="100%",
                            )
                        ):
                            me.progress_spinner()
                    else:
                        with me.box(
                            style=me.Style(
                                display="grid",
                                grid_template_columns="repeat(auto-fill, minmax(250px, 1fr))",
                                gap="16px",
                            )
                        ):
                            items_to_render = state.chooser_media_items
                            if not items_to_render and not state.chooser_is_loading:
                                me.text(
                                    f"No items of type '{state.chooser_dialog_media_type}' found in your library."
                                )
                            else:
                                for item in items_to_render:
                                    https_url = gcs_uri_to_https_url(
                                        item.gcsuri
                                        or (item.gcs_uris[0] if item.gcs_uris else "")
                                    )
                                    media_tile(
                                        key=item.gcsuri
                                        or (item.gcs_uris[0] if item.gcs_uris else ""),
                                        on_click=handle_item_selected,
                                        media_type=item.media_type
                                        or state.chooser_dialog_media_type,
                                        https_url=https_url,
                                        pills_json=get_pills_for_item(item, https_url),
                                    )
                        scroll_sentinel(
                            on_visible=handle_load_more,
                            is_loading=state.chooser_is_loading,
                            all_items_loaded=state.chooser_all_items_loaded,
                        )


def on_upload_video_for_audio(e: me.UploadEvent):
    """Upload video handler for the audio tab."""
    state = me.state(PageState)
    gcs_url = store_to_gcs(
        "pixie_compositor_uploads", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.selected_video_for_audio = gcs_url
    yield


def on_video_select_for_audio(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    state.selected_video_for_audio = e.gcs_uri
    yield


def on_upload_audio(e: me.UploadEvent):
    """Upload audio handler for the audio tab."""
    state = me.state(PageState)
    gcs_url = store_to_gcs(
        "pixie_compositor_uploads", e.file.name, e.file.mime_type, e.file.getvalue()
    )
    state.selected_audio = gcs_url
    yield


def on_audio_select_from_library(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    state.selected_audio = e.gcs_uri
    yield


def on_layer_audio_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_loading = True
    state.concatenated_video_url = ""
    state.gif_url = ""
    state.error_message = ""
    yield

    try:
        processed_uri = layer_audio_on_video(
            state.selected_video_for_audio, state.selected_audio
        )
        state.concatenated_video_url = processed_uri

        # Log to Firestore
        add_media_item_to_firestore(
            MediaItem(
                gcsuri=processed_uri,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                mime_type="video/mp4",
                source_uris=[state.selected_video_for_audio, state.selected_audio],
                comment="Produced by Pixie Compositor: Video + Audio",
                model="pixie-compositor-v1-audio-layer",
            )
        )

    except Exception as ex:
        state.error_message = f"An error occurred: {ex}"
    finally:
        state.is_loading = False
        yield


def show_snackbar(state: PageState, message: str):
    """Displays a snackbar message at the bottom of the page."""
    state.snackbar_message = message
    state.show_snackbar = True
    yield


def on_close_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_error_dialog = False
    yield


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
        processed_uri = process_videos(
            video_uris_to_process, state.selected_transition
        )
        state.concatenated_video_url = processed_uri

        # Log to Firestore
        add_media_item_to_firestore(
            MediaItem(
                gcsuri=processed_uri,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                mime_type="video/mp4",
                source_uris=video_uris_to_process,
                comment=f"Produced by Pixie Compositor with {state.selected_transition} transition",
                model="pixie-compositor-v1",
            )
        )

    except ValueError as ex:
        # Catch the specific resolution error and show a dialog
        state.dialog_title = "Resolution Mismatch"
        state.dialog_message = str(ex)
        state.show_error_dialog = True
    except Exception as ex:
        # Catch other generic errors
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
        state.gif_url = convert_mp4_to_gif(state.concatenated_video_url, user_email=app_state.user_email)
    except Exception as ex:
        state.error_message = f"An error occurred during GIF conversion: {ex}"
    finally:
        state.is_converting_gif = False
        yield
