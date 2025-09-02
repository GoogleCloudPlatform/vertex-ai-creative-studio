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

import time
from dataclasses import field

import mesop as me

from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from components.header import header
from components.image_thumbnail import image_thumbnail
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.snackbar import snackbar
from config.default import Default as cfg
from models.gemini import generate_image_from_prompt_and_images
from state.state import AppState


@me.stateclass
class PageState:
    """Gemini Image Generation Page State"""

    uploaded_image_gcs_uris: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    prompt: str = ""
    generated_image_urls: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    is_generating: bool = False
    generation_complete: bool = False
    generation_time: float = 0.0
    selected_image_url: str = ""
    show_snackbar: bool = False
    snackbar_message: str = ""
    previous_media_item_id: str | None = None  # For linking generation sequences


def gemini_image_gen_page_content():
    """UI for the Gemini Image Generation test page."""
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Gemini Image Generation", "image")

            with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                # Left column (controls)
                with me.box(
                    style=me.Style(
                        width=400,
                        background=me.theme_var("surface-container-lowest"),
                        padding=me.Padding.all(16),
                        border_radius=12,
                    ),
                ):
                    me.text(
                        "Upload Images and Provide a Prompt",
                        style=me.Style(
                            margin=me.Margin(bottom=16),
                        ),
                    )
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=16,
                            margin=me.Margin(bottom=16),
                            justify_content="center",
                        ),
                    ):
                        me.uploader(
                            label="Upload Images",
                            on_upload=on_upload,
                            multiple=True,
                            style=me.Style(width="100%"),
                        )
                        library_chooser_button(
                            on_library_select=on_library_select,
                            button_label="Choose from Library",
                        )
                    if state.uploaded_image_gcs_uris:
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_wrap="wrap",
                                gap=10,
                                justify_content="center",
                                margin=me.Margin(bottom=16),
                            ),
                        ):
                            for i, uri in enumerate(state.uploaded_image_gcs_uris):
                                image_thumbnail(
                                    image_uri=uri,
                                    index=i,
                                    on_remove=on_remove_image,
                                    icon_size=18,
                                )
                    me.textarea(
                        label="Prompt",
                        rows=3,
                        on_blur=on_prompt_blur,
                        value=state.prompt,
                        style=me.Style(width="100%", margin=me.Margin(bottom=16)),
                    )

                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            align_items="center",
                            gap=16,
                        )
                    ):
                        if state.is_generating:
                            with me.content_button(type="raised", disabled=True):
                                with me.box(
                                    style=me.Style(
                                        display="flex",
                                        flex_direction="row",
                                        align_items="center",
                                        gap=8,
                                    )
                                ):
                                    me.progress_spinner(diameter=20, stroke_width=3)
                                    me.text("Generating Images...")
                        else:
                            me.button(
                                "Generate Images",
                                on_click=generate_images,
                                type="raised",
                            )
                            with me.content_button(
                                on_click=on_clear_click, type="icon"
                            ):
                                me.icon("delete_sweep")

                        if state.generation_complete and state.generation_time > 0:
                            me.text(
                                f"{state.generation_time:.2f} seconds",
                                style=me.Style(font_size=12),
                            )

                    # Actions row
                    if state.generated_image_urls:
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="column",
                                gap=16,
                                margin=me.Margin(top=16),
                            )
                        ):
                            me.text("Actions", type="headline-5")
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_direction="row",
                                    align_items="center",
                                    gap=16,
                                )
                            ):
                                me.image(
                                    src=state.selected_image_url,
                                    style=me.Style(
                                        width=100,
                                        height=100,
                                        border_radius=8,
                                        object_fit="cover",
                                    ),
                                )
                                me.button(
                                    "Continue",
                                    on_click=on_continue_click,
                                    type="stroked",
                                )

                with me.box(style=me.Style(flex_grow=1)):
                    if state.generation_complete and not state.generated_image_urls:
                        me.text("No images returned.")
                    elif state.generated_image_urls:
                        if len(state.generated_image_urls) == 1:
                            # Display single, maximized image
                            me.image(
                                src=state.generated_image_urls[0],
                                style=me.Style(
                                    width="100%",
                                    max_height="85vh",
                                    object_fit="contain",
                                    border_radius=8,
                                ),
                            )
                        else:
                            # Display multiple images in a gallery view
                            with me.box(
                                style=me.Style(
                                    display="flex", flex_direction="column", gap=16
                                )
                            ):
                                # Main image
                                me.image(
                                    src=state.selected_image_url,
                                    style=me.Style(
                                        width="100%",
                                        max_height="75vh",
                                        object_fit="contain",
                                        border_radius=8,
                                    ),
                                )

                                # Thumbnail strip
                                with me.box(
                                    style=me.Style(
                                        display="flex",
                                        flex_direction="row",
                                        gap=16,
                                        justify_content="center",
                                    )
                                ):
                                    for url in state.generated_image_urls:
                                        is_selected = url == state.selected_image_url
                                        with me.box(
                                            key=url,
                                            on_click=on_thumbnail_click,
                                            style=me.Style(
                                                padding=me.Padding.all(4),
                                                border=me.Border.all(
                                                    me.BorderSide(
                                                        width=4,
                                                        style="solid",
                                                        color=me.theme_var("secondary")
                                                        if is_selected
                                                        else "transparent",
                                                    )
                                                ),
                                                border_radius=12,
                                                cursor="pointer",
                                            ),
                                        ):
                                            me.image(
                                                src=url,
                                                style=me.Style(
                                                    width=100,
                                                    height=100,
                                                    object_fit="cover",
                                                    border_radius=6,
                                                ),
                                            )
            snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)


