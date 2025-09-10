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

import json
import time
from dataclasses import field

import mesop as me

from common.analytics import log_ui_click, track_model_call
from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url, https_url_to_gcs_uri
from components.dialog import dialog
from components.header import header
from components.image_thumbnail import image_thumbnail
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.snackbar import snackbar
from components.svg_icon.svg_icon import svg_icon
from config.default import Default as cfg
from models.gemini import (
    generate_image_from_prompt_and_images,
    generate_transformation_prompts,
)
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
    num_images_to_generate: int = 1
    suggested_transformations: list[dict] = field(default_factory=list)  # pylint: disable=invalid-field-call

    info_dialog_open: bool = False


ACTION_PROMPTS = {
    "rotate_left": "Rotate the primary subject in the image to the left.",
    "rotate_right": "Rotate the primary subject in the image to the right.",
    "remove_background": "Remove the background from this image, replacing it with a solid white background.",
}

NUM_IMAGES_PROMPTS = {
    2: "Give me 2 options.",
    3: "Give me 3 options.",
    4: "Give me 4 options.",
}

with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    NANO_BANANA_INFO = next(
        (
            s
            for s in about_content["sections"]
            if s.get("id") == "gemini_image_generation"
        ),
        None,
    )


def gemini_image_gen_page_content():
    """Renders the main UI for the Gemini Image Generation page."""
    state = me.state(PageState)

    if state.info_dialog_open:
        with dialog(is_open=state.info_dialog_open):  # pylint: disable=not-context-manager
            me.text(f"About {NANO_BANANA_INFO['title']}", type="headline-6")
            me.markdown(NANO_BANANA_INFO["description"])
            me.divider()
            me.text("Current Settings", type="headline-6")
            with me.box(style=me.Style(margin=me.Margin(top=16))):
                me.button("Close", on_click=close_info_dialog, type="flat")

    with page_frame():  # pylint: disable=E1129
        header(
            "Gemini Image Generation",
            "spark",
            show_info_button=True,
            on_info_click=open_info_dialog,
        )

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
                    "Type a prompt or add images and a prompt",
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
                    max_rows=14,
                    autosize=True,
                    on_blur=on_prompt_blur,
                    value=state.prompt,
                    style=me.Style(width="100%", margin=me.Margin(bottom=16)),
                )

                me.select(
                    label="Number of Images",
                    options=[
                        me.SelectOption(label="1", value="1"),
                        me.SelectOption(label="2", value="2"),
                        me.SelectOption(label="3", value="3"),
                        me.SelectOption(label="4", value="4"),
                    ],
                    on_selection_change=on_num_images_change,
                    value=str(state.num_images_to_generate),
                    style=me.Style(width="100%", margin=me.Margin(bottom=16)),
                )

                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        align_items="center",
                        gap=16,
                    ),
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
                        with me.content_button(on_click=on_clear_click, type="icon"):
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
                            ),
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
                            with (
                                me.content_button(
                                    on_click=on_send_to_veo,
                                    # type="flat",
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

                # Image presets
                if state.generated_image_urls or state.uploaded_image_gcs_uris:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="column",
                            gap=16,
                            margin=me.Margin(top=16),
                        )
                    ):
                        me.text("Image Presets", style=me.Style(font_weight="bold"))
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="row",
                                align_items="center",
                                gap=16,
                            ),
                        ):
                            me.button(
                                "Rotate left",
                                on_click=on_image_action_click,
                                type="stroked",
                                key="rotate_left",
                            )
                            me.button(
                                "Rotate right",
                                on_click=on_image_action_click,
                                type="stroked",
                                key="rotate_right",
                            )
                            me.button(
                                "Remove background",
                                on_click=on_image_action_click,
                                type="stroked",
                                key="remove_background",
                            )

                # Suggested transformations
                if state.suggested_transformations:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=16,
                            margin=me.Margin(top=16),
                        )
                    ):
                        # me.text("Suggested Transformations", style=me.Style(font_weight="bold"))
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="column",
                                align_items="flex-start",
                                gap=8,
                            ),
                        ):
                            for transformation in state.suggested_transformations:
                                with me.content_button(
                                    on_click=on_transformation_click,
                                    key=json.dumps(transformation),
                                    type="stroked",
                                ):
                                    with me.box(
                                        style=me.Style(
                                            display="flex",
                                            flex_direction="row",
                                            align_items="center",
                                            gap=8,
                                        )
                                    ):
                                        svg_icon(icon_name="image_edit_auto")
                                        me.text(transformation["title"])

            # Right column (generated images)
            with me.box(
                style=me.Style(
                    flex_grow=1,
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    justify_content="center",
                    border_radius=12,
                    padding=me.Padding.all(16),
                    min_height=400,
                )
            ):
                if state.generation_complete and not state.generated_image_urls:
                    me.text("No images returned.")
                elif state.generated_image_urls:
                    # This box is to override the parent's centering styles
                    with me.box(
                        style=me.Style(
                            width="100%",
                            height="100%",
                            display="flex",
                            flex_direction="column",
                        )
                    ):
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
                else:
                    # Placeholder
                    with me.box(
                        style=me.Style(
                            opacity=0.2,
                            width=128,
                            height=128,
                            color=me.theme_var("on-surface-variant"),
                        )
                    ):
                        svg_icon(icon_name="banana")
        snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)


