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

"""Veo and Me: A simplified R2V-focused page."""

import datetime
import time

import mesop as me

from common.error_handling import GenerationError
from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from components.veo.r2v_prompt_inputs import r2v_prompt_inputs
from components.veo.r2v_generation_controls import r2v_generation_controls
from components.veo.r2v_uploader import r2v_uploader
from components.veo.r2v_video_display import r2v_video_display
from config.veo_models import get_veo_model_config
from models.veo import APIReferenceImage, VideoGenerationRequest, generate_video
from state.state import AppState
from state.veo_and_me_state import PageState


@me.page(path="/veo_and_me", title="Veo & Me")
def veo_and_me_page():
    """Main Page."""
    with page_scaffold(page_name="veo_and_me"):
        veo_and_me_content()


# --- Dummy Handlers for Component Compatibility ---
def on_library_select(e: me.ClickEvent): pass
def on_click_rewrite(e: me.ClickEvent): pass

def on_selection_change_veo_model(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.veo_model = e.value
    yield
# ----------------------------------------------

def veo_and_me_content():
    """Renders the content for the Veo & Me page."""
    with page_frame():
        header("Veo & Me", "movie")

        with me.box(style=me.Style(display="flex", flex_direction="column", gap=20)):
            with me.box(style=me.Style(display="flex", flex_direction="row", gap=10)):
                # Left column: Prompt
                with me.box(
                    style=me.Style(
                        flex_basis="max(480px, calc(60% - 48px))",
                        display="flex",
                        flex_direction="column",
                        gap=10,
                    )
                ):
                    r2v_prompt_inputs(
                        on_click_generate=on_click_veo,
                        on_click_rewrite=on_click_rewrite,
                        on_click_clear=on_click_clear,
                        on_blur_prompt=on_blur_veo_prompt,
                        on_blur_negative_prompt=on_blur_negative_prompt,
                    )

                # Right column: R2V inputs using the new component
                r2v_uploader(
                    on_r2v_asset_add=on_r2v_asset_add,
                    on_r2v_asset_remove=on_r2v_asset_remove,
                    on_r2v_style_add=on_r2v_style_add,
                    on_r2v_style_remove=on_r2v_style_remove,
                    on_library_select=on_library_select,
                )

            # Use the new focused generation controls
            r2v_generation_controls(on_selection_change_veo_model=on_selection_change_veo_model)

        me.box(style=me.Style(height=50))

        r2v_video_display(on_thumbnail_click=on_thumbnail_click)


# --- Event Handlers ---

def on_blur_veo_prompt(e: me.InputBlurEvent):
    state = me.state(PageState)
    state.veo_prompt_input = e.value
    yield


def on_blur_negative_prompt(e: me.InputBlurEvent):
    state = me.state(PageState)
    state.negative_prompt = e.value
    yield


def on_click_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.result_videos = []
    state.selected_video_url = ""
    state.veo_prompt_input = "A cinematic shot of a [ASSET] driving a car."
    state.negative_prompt = ""
    state.is_loading = False
    state.r2v_reference_images = []
    state.r2v_reference_mime_types = []
    state.r2v_style_image = None
    state.r2v_style_image_mime_type = None
    yield


def on_r2v_asset_add(e: me.UploadEvent):
    state = me.state(PageState)
    if len(state.r2v_reference_images) >= 3:
        state.error_message = "You can upload a maximum of 3 asset images."
        state.show_error_dialog = True
        yield
        return
    try:
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        state.r2v_reference_images.append(gcs_path)
        state.r2v_reference_mime_types.append(e.file.mime_type)
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_r2v_asset_remove(e: me.ClickEvent):
    state = me.state(PageState)
    index_to_remove = int(e.key)
    if 0 <= index_to_remove < len(state.r2v_reference_images):
        state.r2v_reference_images.pop(index_to_remove)
        state.r2v_reference_mime_types.pop(index_to_remove)
    yield


def on_r2v_style_add(e: me.UploadEvent):
    state = me.state(PageState)
    try:
        gcs_path = store_to_gcs(
            "uploads", e.file.name, e.file.mime_type, e.file.getvalue()
        )
        state.r2v_style_image = gcs_path
        state.r2v_style_image_mime_type = e.file.mime_type
    except Exception as ex:
        state.error_message = f"Failed to upload image: {ex}"
        state.show_error_dialog = True
    yield


def on_r2v_style_remove(e: me.ClickEvent):
    state = me.state(PageState)
    state.r2v_style_image = None
    state.r2v_style_image_mime_type = None
    yield


def on_thumbnail_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.selected_video_url = e.key
    yield


def on_click_veo(e: me.ClickEvent):
    app_state = me.state(AppState)
    state = me.state(PageState)

    if not state.veo_prompt_input or not state.r2v_reference_images:
        state.error_message = "Prompt and at least one asset image are required."
        state.show_error_dialog = True
        yield
        return

    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_videos = []
    state.selected_video_url = ""
    state.timing = ""
    yield

    start_time = time.time()

    request = VideoGenerationRequest(
        prompt=state.veo_prompt_input,
        negative_prompt=state.negative_prompt,
        duration_seconds=state.video_length,
        video_count=state.video_count,
        aspect_ratio=state.aspect_ratio,
        resolution=state.resolution,
        enhance_prompt=state.auto_enhance_prompt,
        model_version_id=state.veo_model,
        person_generation=state.person_generation,
        r2v_references=[
            APIReferenceImage(gcs_uri=uri, mime_type=mime)
            for uri, mime in zip(
                state.r2v_reference_images, state.r2v_reference_mime_types
            )
        ],
        r2v_style_image=APIReferenceImage(
            gcs_uri=state.r2v_style_image, mime_type=state.r2v_style_image_mime_type
        )
        if state.r2v_style_image
        else None,
    )

    item_to_log = MediaItem(
        user_email=app_state.user_email,
        timestamp=datetime.datetime.now(datetime.UTC),
        prompt=request.prompt,
        model=get_veo_model_config(request.model_version_id).model_name,
        mime_type="video/mp4",
        mode=state.veo_mode,
        aspect=request.aspect_ratio,
        duration=float(request.duration_seconds),
        r2v_reference_images=state.r2v_reference_images,
        r2v_style_image=state.r2v_style_image,
        negative_prompt=request.negative_prompt,
    )

    try:
        gcs_uris, resolution = generate_video(request)
        state.result_videos = gcs_uris
        if gcs_uris:
            state.selected_video_url = gcs_uris[0]
        item_to_log.gcs_uris = gcs_uris
        item_to_log.gcsuri = gcs_uris[0] if gcs_uris else None
        item_to_log.resolution = resolution

    except GenerationError as ge:
        state.error_message = ge.message
        state.show_error_dialog = True
        item_to_log.error_message = ge.message
    except Exception as ex:
        state.error_message = f"An unexpected error occurred: {str(ex)}"
        state.show_error_dialog = True
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

    state.is_loading = False
    yield