def on_upload(e: me.UploadEvent):
    """Handle image uploads."""
    state = me.state(PageState)
    for file in e.files:
        gcs_url = store_to_gcs(
            "gemini_image_gen_references",
            file.name,
            file.mime_type,
            file.getvalue(),
        )
        state.uploaded_image_gcs_uris.append(gcs_url)
    yield


def on_library_select(e: LibrarySelectionChangeEvent):
    """Handle image selection from the library."""
    state = me.state(PageState)
    state.uploaded_image_gcs_uris.append(e.gcs_uri)
    yield


def on_remove_image(e: me.ClickEvent):
    """Handle remove image click."""
    state = me.state(PageState)
    del state.uploaded_image_gcs_uris[int(e.key)]
    yield


def on_prompt_blur(e: me.InputEvent):
    """Handle prompt input."""
    me.state(PageState).prompt = e.value


def on_thumbnail_click(e: me.ClickEvent):
    """Handle thumbnail click."""
    state = me.state(PageState)
    state.selected_image_url = e.key
    yield


def on_clear_click(e: me.ClickEvent):
    """Handle clear button click."""
    state = me.state(PageState)
    state.generated_image_urls = []
    state.prompt = ""
    state.uploaded_image_gcs_uris = []
    state.selected_image_url = ""
    state.generation_time = 0.0
    state.generation_complete = False
    state.previous_media_item_id = None  # Reset the chain
    yield


def on_continue_click(e: me.ClickEvent):
    """Handle continue button click."""
    state = me.state(PageState)
    # Convert the display URL back to a GCS URI
    gcs_uri = state.selected_image_url.replace(
        "https://storage.mtls.cloud.google.com/", "gs://"
    )

    # Clear the uploaded images and add the selected one
    state.uploaded_image_gcs_uris = [gcs_uri]

    # Clear the generated images and related state, and reset the chain
    state.generated_image_urls = []
    state.selected_image_url = ""
    state.generation_time = 0.0
    state.generation_complete = False
    state.previous_media_item_id = None  # Reset the chain
    yield


def show_snackbar(state: PageState, message: str):
    state.snackbar_message = message
    state.show_snackbar = True
    yield
    time.sleep(3)
    state.show_snackbar = False
    yield


def generate_images(e: me.ClickEvent):
    """Generate images and automatically save them to the library in a chain."""
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_generating = True
    state.generation_complete = False
    yield

    try:
        gcs_uris, execution_time = generate_image_from_prompt_and_images(
            prompt=state.prompt,
            images=state.uploaded_image_gcs_uris,
            gcs_folder="gemini_image_generations",
            file_prefix="gemini_image",
        )

        state.generation_time = execution_time

        if not gcs_uris:
            item = MediaItem(
                prompt=state.prompt,
                mime_type="image/png",
                user_email=app_state.user_email,
                source_images_gcs=state.uploaded_image_gcs_uris,
                comment="generated by gemini image generation",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
                related_media_item_id=state.previous_media_item_id,
                error_message="No images returned.",
                generation_time=execution_time,
            )
            add_media_item_to_firestore(item)
            state.previous_media_item_id = item.id  # Keep the chain
            show_snackbar(
                state,
                "No images were generated, but the attempt was logged to the library.",
            )
        else:
            state.generated_image_urls = [
                uri.replace("gs://", "https://storage.mtls.cloud.google.com/")
                for uri in gcs_uris
            ]
            if state.generated_image_urls:
                state.selected_image_url = state.generated_image_urls[0]

            # Automatically save to library
            item = MediaItem(
                gcs_uris=gcs_uris,
                prompt=state.prompt,
                mime_type="image/png",
                user_email=app_state.user_email,
                source_images_gcs=state.uploaded_image_gcs_uris,
                comment="generated by gemini image generation",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
                related_media_item_id=state.previous_media_item_id,
                generation_time=execution_time,
            )
            add_media_item_to_firestore(item)

            # Update state for the next link in the chain
            state.previous_media_item_id = item.id

            # Show feedback
            show_snackbar(state, "Automatically saved to library.")

    except Exception as ex:
        print(f"ERROR: Failed to generate images. Details: {ex}")
        show_snackbar(state, f"An error occurred: {ex}")

    finally:
        state.is_generating = False
        state.generation_complete = True
        yield


@me.page(path="/gemini_image_generation")
def page():
    gemini_image_gen_page_content()
