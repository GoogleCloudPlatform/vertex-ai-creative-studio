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
""" Veo 2 mesop ui page"""
import time

import mesop as me
import requests
from common.metadata import add_video_metadata
from common.storage import store_to_gcs
from common.utils import print_keys
from components.dialog import dialog, dialog_actions
from components.header import header
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)

from config.default import Default
from models.model_setup import VeoModelSetup
from models.veo import image_to_video, text_to_video
from pages.styles import _BOX_STYLE_CENTER_DISTRIBUTED

config = Default()

veo_model = VeoModelSetup.init()


@me.stateclass
class PageState:
    """Mesop Page State"""

    veo_prompt_input: str = ""
    veo_prompt_placeholder: str = ""
    veo_prompt_textarea_key: int = 0

    prompt: str
    original_prompt: str

    aspect_ratio: str = "16:9"
    video_length: int = 5

    # I2V reference Image
    reference_image_file: me.UploadedFile = None
    reference_image_file_key: int = 0
    reference_image_gcs: str
    reference_image_uri: str

    # Rewriter
    auto_enhance_prompt: bool = False

    rewriter_name: str

    is_loading: bool = False
    show_error_dialog: bool = False
    error_message: str = ""
    result_video: str
    timing: str


def veo_content(app_state: me.state):
    """Veo 2 Mesop Page"""
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Veo 2", "movie")

            # tricolumn
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=10,
                    height=250,
                )
            ):
                # Controls
                with me.box(
                    style=me.Style(
                        # flex_basis="450px",
                        flex_basis="max(480px, calc(60% - 48px))",
                        display="flex",
                        flex_direction="column",
                        align_items="stretch",
                        justify_content="space-between",
                        gap=10,
                    )
                ):
                    subtle_veo_input()
                    # me.box(style=me.Style(height=12))
                    # me.text("no video generated")

                    with me.box(
                        style=me.Style(display="flex", flex_basis="row", gap=5)
                    ):
                        me.select(
                            label="aspect",
                            appearance="outline",
                            options=[
                                me.SelectOption(label="16:9 widescreen", value="16:9"),
                                me.SelectOption(label="9:16 portrait", value="9:16"),
                            ],
                            value=state.aspect_ratio,
                            on_selection_change=on_selection_change_aspect,
                        )
                        me.select(
                            label="length",
                            options=[
                                me.SelectOption(label="5 seconds", value="5"),
                                me.SelectOption(label="6 seconds", value="6"),
                                me.SelectOption(label="7 seconds", value="7"),
                                me.SelectOption(label="8 seconds", value="8"),
                            ],
                            appearance="outline",
                            style=me.Style(),
                            value=f"{state.video_length}",
                            on_selection_change=on_selection_change_length,
                        )
                        me.checkbox(
                            label="auto-enhance prompt",
                            checked=state.auto_enhance_prompt,
                            on_change=on_change_auto_enhance_prompt,
                        )

                # Uploaded image
                with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                    me.text("Reference Image (optional)")

                    if state.reference_image_uri:
                        output_url = state.reference_image_uri
                        # output_url = f"https://storage.mtls.cloud.google.com/{state.reference_image_uri}"
                        # output_url = "https://storage.mtls.cloud.google.com/ghchinoy-genai-sa-assets-flat/edits/image (30).png"
                        print(f"displaying {output_url}")
                        me.image(
                            src=output_url,
                            style=me.Style(
                                height=150,
                                border_radius=12,
                            ),
                            key=str(state.reference_image_file_key),
                        )
                    else:
                        me.image(src=None, style=me.Style(height=200))

                    with me.box(
                        style=me.Style(display="flex", flex_direction="row", gap=5)
                    ):
                        # me.button(label="Upload", type="flat", disabled=True)
                        me.uploader(
                            label="Upload",
                            accepted_file_types=["image/jpeg", "image/png"],
                            on_upload=on_click_upload,
                            type="flat",
                            color="primary",
                            style=me.Style(font_weight="bold"),
                        )
                        me.button(
                            label="Clear", on_click=on_click_clear_reference_image
                        )

            me.box(style=me.Style(height=30))

            # Generated video
            with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                me.text("Generated Video")
                me.box(style=me.Style(height=8))
                with me.box(style=me.Style(height="100%")):
                    if state.is_loading:
                        me.progress_spinner()
                    elif state.result_video:
                        video_url = state.result_video.replace(
                            "gs://",
                            "https://storage.mtls.cloud.google.com/",
                        )
                        print(f"video_url: {video_url}")
                        me.video(src=video_url, style=me.Style(border_radius=6))
                        me.text(state.timing)

    with dialog(is_open=state.show_error_dialog):  # pylint: disable=not-context-manager
        # Content within the dialog box
        me.text(
            "Generation Error",
            type="headline-6",
            style=me.Style(color=me.theme_var("error")),
        )
        me.text(state.error_message, style=me.Style(margin=me.Margin(top=16)))
        # Use the dialog_actions component for the button
        with dialog_actions():  # pylint: disable=not-context-manager
            me.button("Close", on_click=on_close_error_dialog, type="flat")


