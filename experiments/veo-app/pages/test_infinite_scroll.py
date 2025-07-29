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

import mesop as me

from components.library.events import LibrarySelectionChangeEvent
from components.library.infinite_scroll_chooser_button import (
    infinite_scroll_chooser_button,
)
from components.page_scaffold import page_frame, page_scaffold


@me.stateclass
class PageState:
    """Local component page state."""

    selected_gcs_uri: str = ""


@me.page(path="/test_infinite_scroll")
def test_infinite_scroll_page():
    """Test page for the infinite scroll library chooser."""
    state = me.state(PageState)

    def on_test_library_select(e: LibrarySelectionChangeEvent):
        """Select event."""
        print(
            f"Test Page: Received event: chooser_id={e.chooser_id}, gcs_uri={e.gcs_uri}",
        )
        state.selected_gcs_uri = e.gcs_uri.replace(
            "gs://",
            "https://storage.mtls.cloud.google.com/",
        )
        yield

    with page_scaffold():  # pylint: disable = E1129:not-context-manager
        with page_frame():  # pylint: disable = E1129:not-context-manager
            with me.box(
                style=me.Style(
                    padding=me.Padding.all(24),
                    display="flex",
                    flex_direction="column",
                    gap=16,
                ),
            ):
                me.text("Test Infinite Scroll Library Chooser", type="headline-5")

                me.divider()

                infinite_scroll_chooser_button(
                    key="infinite_chooser",
                    on_library_select=on_test_library_select,
                    button_label="Open Infinite Scroll Library",
                )

                if state.selected_gcs_uri:
                    with me.box(style=me.Style(margin=me.Margin(top=24))):
                        me.text("Selected Image:")
                        me.image(
                            src=state.selected_gcs_uri,
                            style=me.Style(width="300px", border_radius=8),
                        )
