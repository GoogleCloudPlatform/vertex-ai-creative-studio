# Copyright 2024 Google LLC
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
"""Veo mesop UI page."""

import datetime  # Required for timestamp
import time

import mesop as me

from common.analytics import track_model_call
from common.error_handling import GenerationError
from common.metadata import MediaItem, add_media_item_to_firestore  # Updated import
from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from components.dialog import dialog, dialog_actions
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.page_scaffold import page_frame, page_scaffold
from components.veo.file_uploader import file_uploader
from components.veo.generation_controls import generation_controls
from components.veo.video_display import video_display
from config.default import Default
from config.rewriters import VIDEO_REWRITER
from models.gemini import rewriter
from models.model_setup import VeoModelSetup
from models.veo import generate_video, VideoGenerationRequest
from state.state import AppState
from state.veo_state import PageState
from config.default import ABOUT_PAGE_CONTENT

config = Default()

veo_model = VeoModelSetup.init()


def on_veo_load(e: me.LoadEvent):
    """Handles page load events, including query parameters for deep linking."""
    state = me.state(PageState)
    source_image_uri = me.query_params.get("source_image_uri")
    veo_model_param = me.query_params.get("veo_model")

    if source_image_uri:
        # Set the image from the query parameter
        state.reference_image_gcs = source_image_uri
        state.reference_image_uri = gcs_uri_to_https_url(source_image_uri)
        # Switch to the Image-to-Video tab
        state.veo_mode = "i2v"
        # Provide a default prompt for a better user experience
        state.veo_prompt_input = "Animate this image with subtle motion."

    if veo_model_param:
        state.veo_model = veo_model_param

    yield


@me.page(
    path="/veo",
    title="Veo - GenMedia Creative Studio",
    on_load=on_veo_load,
)
def veo_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold(page_name="veo"):  # pylint: disable=not-context-manager
        veo_content(state)


def veo_content(app_state: me.state):
    """Veo Mesop Page."""
    state = me.state(PageState)

    if state.info_dialog_open:
        with dialog(is_open=state.info_dialog_open):  # pylint: disable=not-context-manager
            me.text("About Veo", type="headline-6")
            me.markdown(ABOUT_PAGE_CONTENT["sections"][1]["description"])
            me.divider()
            me.text("Current Settings", type="headline-6")
            me.text(f"Prompt: {state.veo_prompt_input}")
            me.text(f"Negative Prompt: {state.negative_prompt}")
            me.text(f"Model: {state.veo_model}")
            me.text(f"Duration: {state.video_length}s")
            me.text(f"Input Image: {state.reference_image_gcs}")
            with dialog_actions():  # pylint: disable=not-context-manager
                me.button("Close", on_click=close_info_dialog, type="flat")

    with page_frame():  # pylint: disable=not-context-manager
            header("Veo", "movie", show_info_button=True, on_info_click=open_info_dialog)

            with me.box(
                style=me.Style(display="flex", flex_direction="row", gap=10)
            ):
                with me.box(
                    style=me.Style(
                        flex_basis="max(480px, calc(60% - 48px))",
                        display="flex",
                        flex_direction="column",
                        align_items="stretch",
                        justify_content="space-between",
                        gap=10,
                    )
                ):
                    # Renders the action buttons (e.g. create, rewrite, clear)
                    subtle_veo_input()
                    with me.box(
                        style=me.Style(
                            border_radius=16,
                            padding=me.Padding.all(8),
                            background=me.theme_var("secondary-container"),
                            display="flex",
                            width="100%",
                        )
                    ):
                        with me.box(style=me.Style(flex_grow=1)):
                            me.native_textarea(
                                placeholder="Enter concepts to avoid (negative prompt)",
                                on_blur=on_blur_negative_prompt,
                                value=state.negative_prompt,
                                autosize=True,
                                min_rows=1,
                                max_rows=3,
                                style=me.Style(
                                    background="transparent",
                                    outline="none",
                                    width="100%",
                                    border=me.Border.all(me.BorderSide(style="none")),
                                    color=me.theme_var("foreground"),
                                ),
                            )

                    # Renders the generation quality controls (e.g., aspect ratio, length)
                    generation_controls()

                file_uploader(
                    on_upload_image, on_upload_last_image, on_veo_image_from_library,
                )

            me.box(style=me.Style(height=50))

            video_display()

    with dialog(is_open=state.show_error_dialog):  # pylint: disable=not-context-manager
        me.text(
            "Generation Error",
            type="headline-6",
            style=me.Style(color=me.theme_var("error")),
        )
        me.text(state.error_message, style=me.Style(margin=me.Margin(top=16)))
        with dialog_actions():  # pylint: disable=not-context-manager
            me.button("Close", on_click=on_close_error_dialog, type="flat")


