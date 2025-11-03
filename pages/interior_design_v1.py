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

"""Interior Design page."""

import datetime
from dataclasses import field
import json

import mesop as me

from common.analytics import log_ui_click, track_click

from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from components.header import header
from components.dialog import dialog
from components.info_dialog.info_dialog import info_dialog
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.veo_button.veo_button import veo_button
from config.default import Default as cfg
from models.gemini import (
    extract_room_names_from_image,
    generate_image_from_prompt_and_images,
)
from state.state import AppState

# Placeholder style for image dropzones
IMAGE_PLACEHOLDER_STYLE = me.Style(
    width=400,
    height=400,
    border=me.Border.all(
        me.BorderSide(width=2, style="dashed", color=me.theme_var("outline-variant")),
    ),
    border_radius=8,
    display="flex",
    align_items="center",
    justify_content="center",
    flex_direction="column",
    gap=8,
)


with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    INTERIOR_DESIGN_INFO = next(
        (
            s
            for s in about_content["sections"]
            if s.get("id") == "interior_design"
        ),
        None,
    )
    

@me.stateclass
class PageState:
    """State for the Interior Design page."""

    floor_plan_uri: str = ""
    generated_3d_view_uri: str = ""
    room_names: list[str] = field(default_factory=list)  # pylint: disable=E3701:invalid-field-call
    is_generating: bool = False
    error_message: str = ""
    zoomed_view_uri: str = ""
    is_generating_zoom: bool = False
    selected_room: str = ""
    generated_3d_view_media_id: str = ""
    design_prompt: str = ""
    is_designing: bool = False
    zoomed_view_media_id: str = ""
    design_image_uri: str = ""

    info_dialog_open: bool = False


@me.page(
    path="/interior_design_v1",
    title="Interior Design",
)
def interior_design_page():
    with page_scaffold(page_name="interior_design"):  # pylint: disable=E1129:not-context-manager
        with page_frame():  # pylint: disable=E1129:not-context-manager
            header("Interior Design", "chair", show_info_button=True, on_info_click=open_info_dialog)
            page_content()


def page_content():
    state = me.state(PageState)
    print(f"DEBUG: page_content rendering, state.info_dialog_open = {state.info_dialog_open}")
    
    info_dialog(
        is_open=state.info_dialog_open,
        info_data=INTERIOR_DESIGN_INFO,
        on_close=close_info_dialog,
        default_title="Interior Design",
    )

    with me.box(
        style=me.Style(
            display="flex", flex_direction="column", gap=24, align_items="center"
        )
    ):
        # Input and Output Area
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=32, justify_content="center"
            )
        ):
            # Input Floor Plan
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    gap=10,
                    align_items="center",
                )
            ):
                me.text("Floor Plan", type="headline-6")
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=8,
                        align_items="center",
                        min_height=48,
                    )
                ):
                    me.uploader(
                        label="Upload Floor Plan",
                        on_upload=on_upload_floor_plan,
                        accepted_file_types=["image/jpeg", "image/png", "image/webp"],
                        style=me.Style(width="100%"),
                    )
                    library_chooser_button(
                        key="floor_plan", on_library_select=on_select_floor_plan
                    )
                with me.box(style=IMAGE_PLACEHOLDER_STYLE):
                    if state.floor_plan_uri:
                        me.image(
                            src=gcs_uri_to_https_url(state.floor_plan_uri),
                            style=me.Style(
                                height="100%",
                                width="100%",
                                border_radius=8,
                                object_fit="contain",
                            ),
                        )
                    else:
                        me.icon("floorplan")
                        me.text("Add a floor plan")

            # Output 3D View
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    gap=10,
                    align_items="center",
                )
            ):
                me.text("Generated 3D View", type="headline-6")
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=8,
                        align_items="center",
                        min_height=48,
                    )
                ):
                    me.button(
                        "Generate 3D View",
                        on_click=on_generate_3d_view_click,
                        disabled=not state.floor_plan_uri or state.is_generating,
                        type="raised",
                    )
                with me.box(style=IMAGE_PLACEHOLDER_STYLE):
                    if state.is_generating:
                        me.progress_spinner()
                    elif state.generated_3d_view_uri:
                        me.image(
                            src=gcs_uri_to_https_url(state.generated_3d_view_uri),
                            style=me.Style(
                                height="100%",
                                width="100%",
                                border_radius=8,
                                object_fit="contain",
                            ),
                        )
                    else:
                        me.icon("view_in_ar")
                        me.text("Your 3D view will appear here")

        # Room Name Buttons - now in the main column
        if state.room_names:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    gap=10,
                )
            ):
                me.text("Identified Rooms", type="headline-6")
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=10,
                        flex_wrap="wrap",
                        justify_content="center",
                    )
                ):
                    for room in state.room_names:
                        with me.content_button(
                            key=room, on_click=on_room_button_click, type="stroked"
                        ):
                            if state.is_generating_zoom and state.selected_room == room:
                                me.progress_spinner(diameter=18)
                            else:
                                me.text(room)

        # Display the zoomed-in view and design controls
        if state.zoomed_view_uri:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=24,
                    margin=me.Margin(top=24),
                    width="100%",
                )
            ):
                # Left side: Image
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                        gap=10,
                        flex_grow=1,
                    )
                ):
                    me.text(f"Zoomed View: {state.selected_room}", type="headline-6")
                    me.image(
                        src=gcs_uri_to_https_url(state.zoomed_view_uri),
                        style=me.Style(
                            height="100%",
                            width="100%",
                            max_width="600px",
                            border_radius=8,
                            object_fit="contain",
                        ),
                    )
                # Right side: Controls
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="column", gap=16, width=300
                    )
                ):
                    me.text("Design Studio", type="headline-6")
                    me.uploader(
                        label="Upload Design Image",
                        on_upload=on_upload_design_image,
                        style=me.Style(width="100%"),
                        accepted_file_types=["image/jpeg", "image/png", "image/webp"],
                    )
                    library_chooser_button(
                        key="design_image_library_chooser",
                        on_library_select=on_select_design_image,
                        button_label="Add from Library",
                    )
                    if state.design_image_uri:
                        me.image(
                            src=gcs_uri_to_https_url(state.design_image_uri),
                            style=me.Style(width="100%", border_radius=8, margin=me.Margin(top=8)),
                        )
                    me.textarea(
                        label="Design Modifications",
                        on_blur=on_design_prompt_blur,
                        style=me.Style(width="100%"),
                    )
                    with me.box(style=me.Style(display="flex", flex_direction="row", gap=8)):
                        me.button("Clear", on_click=on_clear_design, type="stroked")
                        me.button(
                            "Design",
                            on_click=on_design_click,
                            type="raised",
                            disabled=state.is_designing,
                        )
                    veo_button(gcs_uri=state.zoomed_view_uri)
                    if state.is_designing:
                        me.progress_spinner()

        if state.error_message:
            me.text(state.error_message, style=me.Style(color="red"))


