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

from common.metadata import MediaItem, get_media_for_page
from components.dialog import dialog
from components.library.events import LibrarySelectionChangeEvent
from components.library.infinite_scroll_library import infinite_scroll_library


@me.stateclass
class State:
    """Local mesop state for the infinite scroll chooser button."""

    show_dialog: bool = False
    active_chooser_key: str = ""
    is_loading: bool = False
    media_items: list[MediaItem] = field(default_factory=list)  # pylint: disable=invalid-field-call
    current_page: int = 1
    has_more_items: bool = True


@me.component
def infinite_scroll_chooser_button(
    on_library_select: Callable[[LibrarySelectionChangeEvent], None],
    button_label: Optional[str] = None,
    button_type: str = "stroked",
    key: str = "",
):
    """Render a button that opens a dialog to select an image from the library with infinite scroll."""
    state = me.state(State)

    def open_dialog(e: me.ClickEvent):
        """Open the dialog and load the first page of images."""
        state.active_chooser_key = e.key
        state.show_dialog = True
        state.is_loading = True
        state.current_page = 1
        state.media_items = []
        state.has_more_items = True
        yield

        items = get_media_for_page(
            state.current_page, 20, ["images"], sort_by_timestamp=True
        )
        state.media_items = items
        state.is_loading = False
        if not items:
            state.has_more_items = False
        yield

    def handle_load_more(e: me.WebEvent):
        """Load the next page of images when the user scrolls to the bottom."""
        if state.is_loading or not state.has_more_items:
            return

        state.is_loading = True
        state.current_page += 1
        yield

        new_items = get_media_for_page(
            state.current_page, 20, ["images"], sort_by_timestamp=True
        )
        if new_items:
            state.media_items.extend(new_items)
        else:
            state.has_more_items = False
        state.is_loading = False
        yield

    def handle_image_selected(e: me.WebEvent):
        """Handle the image selection from the web component."""
        event = LibrarySelectionChangeEvent(
            chooser_id=state.active_chooser_key,
            gcs_uri=e.value["uri"],
        )
        yield from on_library_select(event)
        state.show_dialog = False
        yield

    with me.content_button(on_click=open_dialog, type=button_type, key=key):
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=8, align_items="center"
            )
        ):
            me.icon("photo_library")
            if button_label:
                me.text(button_label)

    dialog_style = me.Style(
        width="75vw", height="80vh", display="flex", flex_direction="column"
    )

    with dialog(is_open=state.show_dialog, dialog_style=dialog_style):  # pylint: disable=not-context-manager
        with me.box(
            style=me.Style(display="flex", flex_direction="column", gap=16, flex_grow=1)
        ):
            me.text("Select an Image from Library", type="headline-6")
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
                    items_to_render = []
                    for item in state.media_items:
                        if item.gcs_uris:
                            for uri in item.gcs_uris:
                                items_to_render.append({"uri": uri})
                        elif item.gcsuri:
                            items_to_render.append({"uri": item.gcsuri})

                    infinite_scroll_library(
                        key=f"infinite_scroll_{state.active_chooser_key}",
                        items=items_to_render,
                        has_more_items=state.has_more_items,
                        on_load_more=handle_load_more,
                        on_image_selected=handle_image_selected,
                    )
            with me.box(
                style=me.Style(
                    display="flex", justify_content="flex-end", margin=me.Margin(top=24)
                )
            ):
                me.button(
                    "Cancel",
                    on_click=lambda e: setattr(state, "show_dialog", False),
                    type="stroked",
                )
