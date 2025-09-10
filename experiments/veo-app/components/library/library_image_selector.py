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

from typing import Callable, List

import mesop as me

from common.metadata import MediaItem
from common.utils import gcs_uri_to_https_url
from components.library.events import LibrarySelectionChangeEvent


@me.component
def library_image_selector(
    on_select: Callable[[LibrarySelectionChangeEvent], None],
    media_items: List[MediaItem],
):
    """A component that displays a grid of recent images from the library."""

    def on_image_click(e: me.ClickEvent):
        """Handles the click event on an image in the grid."""
        print(f"Image Clicked. URI from key: {e.key}")
        yield from on_select(LibrarySelectionChangeEvent(gcs_uri=e.key))

    with me.box(
        style=me.Style(
            display="grid",
            grid_template_columns="repeat(auto-fill, minmax(150px, 1fr))",
            gap="16px",
        )
    ):
        if not media_items:
            me.text("No recent images found in the library.")
        else:
            for item in media_items:
                if item.gcs_uris:
                    for image_uri in item.gcs_uris:
                        with me.box(
                            on_click=on_image_click,
                            key=image_uri,
                            style=me.Style(cursor="pointer"),
                        ):
                            me.image(
                                src=gcs_uri_to_https_url(image_uri),
                                style=me.Style(
                                    width="100%",
                                    border_radius=8,
                                    object_fit="cover",
                                ),
                            )
                elif item.gcsuri:
                    with me.box(
                        on_click=on_image_click,
                        key=item.gcsuri,
                        style=me.Style(cursor="pointer"),
                    ):
                        me.image(
                            src=gcs_uri_to_https_url(item.gcsuri),
                            style=me.Style(
                                width="100%",
                                border_radius=8,
                                object_fit="cover",
                            ),
                        )