def on_upload(e: me.UploadEvent):
    """Handles file uploads, stores them in GCS, and updates the state."""
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
    """Appends a selected library image's GCS URI to the list of uploaded images."""
    state = me.state(PageState)
    state.uploaded_image_gcs_uris.append(e.gcs_uri)
    yield


def on_remove_image(e: me.ClickEvent):
    """Removes an image from the `uploaded_image_gcs_uris` list based on its index."""
    state = me.state(PageState)
    del state.uploaded_image_gcs_uris[int(e.key)]
    yield


def on_prompt_blur(e: me.InputEvent):
    """Updates the prompt in the page state when the input field loses focus."""
    me.state(PageState).prompt = e.value


def on_num_images_change(e: me.SelectSelectionChangeEvent):
    """Updates the number of images to generate in the page state."""
    me.state(PageState).num_images_to_generate = int(e.value)


def on_thumbnail_click(e: me.ClickEvent):
    """Sets the clicked thumbnail as the main selected image."""
    state = me.state(PageState)
    state.selected_image_url = e.key
    yield


def on_clear_click(e: me.ClickEvent):
    """Resets the entire page state to its initial values, clearing all inputs and outputs."""
    state = me.state(PageState)
    state.generated_image_urls = []
    state.prompt = ""
    state.uploaded_image_gcs_uris = []
    state.selected_image_url = ""
    state.generation_time = 0.0
    state.generation_complete = False
    state.previous_media_item_id = None  # Reset the chain
    state.num_images_to_generate = 1
    state.suggested_transformations = []
    yield


