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

from common.metadata import MediaItem, get_media_for_page_optimized
from components.dialog import dialog
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_image_selector import library_image_selector


@me.stateclass
class State:
    """Local mesop state for the library chooser button."""

    show_library_dialog: bool = False
    active_chooser_key: str = ""
    is_loading: bool = False
    media_items: list[MediaItem] = field(default_factory=list)  # pylint: disable=E3701


@me.component
def library_chooser_button(
    on_library_select: Callable[[LibrarySelectionChangeEvent], None],
    button_label: Optional[str] = None,
    button_type: str = "stroked",
    key: str = "",
):
    """Render a button that opens a dialog to select an image from the library."""
    state = me.state(State)

    def open_dialog(e: me.ClickEvent):
        """Dedicated click handler for opening the dialog and fetching data."""
        print(f"CLICK on library_chooser_button with key: '{e.key}'")
        state.active_chooser_key = e.key
        state.show_library_dialog = True
        state.is_loading = True
        yield

        # Fetch fresh data every time the dialog is opened
        items, _ = get_media_for_page_optimized(20, ["images"])
        state.media_items = items
        state.is_loading = False
        yield

    def on_select_from_library(e: LibrarySelectionChangeEvent):
        """Callback to handle image selection from the library dialog."""
        e.chooser_id = state.active_chooser_key
        yield from on_library_select(e)
        state.show_library_dialog = False
        yield

    with me.content_button(on_click=open_dialog, type=button_type, key=key):
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=8,
                align_items="center",
            )
        ):
            me.icon("photo_library")
            if button_label:
                me.text(button_label)

    dialog_style = me.Style(
        width="65vw",
        height="35vh",
        display="flex",
        flex_direction="column",
    )

    with dialog(is_open=state.show_library_dialog, dialog_style=dialog_style):  # pylint: disable=E1129
        with me.box(
            style=me.Style(display="flex", flex_direction="column", gap=16, flex_grow=1)
        ):
            me.text("Select an Image from Library", type="headline-6")
            with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
                if state.is_loading:
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
                    library_image_selector(
                        on_select=on_select_from_library,
                        media_items=state.media_items,
                    )
            with me.box(
                style=me.Style(
                    display="flex", justify_content="flex-end", margin=me.Margin(top=24)
                )
            ):
                me.button(
                    "Cancel",
                    on_click=lambda e: setattr(state, "show_library_dialog", False),
                    type="stroked",
                )