def on_change_auto_enhance_prompt(e: me.CheckboxChangeEvent):
    """Toggle auto-enhance prompt"""
    state = me.state(PageState)
    state.auto_enhance_prompt = e.checked


def on_click_upload(e: me.UploadEvent):
    """Upload image to GCS"""
    state = me.state(PageState)
    state.reference_image_file = e.file
    contents = e.file.getvalue()
    destination_blob_name = store_to_gcs(
        "uploads", e.file.name, e.file.mime_type, contents
    )
    # gcs
    state.reference_image_gcs = f"gs://{destination_blob_name}"
    # url
    state.reference_image_uri = (
        f"https://storage.mtls.cloud.google.com/{destination_blob_name}"
    )
    # log
    print(
        f"{destination_blob_name} with contents len {len(contents)} of type {e.file.mime_type} uploaded to {config.GENMEDIA_BUCKET}."
    )


def on_click_clear_reference_image(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clear reference image"""
    state = me.state(PageState)
    state.reference_image_file = None
    state.reference_image_file_key += 1
    state.reference_image_uri = None
    state.reference_image_gcs = None
    state.is_loading = False


def on_selection_change_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video duration length in seconds based on user event"""
    state = me.state(PageState)
    state.video_length = int(e.value)


def on_selection_change_aspect(e: me.SelectSelectionChangeEvent):
    """Adjust aspect ratio based on user event."""
    state = me.state(PageState)
    state.aspect_ratio = e.value


def on_click_clear(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Clear prompt and video"""
    state = me.state(PageState)
    state.result_video = None
    state.prompt = None
    state.veo_prompt_input = None
    state.original_prompt = None
    state.veo_prompt_textarea_key += 1
    state.video_length = 5
    state.aspect_ratio = "16:9"
    state.is_loading = False
    state.auto_enhance_prompt = False
    yield


def on_click_veo(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Veo generate request handler"""
    state = me.state(PageState)
    state.is_loading = True
    state.show_error_dialog = False  # Reset error state before starting
    state.error_message = ""
    state.result_video = ""  # Clear previous result
    state.timing = ""  # Clear previous timing
    yield

    print(f"Lights, camera, action!:\n{state.veo_prompt_input}")

    aspect_ratio = state.aspect_ratio  # @param ["16:9", "9:16"]
    seed = 120
    sample_count = 1
    rewrite_prompt = state.auto_enhance_prompt
    if rewrite_prompt:
        print("Default auto-enhance prompt is ON")
    duration_seconds = state.video_length

    start_time = time.time()  # Record the starting time
    gcs_uri = ""
    current_error_message = ""

    try:
        if state.reference_image_gcs:
            print(f"I2V invoked. I see you have an image! {state.reference_image_gcs} ")
            op = image_to_video(
                state.veo_prompt_input,
                state.reference_image_gcs,
                seed,
                aspect_ratio,
                sample_count,
                f"gs://{config.VIDEO_BUCKET}",
                rewrite_prompt,
                duration_seconds,
            )
        else:
            print("T2V invoked.")
            op = text_to_video(
                state.veo_prompt_input,
                seed,
                aspect_ratio,
                sample_count,
                f"gs://{config.VIDEO_BUCKET}",
                rewrite_prompt,
                duration_seconds,
            )

        print(f"Operation result: {op}")

        # Check for explicit errors in response
        if op.get("done") and op.get("error"):
            current_error_message = op["error"].get("message", "Unknown API error")
            print(f"API Error Detected: {current_error_message}")
            # No GCS URI in this case
            gcs_uri = ""
        elif op.get("done") and op.get("response"):
            response_data = op["response"]
            print(f"Response: {response_data}")
            print_keys(op["response"])

            if response_data.get("raiMediaFilteredCount", 0) > 0 and response_data.get(
                "raiMediaFilteredReasons"
            ):
                # Extract the first reason provided
                filter_reason = response_data["raiMediaFilteredReasons"][0]
                current_error_message = f"Content Filtered: {filter_reason}"
                print(f"Filtering Detected: {current_error_message}")
                gcs_uri = ""  # No GCS URI if content was filtered

            else:
                # Extract GCS URI from different possible locations
                if (
                    "generatedSamples" in response_data
                    and response_data["generatedSamples"]
                ):
                    print(f"Generated Samples: {response_data["generatedSamples"]}")
                    gcs_uri = (
                        response_data["generatedSamples"][0]
                        .get("video", {})
                        .get("uri", "")
                    )
                elif "videos" in response_data and response_data["videos"]:
                    print(f"Videos: {response_data["videos"]}")
                    gcs_uri = response_data["videos"][0].get("gcsUri", "")

                if gcs_uri:
                    file_name = gcs_uri.split("/")[-1]
                    print("Video generated - use the following to copy locally")
                    print(f"gsutil cp {gcs_uri} {file_name}")
                    state.result_video = gcs_uri
                else:
                    # Success reported, but no video URI found - treat as an error/unexpected state
                    current_error_message = "API reported success but no video URI was found in the response."
                    print(f"Error: {current_error_message}")
                    state.result_video = ""  # Ensure no video is shown

        else:
            # Handle cases where 'done' is false or response structure is unexpected
            current_error_message = (
                "Unexpected API response structure or operation not done."
            )
            print(f"Error: {current_error_message}")
            state.result_video = ""

    # Catch specific exceptions you anticipate
    except ValueError as err:
        print(f"ValueError caught: {err}")
        current_error_message = f"Input Error: {err}"
    except requests.exceptions.HTTPError as err:
        print(f"HTTPError caught: {err}")
        current_error_message = f"Network/API Error: {err}"
    # Catch any other unexpected exceptions
    except Exception as err:
        print(f"Generic Exception caught: {type(err).__name__}: {err}")
        current_error_message = f"An unexpected error occurred: {err}"

    finally:
        end_time = time.time()  # Record the ending time
        execution_time = end_time - start_time  # Calculate the elapsed time
        print(f"Execution time: {execution_time} seconds")  # Print the execution time
        state.timing = f"Generation time: {round(execution_time)} seconds"

        #  If an error occurred, update the state to show the dialog
        if current_error_message:
            state.error_message = current_error_message
            state.show_error_dialog = True
            # Ensure no result video is displayed on error
            state.result_video = ""

        try:
            add_video_metadata(
                gcs_uri,
                state.veo_prompt_input,
                aspect_ratio,
                veo_model,
                execution_time,
                state.video_length,
                state.reference_image_gcs,
                rewrite_prompt,
                error_message=current_error_message,
                comment="veo2 default generation",
            )
        except Exception as meta_err:
            # Handle potential errors during metadata storage itself
            print(f"CRITICAL: Failed to store metadata: {meta_err}")
            # Optionally, display another error or log this critical failure
            if not state.show_error_dialog:  # Avoid overwriting primary error
                state.error_message = f"Failed to store video metadata: {meta_err}"
                state.show_error_dialog = True

    state.is_loading = False
    yield
    print("Cut! That's a wrap!")


def on_blur_veo_prompt(e: me.InputBlurEvent):
    """Veo prompt blur event"""
    me.state(PageState).veo_prompt_input = e.value


@me.component
def subtle_veo_input():
    """veo input"""

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
        with me.box(
            style=me.Style(
                flex_grow=1,
            )
        ):
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
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_veo_prompt,
                key=str(pagestate.veo_prompt_textarea_key),
                value=pagestate.veo_prompt_placeholder,
            )
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=15,
            )
        ):
            # do the veo
            with me.content_button(
                type="icon",
                on_click=on_click_veo,
            ):
                with me.box(style=icon_style):
                    me.icon("play_arrow")
                    me.text("Create")
            # invoke gemini
            with me.content_button(
                type="icon",
                disabled=True,
            ):
                with me.box(style=icon_style):
                    me.icon("auto_awesome")
                    me.text("Rewriter")
            # clear all of this
            with me.content_button(
                type="icon",
                on_click=on_click_clear,
            ):
                with me.box(style=icon_style):
                    me.icon("clear")
                    me.text("Clear")



def on_close_error_dialog(e: me.ClickEvent):
    """Handler to close the error dialog."""
    state = me.state(PageState)
    state.show_error_dialog = False
    yield  # Update UI to hide dialog
