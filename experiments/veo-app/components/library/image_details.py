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

# pyright: basic

"""A component for displaying media item details, including a carousel."""

import os
from typing import Callable

import mesop as me

from common.metadata import MediaItem
from components.download_button.download_button import download_button


@me.stateclass
class CarouselState:
    """State for the image carousel."""

    current_index: int = 0
    current_index_gcsuri: str


def on_next(e: me.ClickEvent) -> None:
    """Event handler for the 'Next' button in the image carousel.

    Args:
        e: The Mesop click event.
    """
    state = me.state(CarouselState)
    state.current_index += 1


def on_prev(e: me.ClickEvent) -> None:
    """Event handler for the 'Previous' button in the image carousel.

    Args:
        e: The Mesop click event.
    """
    state = me.state(CarouselState)
    state.current_index -= 1


def on_send_to_veo(e: me.ClickEvent):
    """Navigates to the Veo page with the selected image as a query parameter."""
    state = me.state(CarouselState)

    # Convert back to GCS URI to pass a clean identifier
    gcs_uri = state.current_index_gcsuri.replace(
        "https://storage.mtls.cloud.google.com/", "gs://"
    )

    me.navigate(
        url="/veo",
        query_params={"source_image_uri": gcs_uri, "veo_model": "3.0-fast"},
    )
    yield


@me.component
def image_details(item: MediaItem, on_click_permalink: Callable) -> None:
    """A component that displays image details in a carousel.

    Args:
        item: The MediaItem to display.
    """
    state = me.state(CarouselState)

    # Handle case where there are no images to display.
    if not item.gcs_uris:
        me.text("Image data not available for this item.")
        return

    num_images = len(item.gcs_uris)

    # Defensively reset index if it's out of bounds. This can happen if the
    # component is re-rendered with a new item that has fewer images.
    if state.current_index >= num_images:
        state.current_index = 0

    with me.box(
        style=me.Style(
            display="flex", flex_direction="column", align_items="center", gap=16
        )
    ):
        # Image display
        image_url = item.gcs_uris[state.current_index].replace(
            "gs://", "https://storage.mtls.cloud.google.com/"
        )
        me.image(
            src=image_url,
            style=me.Style(
                width="100%",
                height="auto",
                border_radius="8px",
            ),
        )

        # Carousel controls - only show if there is more than one image.
        if num_images > 1:
            with me.box(
                style=me.Style(
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    gap=16,
                )
            ):
                me.button(
                    "Back",
                    on_click=on_prev,
                    disabled=state.current_index == 0,
                )
                me.text(f"{state.current_index + 1} / {num_images}")
                me.button(
                    "Next",
                    on_click=on_next,
                    disabled=state.current_index >= num_images - 1,
                )

    if item.rewritten_prompt:
        me.text(f'Rewritten Prompt: "{item.rewritten_prompt}"')
    else:
        me.text(f"Prompt: '{item.prompt or 'N/A'}'")
    if item.negative_prompt:
        me.text(f"Negative Prompt: '{item.negative_prompt}'")
    if item.critique:
        me.text(f"Critique: {item.critique}")

    # Conditionally display VTO input images
    if item.raw_data and "virtual-try-on" in item.raw_data.get("model", ""):
        with me.box(style=me.Style(margin=me.Margin(top=16))):
            me.text(
                "Input Images",
                style=me.Style(font_weight="bold", margin=me.Margin(bottom=8)),
            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=16,
                    justify_content="center",
                )
            ):
                # Person Image
                person_gcs_uri = item.raw_data.get("person_image_gcs")
                if person_gcs_uri:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                            gap=4,
                        )
                    ):
                        me.text("Person Image")
                        person_url = person_gcs_uri.replace(
                            "gs://", "https://storage.mtls.cloud.google.com/"
                        )
                        me.image(
                            src=person_url,
                            style=me.Style(
                                width="200px", height="auto", border_radius="8px"
                            ),
                        )

                # Product Image
                product_gcs_uri = item.raw_data.get("product_image_gcs")
                if product_gcs_uri:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                            gap=4,
                        )
                    ):
                        me.text("Product Image")
                        product_url = product_gcs_uri.replace(
                            "gs://", "https://storage.mtls.cloud.google.com/"
                        )
                        me.image(
                            src=product_url,
                            style=me.Style(
                                width="200px", height="auto", border_radius="8px"
                            ),
                        )
    if item.comment == "product recontext":
        with me.box(style=me.Style(margin=me.Margin(top=16))):
            me.text(
                "Source Images",
                style=me.Style(font_weight="bold", margin=me.Margin(bottom=8)),
            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=16,
                    justify_content="center",
                )
            ):
                for uri in item.source_images_gcs:
                    me.image(
                        src=uri.replace(
                            "gs://", "https://storage.mtls.cloud.google.com/"
                        ),
                        style=me.Style(
                            width="100px", height="auto", border_radius="8px"
                        ),
                    )
    with me.box(
        style=me.Style(
            display="flex", flex_direction="row", gap=10, margin=me.Margin(top=16)
        )
    ):
        with me.content_button(
            on_click=on_click_permalink,
            key=item.id or "",  # Ensure key is not None
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    align_items="center",
                    gap=5,
                )
            ):
                me.icon(icon="link")
                me.text("permalink")

        if image_url:
            gcs_uri = item.gcs_uris[state.current_index]
            state.current_index_gcsuri = gcs_uri
            filename = os.path.basename(gcs_uri.split("?")[0])
            download_button(url=gcs_uri, filename=filename)
            with (
                me.content_button(
                    on_click=on_send_to_veo,
                ),
                me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        align_items="center",
                        gap=8,
                    )
                ),
            ):
                me.icon("slideshow")
                me.text("Veo")