def on_transformation_click(e: me.ClickEvent):
    """Handles clicks on suggested transformation buttons."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    if not state.selected_image_url:
        yield from show_snackbar(state, "Please select an image to transform.")
        return

    try:
        transformation = json.loads(e.key)
        title = transformation["title"]
        prompt = transformation["prompt"]
    except (json.JSONDecodeError, KeyError):
        yield from show_snackbar(state, "Invalid transformation data.")
        return

    # Log the click event for analytics
    element_id = f"suggested_transformation_{title.replace(' ', '_').lower()}"
    log_ui_click(
        element_id=element_id,
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )

    input_gcs_uri = https_url_to_gcs_uri(state.selected_image_url)

    # The transformation uses the selected image as the sole input
    # and the button's key as the prompt.
    state.prompt = prompt  # Update the main prompt box for clarity
    yield from _generate_and_save(base_prompt=prompt, input_gcs_uris=[input_gcs_uri])


def on_image_action_click(e: me.ClickEvent):
    """Handles clicks on image action buttons, triggering a new generation."""
    state = me.state(PageState)
    input_gcs_uri = ""

    # Prioritize the selected generated image
    if state.selected_image_url:
        input_gcs_uri = https_url_to_gcs_uri(state.selected_image_url)
    # Fallback to the first uploaded image
    elif state.uploaded_image_gcs_uris:
        input_gcs_uri = state.uploaded_image_gcs_uris[0]
    # No image available
    else:
        yield from show_snackbar(state, "Please upload or select an image first.")
        return

    action_prompt = ACTION_PROMPTS.get(e.key)
    if not action_prompt:
        yield from show_snackbar(state, f"Unknown action: {e.key}")
        return

    # The action uses the identified image as the sole input
    yield from _generate_and_save(
        base_prompt=action_prompt, input_gcs_uris=[input_gcs_uri]
    )


def on_continue_click(e: me.ClickEvent):
    """Uses the currently selected generated image as the input for a subsequent generation."""
    state = me.state(PageState)
    if not state.selected_image_url:
        yield from show_snackbar(state, "Please select an image to continue with.")
        return

    gcs_uri = https_url_to_gcs_uri(state.selected_image_url)
    state.uploaded_image_gcs_uris = [gcs_uri]
    state.generated_image_urls = []
    state.selected_image_url = ""
    state.generation_time = 0.0
    state.generation_complete = False
    # Keep state.previous_media_item_id to maintain the chain
    yield


def show_snackbar(state: PageState, message: str):
    """Displays a snackbar message at the bottom of the page."""
    state.snackbar_message = message
    state.show_snackbar = True
    yield
    time.sleep(3)
    state.show_snackbar = False
    yield
    # The snackbar will be hidden on the next interaction.


def _get_appended_prompt(base_prompt: str, num_images: int) -> str:
    """Appends the number of images prompt to the base prompt."""
    suffix = NUM_IMAGES_PROMPTS.get(num_images)
    if not suffix:
        return base_prompt

    if not base_prompt:
        return suffix

    # Avoid double punctuation
    if base_prompt.endswith((".", "!", "?")):
        return f"{base_prompt} {suffix}"
    return f"{base_prompt}. {suffix}"


def _generate_and_save(base_prompt: str, input_gcs_uris: list[str]):
    """Core logic to generate images and save results to Firestore."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    # Clear previous suggestions before generating new ones
    state.suggested_transformations = []

    final_prompt = _get_appended_prompt(base_prompt, state.num_images_to_generate)

    state.is_generating = True
    state.generation_complete = False
    yield

    try:
        with track_model_call(
            model_name=cfg().GEMINI_IMAGE_GEN_MODEL,
            prompt_length=len(final_prompt),
            num_input_images=len(input_gcs_uris),
            num_images_generated=state.num_images_to_generate,
        ):
            gcs_uris, execution_time = generate_image_from_prompt_and_images(
                prompt=final_prompt,
                images=input_gcs_uris,
                gcs_folder="gemini_image_generations",
                file_prefix="gemini_image",
            )

        state.generation_time = execution_time

        if not gcs_uris:
            item = MediaItem(
                prompt=final_prompt,
                mime_type="image/png",
                user_email=app_state.user_email,
                source_images_gcs=input_gcs_uris,
                comment="generated by gemini image generation",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
                related_media_item_id=state.previous_media_item_id,
                error_message="No images returned.",
                generation_time=execution_time,
            )
            add_media_item_to_firestore(item)
            state.previous_media_item_id = item.id
            yield from show_snackbar(
                state,
                "No images were generated, but the attempt was logged to the library.",
            )
        else:
            state.generated_image_urls = [
                gcs_uri_to_https_url(uri) for uri in gcs_uris
            ]
            if state.generated_image_urls:
                state.selected_image_url = state.generated_image_urls[0]

            item = MediaItem(
                gcs_uris=gcs_uris,
                prompt=final_prompt,
                mime_type="image/png",
                user_email=app_state.user_email,
                source_images_gcs=input_gcs_uris,
                comment="generated by gemini image generation",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
                related_media_item_id=state.previous_media_item_id,
                generation_time=execution_time,
            )
            add_media_item_to_firestore(item)
            state.previous_media_item_id = item.id
            yield from show_snackbar(state, "Automatically saved to library.")

            # Generate transformation prompts
            try:
                raw_transformations = generate_transformation_prompts(
                    image_uris=[gcs_uris[0]]
                )
                # Convert Pydantic objects to dicts for state
                state.suggested_transformations = [
                    t.model_dump() for t in raw_transformations
                ]
            except Exception as e:
                print(f"Could not generate transformation prompts: {e}")
                state.suggested_transformations = []  # Clear any old ones

    except Exception as ex:
        print(f"ERROR: Failed to generate images. Details: {ex}")
        yield from show_snackbar(state, f"An error occurred: {ex}")

    finally:
        state.is_generating = False
        state.generation_complete = True
        yield


def generate_images(e: me.ClickEvent):
    """Event handler for the main 'Generate Images' button."""
    state = me.state(PageState)
    yield from _generate_and_save(
        base_prompt=state.prompt, input_gcs_uris=state.uploaded_image_gcs_uris
    )


def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = True
    yield


def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = False
    yield


def on_send_to_veo(e: me.ClickEvent):
    """Navigates to the Veo page with the selected image as a query parameter."""
    state = me.state(PageState)
    if not state.selected_image_url:
        yield from show_snackbar(state, "Please select an image to send.")
        return

    # Convert back to GCS URI to pass a clean identifier
    gcs_uri = https_url_to_gcs_uri(state.selected_image_url)

    me.navigate(
        url="/veo",
        query_params={"source_image_uri": gcs_uri, "veo_model": "3.0-fast"},
    )
    yield


@me.page(
    path="/gemini_image_generation",
    title="Gemini Image Generation - GenMedia Creative Studio",
)
def page():
    """Define the Mesop page route for Gemini Image Generation."""
    with page_scaffold(page_name="gemini_image_generation"):  # pylint: disable=E1129
        gemini_image_gen_page_content()