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

import base64
import uuid

import mesop as me

from common.metadata import add_media_item
from common.storage import store_to_gcs
from components.drawing.events import DoodleSaveEvent
from components.drawing.image_drawer import image_drawer
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.infinite_scroll_chooser_button import (
    infinite_scroll_chooser_button,
)
from components.page_scaffold import page_frame, page_scaffold
from state.state import AppState


@me.stateclass
class PageState:
    """Local page state."""

    selected_gcs_uri: str = ""
    pen_color: str = "#ff0000"
    pen_width: int = 4
    # Key to force re-render of the doodle component for clearing.
    doodle_key: int = 0
    # Key to force re-render of the doodle component for clearing.
    doodle_key: int = 0
    


@me.page(
    path="/doodle",
    security_policy=me.SecurityPolicy(
        allowed_script_srcs=["https://esm.sh"],
        dangerously_disable_trusted_types=True,
    ),
)
def doodle_page():
    """Doodle page."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    with page_scaffold():  # pylint: disable = E1129:not-context-manager
        with page_frame():  # pylint: disable = E1129:not-context-manager
            header("Doodle Pad", "edit")

            with me.box(
                style=me.Style(
                    padding=me.Padding.all(24),
                    display="flex",
                    flex_direction="column",
                    gap=16,
                ),
            ):
                me.text("Select an image to start doodling", type="headline-5")

                with me.box(style=me.Style(display="flex", gap=16, align_items="center")):
                    infinite_scroll_chooser_button(
                        key="doodle_library_select",
                        on_library_select=on_library_chooser_select,
                        button_label="Choose from Library",
                    )
                    if state.selected_gcs_uri:
                        me.button("Clear", on_click=on_clear_click, type="stroked")

                if state.selected_gcs_uri:
                    with me.box(key=str(state.doodle_key)):
                        image_drawer(
                            image_url=state.selected_gcs_uri,
                            pen_color=state.pen_color,
                            pen_width=state.pen_width,
                            on_save=on_doodle_save,
                        )
                    


def on_library_chooser_select(e: LibrarySelectionChangeEvent):
    """Image select event from infinite scroll chooser"""
    state = me.state(PageState)
    print(
        f"Received event: chooser_id={e.chooser_id}, gcs_uri={e.gcs_uri}",
    )
    state.selected_gcs_uri = e.gcs_uri
    yield


def on_clear_click(e: me.ClickEvent):
    """Triggers a re-render of the component to clear the canvas."""
    state = me.state(PageState)
    state.doodle_key += 1
    state.selected_gcs_uri = ""
    yield


def on_doodle_save(e: DoodleSaveEvent):
    """Receives the doodle data from the Lit component and saves it."""
    app_state = me.state(AppState)
    state = me.state(PageState)

    # Reset the trigger so it can be used again.
    state.get_save_data_trigger = False

    # Decode the Base64 data URL
    # The data URL is in the format: data:image/png;base64,<data>
    header, data = e.value["value"].split(",", 1)
    image_bytes = base64.b64decode(data)

    # Create a unique filename
    file_name = f"doodle_{uuid.uuid4()}.png"

    # Save to GCS
    gcs_uri = store_to_gcs(
        "doodles",
        file_name,
        "image/png",
        image_bytes,
        decode=False,
    )

    # Add to Firestore
    add_media_item(
        user_email=app_state.user_email,
        model="image_drawer",
        mime_type="image/png",
        gcs_uris=[gcs_uri],
        source_images_gcs=[state.selected_gcs_uri],
        comment="Doodle created from image.",
    )
    print(f"Saved doodle to GCS: {gcs_uri}")

    # Navigate to the library to see the new doodle
    # me.navigate("/library")
    yield