# --- Event Handlers ---


def on_upload_floor_plan(e: me.UploadEvent):
    """Upload floor plan handler."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="interior_design_upload_floor_plan",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
    state = me.state(PageState)
    # Assuming single file upload for simplicity
    file = e.files[0]
    gcs_url = store_to_gcs(
        "interior_design_uploads", file.name, file.mime_type, file.getvalue()
    )
    state.floor_plan_uri = gcs_url
    # Clear previous results when a new image is uploaded
    state.generated_3d_view_uri = ""
    state.room_names = []
    state.error_message = ""
    yield


def on_select_floor_plan(e: LibrarySelectionChangeEvent):
    """Floor plan selection from library handler."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="interior_design_select_floor_plan",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
    state = me.state(PageState)
    state.floor_plan_uri = e.gcs_uri
    # Clear previous results when a new image is selected
    state.generated_3d_view_uri = ""
    state.room_names = []
    state.error_message = ""
    yield


@track_click(element_id="interior_design_generate_3d_view_button")
def on_generate_3d_view_click(e: me.ClickEvent):
    """Handles the 3D view generation."""
    state = me.state(PageState)
    app_state = me.state(AppState)  # Need this for logging user email

    state.is_generating = True
    state.generated_3d_view_uri = ""
    state.room_names = []
    state.error_message = ""
    state.zoomed_view_uri = ""
    state.selected_room = ""
    yield

    try:
        prompt = "create a 3D version for the floor plan. make it realistic. keep the furnitures as per the floor plan and follow the measurement. retain the names of rooms in the appropriate location"

        # Call the existing Gemini model function
        gcs_uris, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=[state.floor_plan_uri],
            gcs_folder="interior_design_generations",
        )

        if gcs_uris:
            state.generated_3d_view_uri = gcs_uris[0]
            item_to_log = MediaItem(
                gcsuri=gcs_uris[0],
                gcs_uris=gcs_uris,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=prompt,
                source_images_gcs=[state.floor_plan_uri],
                mime_type="image/png",  # Assuming PNG output
                comment="Generated by Interior Design",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
            )
            # This function modifies item_to_log, adding the ID to it
            add_media_item_to_firestore(item_to_log)
            # Now we can safely access the ID
            state.generated_3d_view_media_id = item_to_log.id

            # Now, extract room names from the original floor plan
            try:
                room_names = extract_room_names_from_image(state.floor_plan_uri)
                state.room_names = room_names
            except Exception as room_ex:
                # Don't fail the whole operation, just log that room extraction failed
                print(f"Could not extract room names: {room_ex}")
                state.error_message = "Could not extract room names from floor plan."

        else:
            state.error_message = "Image generation failed to return a result."

    except Exception as ex:
        state.error_message = f"An error occurred during generation: {ex}"
    finally:
        state.is_generating = False
        yield


