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

from dataclasses import field

import mesop as me

from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button


@me.stateclass
class PageState:
    """Local component page state."""

    selected_gcs_uri_A: str = ""
    selected_gcs_uri_B: str = ""


@me.page(path="/test_uploader")
def test_uploader_page():
    """Test page for determining uploader component capabilities."""
    state = me.state(PageState)

    def on_test_library_select(e: LibrarySelectionChangeEvent):
        print(
            f"Test Uploader Page: Received event: chooser_id={e.chooser_id}, gcs_uri={e.gcs_uri}",
        )
        if e.chooser_id == "chooser_A":
            state.selected_gcs_uri_A = gcs_uri_to_https_url(e.gcs_uri)
        elif e.chooser_id == "chooser_B":
            state.selected_gcs_uri_B = gcs_uri_to_https_url(e.gcs_uri)
        yield

    with me.box(
        style=me.Style(
            padding=me.Padding.all(24), display="flex", flex_direction="column", gap=16,
        )
    ):
        me.text("Test Uploader Components", type="headline-5")

        me.divider()

        me.text("Example 5: Test Independent State with Keys")
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
            library_chooser_button(
                key="chooser_A",
                on_library_select=on_test_library_select,
                button_label="Chooser A",
            )
            library_chooser_button(
                key="chooser_B",
                on_library_select=on_test_library_select,
                button_label="Chooser B",
            )

        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=16, margin=me.Margin(top=24)
            )
        ):
            if state.selected_gcs_uri_A:
                with me.box():
                    me.text("Selected Image A:")
                    me.image(
                        src=state.selected_gcs_uri_A,
                        style=me.Style(width="300px", border_radius=8),
                    )
            if state.selected_gcs_uri_B:
                with me.box():
                    me.text("Selected Image B:")
                    me.image(
                        src=state.selected_gcs_uri_B,
                        style=me.Style(width="300px", border_radius=8),
                    )
