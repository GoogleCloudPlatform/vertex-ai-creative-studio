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

"""A temporary page to test the new media_chooser_button component."""

from dataclasses import field

import mesop as me

from common.metadata import MediaItem, config, db, get_media_for_chooser
from common.utils import gcs_uri_to_https_url
from components.dialog import dialog
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.media_chooser_button import media_chooser_button
from components.media_tile.media_tile import get_pills_for_item, media_tile
from components.page_scaffold import page_frame, page_scaffold
from components.scroll_sentinel.scroll_sentinel import scroll_sentinel


@me.stateclass
class PageState:
    # UI state
    selected_video_uri: str = ""
    selected_audio_uri: str = ""
    selected_image_uri: str = ""

    # Dialog state
    show_dialog: bool = False
    dialog_media_type: str = ""  # To control the dialog's content
    dialog_chooser_id: str = ""  # To know which button opened the dialog
    is_loading: bool = False
    media_items: list[MediaItem] = field(default_factory=list)  # pylint: disable=E3701:invalid-field-call
    last_doc_id: str = ""  # For pagination, store only the ID
    all_items_loaded: bool = False


@me.page(
    path="/test_media_chooser",
    title="Test Media Chooser",
)
def page():
    """Main test page."""
    with page_scaffold(page_name="test_media_chooser"):  # pylint: disable=E1129:not-context-manager
        with page_frame():  # pylint: disable=E1129:not-context-manager
            header("Test Media Chooser", "science")
            page_content()
            # The dialog is now part of the page, not the button.
            render_chooser_dialog()


def page_content():
    """The main content of the test page."""
    state = me.state(PageState)

    def open_dialog_for(e: me.ClickEvent, media_type: str):
        print(
            f"<-- LOGGER: Button with key '{e.key}' clicked. Opening dialog for media_type: '{media_type}' -->"
        )
        state.show_dialog = True
        state.dialog_media_type = media_type
        state.dialog_chooser_id = e.key
        state.is_loading = True
        state.media_items = []
        state.all_items_loaded = False
        state.last_doc_id = ""
        yield

        # Fetch real data
        items, last_doc = get_media_for_chooser(media_type=media_type, page_size=20)
        state.media_items = items
        state.last_doc_id = last_doc.id if last_doc else ""
        if not last_doc:
            state.all_items_loaded = True
        state.is_loading = False
        print(f"<-- LOGGER: {len(items)} items loaded for dialog. -->")
        yield

    with me.box(style=me.Style(display="flex", flex_direction="column", gap=20)):
        me.text(
            "This page is for testing the new media_chooser_button component in isolation."
        )

        # Test the video chooser
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=16, align_items="center"
            )
        ):
            media_chooser_button(
                key="video_chooser_1",
                on_click=lambda e: open_dialog_for(e, "video"),
                media_type="video",
                button_label="Choose a Video",
            )
            me.text(f"Selected Video: {state.selected_video_uri or 'None'}")

        # Test the audio chooser
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=16, align_items="center",
            )
        ):
            media_chooser_button(
                key="audio_chooser_1",
                on_click=lambda e: open_dialog_for(e, "audio"),
                media_type="audio",
                button_label="Choose Audio",
            )
            me.text(f"Selected Audio: {state.selected_audio_uri or 'None'}")

        # Test the image chooser
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=16, align_items="center"
            )
        ):
            media_chooser_button(
                key="image_chooser_1",
                on_click=lambda e: open_dialog_for(e, "image"),
                media_type="image",
                button_label="Choose an Image",
            )
            me.text(f"Selected Image: {state.selected_image_uri or 'None'}")


@me.component
def render_chooser_dialog():
    """Renders the single, page-level dialog for choosing media."""
    state = me.state(PageState)

    def handle_item_selected(e: me.ClickEvent):
        gcs_uri = e.key
        print(
            f"<-- LOGGER: Item selected. Chooser ID: '{state.dialog_chooser_id}'. GCS URI: {gcs_uri} -->"
        )

        if state.dialog_chooser_id == "video_chooser_1":
            state.selected_video_uri = gcs_uri
        elif state.dialog_chooser_id == "audio_chooser_1":
            state.selected_audio_uri = gcs_uri
        elif state.dialog_chooser_id == "image_chooser_1":
            state.selected_image_uri = gcs_uri

        state.show_dialog = False
        yield

    def handle_load_more(e: me.WebEvent):
        if state.is_loading or state.all_items_loaded:
            return

        print(f"<-- LOGGER: Loading more items for {state.dialog_media_type} -->")
        state.is_loading = True
        yield

        # Re-fetch the snapshot from the stored ID to use as a cursor
        last_doc_ref = (
            db.collection(config.GENMEDIA_COLLECTION_NAME)
            .document(state.last_doc_id)
            .get()
        )

        new_items, last_doc = get_media_for_chooser(
            media_type=state.dialog_media_type, page_size=20, start_after=last_doc_ref
        )
        state.media_items.extend(new_items)
        state.last_doc_id = last_doc.id if last_doc else ""
        if not last_doc:
            state.all_items_loaded = True
        state.is_loading = False
        yield

    dialog_style = me.Style(
        width="95vw", height="80vh", display="flex", flex_direction="column"
    )

    with dialog(is_open=state.show_dialog, dialog_style=dialog_style):  # pylint: disable=E1129:not-context-manager
        if state.show_dialog:
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="column", gap=16, flex_grow=1,
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
                        f"Select a {state.dialog_media_type.capitalize()} from Library",
                        type="headline-6",
                    )
                    with me.content_button(
                        type="icon",
                        on_click=lambda e: setattr(state, "show_dialog", False),
                    ):
                        me.icon("close")

                # Main content area with grid and scroller
                with me.box(
                    style=me.Style(
                        flex_grow=1, overflow_y="auto", padding=me.Padding.all(10)
                    )
                ):
                    if state.is_loading and not state.media_items:
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
                            items_to_render = (
                                state.media_items
                            )  # No need to filter, query does it now
                            if not items_to_render and not state.is_loading:
                                me.text(
                                    f"No items of type '{state.dialog_media_type}' found in your library."
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
                                        or state.dialog_media_type,
                                        https_url=https_url,
                                        pills_json=get_pills_for_item(item, https_url),
                                    )
                        scroll_sentinel(
                            on_visible=handle_load_more,
                            is_loading=state.is_loading,
                            all_items_loaded=state.all_items_loaded,
                        )
