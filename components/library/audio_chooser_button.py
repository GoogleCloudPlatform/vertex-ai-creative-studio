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


from dataclasses import dataclass, field
from typing import Callable, Optional

import mesop as me

from common.metadata import MediaItem, get_media_for_page_optimized, db, config
from components.dialog import dialog
from components.library.events import LibrarySelectionChangeEvent


@me.stateclass
class State:
    """Local mesop state for the audio chooser button."""
    show_dialog: bool = False
    active_chooser_key: str = ""
    is_loading: bool = False
    media_items: list[MediaItem] = field(default_factory=list)
    has_more_items: bool = True


@me.component
def audio_chooser_button(
    on_library_select: Callable[[LibrarySelectionChangeEvent], None],
    button_label: Optional[str] = None,
    button_type: str = "stroked",
    key: str = "",
):
    """Render a button that opens a dialog to select audio from the library."""
    state = me.state(State)

    def open_dialog(e: me.ClickEvent):
        """Open the dialog and load the first page of audio."""
        state.active_chooser_key = e.key
        state.show_dialog = True
        state.is_loading = True
        state.media_items = []
        state.has_more_items = True
        yield

        items, last_doc = get_media_for_page_optimized(20, ["music"])
        print(f"Found {len(items)} audio files in the library.")
        state.media_items = items
        state.is_loading = False
        if not last_doc:
            state.has_more_items = False
        yield

    def handle_image_selected(e: me.ClickEvent):
        """Handle the audio selection from the list."""
        event = LibrarySelectionChangeEvent(
            chooser_id=state.active_chooser_key,
            gcs_uri=e.key,
        )
        yield from on_library_select(event)
        state.show_dialog = False
        yield

    with me.content_button(on_click=open_dialog, type=button_type, key=key):
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=8, align_items="center")):
            me.icon("music_note")
            if button_label:
                me.text(button_label)

    dialog_style = me.Style(width="95vw", height="80vh", display="flex", flex_direction="column")

    with dialog(is_open=state.show_dialog, dialog_style=dialog_style):
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=16, flex_grow=1)):
            me.text("Select Audio from Library", type="headline-6")
            with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
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
                    for item in state.media_items:
                        uri = item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)
                        if uri:
                            with me.box(key=uri, on_click=handle_image_selected, style=me.Style(padding=me.Padding.all(8), cursor="pointer")):
                                me.text(uri.split("/")[-1])


            with me.box(style=me.Style(display="flex", justify_content="flex-end", margin=me.Margin(top=24))):
                me.button(
                    "Cancel",
                    on_click=lambda e: setattr(state, "show_dialog", False),
                    type="stroked",
                )