@track_click(element_id="interior_design_room_button")
def on_room_button_click(e: me.ClickEvent):
    """Handles the generation of a zoomed-in view for a specific room."""
    state = me.state(PageState)
    app_state = me.state(AppState)
    room_name = e.key

    state.is_generating_zoom = True
    state.selected_room = room_name
    state.zoomed_view_uri = ""
    state.error_message = ""
    yield

    try:
        prompt = f"Using the provided 3D rendering as a layout guide, create a photorealistic interior photograph. The photo should be from a first-person perspective, as if a person is standing in the hallway or adjacent room and looking through the doorway into the {room_name}. Capture the sense of entering the room for the first time on a house tour. Ensure the lighting and furniture placement are consistent with the 3D model."

        gcs_uris, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=[state.generated_3d_view_uri],  # Use the 3D view as input
            gcs_folder="interior_design_zoomed_views",
        )

        if gcs_uris:
            state.zoomed_view_uri = gcs_uris[0]
            item_to_log = MediaItem(
                gcsuri=gcs_uris[0],
                gcs_uris=gcs_uris,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=prompt,
                source_images_gcs=[state.generated_3d_view_uri],
                related_media_item_id=state.generated_3d_view_media_id,
                mime_type="image/png",
                comment=f"Zoomed view of {room_name}",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
            )
            # This function modifies item_to_log, adding the ID to it
            add_media_item_to_firestore(item_to_log)
            # Now we can safely access the ID for the next iteration
            state.zoomed_view_media_id = item_to_log.id
        else:
            state.error_message = "Zoomed view generation failed to return a result."

    except Exception as ex:
        state.error_message = f"An error occurred during zoom generation: {ex}"
    finally:
        state.is_generating_zoom = False
        state.selected_room = ""
        yield


def on_design_prompt_blur(e: me.InputBlurEvent):
    """Updates the design prompt in the page state."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="interior_design_design_prompt",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.design_prompt = e.value


def on_upload_design_image(e: me.UploadEvent):
    """Upload design image handler."""
    state = me.state(PageState)
    file = e.files[0]
    gcs_url = store_to_gcs(
        "interior_design_uploads", file.name, file.mime_type, file.getvalue()
    )
    state.design_image_uri = gcs_url
    yield


def on_select_design_image(e: LibrarySelectionChangeEvent):
    """Design image selection from library handler."""
    state = me.state(PageState)
    state.design_image_uri = e.gcs_uri
    yield


def on_clear_design(e: me.ClickEvent):
    """Clear design prompt and image."""
    state = me.state(PageState)
    state.design_prompt = ""
    state.design_image_uri = ""
    yield


@track_click(element_id="interior_design_design_button")
def on_design_click(e: me.ClickEvent):
    """Handles the iterative design generation."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    if not state.design_prompt:
        state.error_message = "Please enter a design modification prompt."
        yield
        return

    state.is_designing = True
    state.error_message = ""
    yield

    try:
        images = [state.zoomed_view_uri]
        if state.design_image_uri:
            images.append(state.design_image_uri)

        gcs_uris, _ = generate_image_from_prompt_and_images(
            prompt=state.design_prompt,
            images=images,  # Use the current zoomed view as input
            gcs_folder="interior_design_iterations",
        )

        if gcs_uris:
            # Update the zoomed view with the new image, creating the loop
            state.zoomed_view_uri = gcs_uris[0]

            # Log the new iteration to Firestore
            item_to_log = MediaItem(
                gcsuri=gcs_uris[0],
                gcs_uris=gcs_uris,
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=state.design_prompt,
                source_images_gcs=[state.zoomed_view_uri, state.design_image_uri],
                related_media_item_id=state.zoomed_view_media_id,
                mime_type="image/png",
                comment="Interior Design Iteration",
                model=cfg().GEMINI_IMAGE_GEN_MODEL,
            )
            # This function modifies item_to_log, adding the ID to it
            add_media_item_to_firestore(item_to_log)
            # Update the ID for the next iteration
            state.zoomed_view_media_id = item_to_log.id
            # Clear the prompt for the next input
            state.design_prompt = ""
            state.design_image_uri = ""
        else:
            state.error_message = "Design generation failed to return a result."

    except Exception as ex:
        state.error_message = f"An error occurred during design generation: {ex}"
    finally:
        state.is_designing = False
        yield

def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    print("DEBUG: open_info_dialog called")
    state = me.state(PageState)
    state.info_dialog_open = True
    yield


@track_click(element_id="interior_design_close_info_dialog_button")
def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = False
    yield