def on_input_prompt(e: me.InputEvent):
    state = me.state(PageState)
    state.prompt = e.value
    yield

def on_blur_negative_prompt(e: me.InputBlurEvent):
    state = me.state(PageState)
    state.negative_prompt = e.value
    yield

def on_click_clear(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clear prompt and video."""
    state = me.state(PageState)
    state.result_video = None
    state.prompt = None
    state.negative_prompt = ""
    state.veo_prompt_input = None
    state.original_prompt = None
    state.veo_prompt_textarea_key += 1
    state.video_length = 5
    state.aspect_ratio = "16:9"
    state.is_loading = False
    state.auto_enhance_prompt = False
    state.veo_model = "2.0"
    state.reference_image_gcs = None
    state.reference_image_uri = None
    state.last_reference_image_gcs = None
    state.last_reference_image_uri = None
    yield


def on_click_custom_rewriter(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo custom rewriter."""
    state = me.state(PageState)
    # Ensure prompt input is not empty before rewriting
    if not state.veo_prompt_input:
        # Optionally, set an error message or simply do nothing
        print("Prompt is empty, skipping rewrite.")
        yield
        return
    rewritten_prompt = rewriter(state.veo_prompt_input, VIDEO_REWRITER)
    state.veo_prompt_input = rewritten_prompt
    state.veo_prompt_placeholder = rewritten_prompt
    yield


def on_click_veo(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo generate request handler."""
    app_state = me.state(AppState)
    state = me.state(PageState)

    if state.veo_mode == "t2v" and not state.veo_prompt_input:
        state.error_message = "Prompt cannot be empty for VEO generation."
        state.show_error_dialog = True
        yield
        return

    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_video = ""
    state.timing = ""
    yield

    start_time = time.time()

    request = VideoGenerationRequest(
        prompt=state.veo_prompt_input,
        negative_prompt=state.negative_prompt,
        duration_seconds=state.video_length,
        aspect_ratio=state.aspect_ratio,
        resolution=state.resolution,
        enhance_prompt=state.auto_enhance_prompt,
        model_version_id=state.veo_model,
        person_generation=state.person_generation,
        reference_image_gcs=state.reference_image_gcs,
        last_reference_image_gcs=state.last_reference_image_gcs,
        reference_image_mime_type=state.reference_image_mime_type,
        last_reference_image_mime_type=state.last_reference_image_mime_type,
    )

    item_to_log = MediaItem(
        user_email=app_state.user_email,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        prompt=request.prompt,
        original_prompt=(
            state.original_prompt if state.original_prompt else request.prompt
        ),
        model=(
            config.VEO_EXP_MODEL_ID
            if request.model_version_id == "3.0"
            else config.VEO_EXP_FAST_MODEL_ID
            if request.model_version_id == "3.0-fast"
            else config.VEO_MODEL_ID
        ),
        mime_type="video/mp4",
        aspect=request.aspect_ratio,
        duration=float(request.duration_seconds),
        reference_image=request.reference_image_gcs,
        last_reference_image=request.last_reference_image_gcs,
        negative_prompt=request.negative_prompt,
        enhanced_prompt_used=request.enhance_prompt,
        comment="veo default generation",
    )

    try:
        gcs_uri, resolution = generate_video(request)
        state.result_video = gcs_uri
        item_to_log.gcsuri = gcs_uri
        item_to_log.resolution = resolution

    except GenerationError as ge:
        state.error_message = ge.message
        state.show_error_dialog = True
        state.result_video = ""
        item_to_log.error_message = ge.message
    except Exception as ex:  # Catch any other unexpected error during generation
        state.error_message = (
            f"An unexpected error occurred during video generation: {str(ex)}"
        )
        state.show_error_dialog = True
        state.result_video = ""
        item_to_log.error_message = state.error_message

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        state.timing = f"Generation time: {round(execution_time)} seconds"
        item_to_log.generation_time = execution_time

        try:
            add_media_item_to_firestore(item_to_log)
        except Exception as meta_err:
            print(f"CRITICAL: Failed to store metadata: {meta_err}")
            # If dialog isn't already shown for a generation error, show for metadata error
            if not state.show_error_dialog:
                state.error_message = f"Failed to store video metadata: {meta_err}"
                state.show_error_dialog = True
            # else, the generation error message takes precedence

    state.is_loading = False
    yield


def on_blur_veo_prompt(e: me.InputBlurEvent):
    """Veo prompt blur event."""
    # It's generally better to update placeholder along with input,
    # or have a separate mechanism if they should diverge.
    state = me.state(PageState)
    state.veo_prompt_input = e.value
    # state.veo_prompt_placeholder = e.value # If placeholder should mirror input


@me.component
def subtle_veo_input():
    """Veo input component."""
    pagestate = me.state(PageState)

    icon_style = me.Style(
        display="flex",
        flex_direction="column",
        gap=3,
        font_size=10,
        align_items="center",
    )
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=me.theme_var("secondary-container"),
            display="flex",
            width="100%",
        )
    ):
        with me.box(style=me.Style(flex_grow=1)):
            me.native_textarea(
                autosize=True,
                min_rows=10,
                max_rows=13,
                placeholder="video creation instructions",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=me.theme_var("secondary-container"),
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(me.BorderSide(style="none")),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_veo_prompt,
                key=str(pagestate.veo_prompt_textarea_key),  # Ensure key is string
                value=pagestate.veo_prompt_input,  # Bind to veo_prompt_input
            )
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=15)):
            # do the veo
            with me.content_button(
                type="icon", on_click=on_click_veo, disabled=pagestate.is_loading
            ):
                with me.box(style=icon_style):
                    me.icon("play_arrow")
                    me.text("Create")
            # invoke gemini
            with me.content_button(
                type="icon",
                on_click=on_click_custom_rewriter,
                disabled=pagestate.is_loading,
            ):
                with me.box(style=icon_style):
                    me.icon("auto_awesome")
                    me.text("Rewriter")
            # clear all of this
            with me.content_button(
                type="icon", on_click=on_click_clear, disabled=pagestate.is_loading
            ):
                with me.box(style=icon_style):
                    me.icon("clear")
                    me.text("Clear")


def on_close_error_dialog(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handler to close the error dialog."""
    state = me.state(PageState)
    state.show_error_dialog = False
    yield

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


def on_upload_image(e: me.UploadEvent):
    """Upload image to GCS and update state."""
    state = me.state(PageState)
    try:
        # Store the uploaded file to GCS
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        # Update the state with the new image details
        state.reference_image_gcs = gcs_path
        state.reference_image_uri = gcs_uri_to_https_url(gcs_path)
        state.reference_image_mime_type = e.file.mime_type
        print(f"Image uploaded to {gcs_path} with mime type {e.file.mime_type}")
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_upload_last_image(e: me.UploadEvent):
    """Upload last image to GCS and update state."""
    state = me.state(PageState)
    try:
        # Store the uploaded file to GCS
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        # Update the state with the new image details
        state.last_reference_image_gcs = gcs_path
        state.last_reference_image_uri = gcs_uri_to_https_url(gcs_path)
        state.last_reference_image_mime_type = e.file.mime_type
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_veo_image_from_library(e: LibrarySelectionChangeEvent):
    """VEO image from library handler."""
    state = me.state(PageState)
    if (
        e.chooser_id == "i2v_library_chooser"
        or e.chooser_id == "first_frame_library_chooser"
    ):
        state.reference_image_gcs = e.gcs_uri
        state.reference_image_uri = gcs_uri_to_https_url(e.gcs_uri)
    elif e.chooser_id == "last_frame_library_chooser":
        state.last_reference_image_gcs = e.gcs_uri
        state.last_reference_image_uri = gcs_uri_to_https_url(e.gcs_uri)
    yield