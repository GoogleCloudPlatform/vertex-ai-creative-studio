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
"""Motion portraits"""

import time
from dataclasses import field

import mesop as me
import requests
from common.metadata import add_video_metadata
from common.storage import store_to_gcs
from common.utils import print_keys
from components.header import header
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from google.genai import types
from google.genai.types import (
    GenerateContentConfig,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.default import Default
from models.model_setup import GeminiModelSetup, VeoModelSetup
from models.veo import image_to_video
from pages.styles import (
    _BOX_STYLE_CENTER_DISTRIBUTED,
    _BOX_STYLE_CENTER_DISTRIBUTED_MARGIN,
)

client, model_id = GeminiModelSetup.init()
MODEL_ID = model_id

config = Default()
veo_model = VeoModelSetup.init()


@me.stateclass
class PageState:
    """Local Page State"""

    is_loading: bool = False
    show_error_dialog: bool = False
    error_message: str = ""
    result_video: str = ""
    timing: str = ""

    aspect_ratio: str = "16:9"
    video_length: int = 5
    auto_enhance_prompt: bool = False

    generated_scene_direction: str = ""

    # I2V reference Image
    reference_image_file: me.UploadedFile = None
    reference_image_file_key: int = 0
    reference_image_gcs: str = ""
    reference_image_uri: str = ""
    reference_image_mime_type: str = ""

    # Style modifiers
    modifier_array: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    modifier_selected_states: dict[str, bool] = field(default_factory=dict)  # pylint: disable=invalid-field-call


modifier_options = [
    {"label": "motion", "key": "motion"},
    {"label": "distracted", "key": "distracted"},
    {"label": "artistic", "key": "artistic_style"},
    {"label": "close-up", "key": "close_up_shot"},
]


def motion_portraits_content(app_state: me.state):
    """Motion portraits Mesop Page"""

    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Motion Portraits", "portrait")

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=20,
                )
            ):
                # Uploaded image
                with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                    me.text("Portrait")

                    if state.reference_image_uri:
                        output_url = state.reference_image_uri
                        print(f"Displaying reference image: {output_url}")
                        me.image(
                            src=output_url,
                            style=me.Style(
                                height=200, border_radius=12, object_fit="contain"
                            ),
                            key=str(state.reference_image_file_key),
                        )
                    else:
                        # me.image(src=None, style=me.Style(height=200))
                        me.box(
                            style=me.Style(
                                height=200,
                                width=200,
                                display="flex",
                                align_items="center",
                                justify_content="center",
                                background=me.theme_var(
                                    "sys-color-surface-container-highest"
                                ),
                                border_radius=12,
                                border=me.Border.all(
                                    me.BorderSide(
                                        color=me.theme_var("sys-color-outline")
                                    )
                                ),
                            )
                        )

                    # uploader controls
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=10,
                            margin=me.Margin(top=10),
                        )
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
                            label="Clear",
                            on_click=on_click_clear_reference_image,
                        )

                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="column",
                        gap=15,
                        padding=me.Padding.all(12),
                        flex_grow=1,
                    )
                ):
                    me.text(
                        "Video options",
                        style=me.Style(font_size="1.1em", font_weight="bold"),
                    )
                    with me.box(
                        style=me.Style(display="flex", flex_direction="row", gap=5)
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

                    me.text(
                        "Style options",
                        style=me.Style(font_size="1.1em", font_weight="bold"),
                    )
                    with me.box(
                        style=me.Style(display="flex", flex_direction="row", gap=5)
                    ):
                        for option in modifier_options:
                            is_selected = option["key"] in state.modifier_array

                            # Use me.content_button. We'll place an icon and text inside.
                            with me.content_button(
                                key=f"mod_btn_{option['key']}",
                                # key=option["key"],  # Crucial for identifying the button in the event handler
                                on_click=on_modifier_click,
                                # Optional: Add some styling to make the buttons look more like selectable items
                                style=me.Style(
                                    padding=me.Padding.symmetric(
                                        vertical=8, horizontal=16
                                    ),
                                    border=me.Border.all(
                                        me.BorderSide(
                                            width=1,
                                            color=me.theme_var("sys-color-primary")
                                            if is_selected
                                            else me.theme_var("sys-color-outline"),
                                        )
                                    ),
                                    background=me.theme_var(
                                        "sys-color-primary-container"
                                    )
                                    if is_selected
                                    else "transparent",
                                    border_radius=20,  # Makes it more chip-like
                                ),
                            ):
                                # Use a horizontal box to arrange icon and text
                                with me.box(
                                    style=me.Style(
                                        display="flex",
                                        flex_direction="row",
                                        align_items="center",
                                        gap=6,  # Space between icon and text
                                    )
                                ):
                                    if is_selected:
                                        # Display a check icon when selected
                                        me.icon(
                                            "check",
                                            style=me.Style(
                                                color=me.theme_var(
                                                    "sys-color-on-primary-container"
                                                )
                                                if is_selected
                                                else me.theme_var(
                                                    "sys-color-on-surface"
                                                )
                                            ),
                                        )
                                    # else:
                                    # Optionally, a placeholder or different icon for unselected state
                                    # For now, no icon when not selected.
                                    # me.icon("add_circle_outline", style=me.Style(color=me.theme_var("sys-color-on-surface-variant")))

                                    # The label for the modifier
                                    me.text(
                                        option["label"],
                                        style=me.Style(
                                            color=me.theme_var(
                                                "sys-color-on-primary-container"
                                            )
                                            if is_selected
                                            else me.theme_var("sys-color-on-surface")
                                        ),
                                    )
                    if state.modifier_array:
                        me.text(
                            f"Active Modifiers: {', '.join(state.modifier_array)}",
                            style=me.Style(margin=me.Margin(top=10), font_size="0.9em"),
                        )

            with me.box(
                style=me.Style(
                    padding=me.Padding.all(16),
                    justify_content="center",
                    display="flex",
                )
            ):
                with me.content_button(
                    on_click=on_click_motion_portraits,
                    type="flat",
                    key="generate_motion_portrait_button",
                    disabled=state.is_loading or not state.reference_image_uri,
                ):
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            align_items="center",
                            gap=2,
                        )
                    ):
                        if state.is_loading:
                            me.progress_spinner(diameter=20, stroke_width=3)
                            me.text("Generating...")
                        else:
                            me.icon("portrait")
                            me.text("Create Moving Portrait")

                me.box(style=me.Style(height=24))

            # Generated video and prompt section
            if (
                state.is_loading
                or state.result_video
                or state.error_message
                or state.generated_scene_direction
            ):
                with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED_MARGIN):
                    if state.is_loading:
                        me.text(
                            "Generating your moving portrait, please wait...",
                            style=me.Style(
                                font_size="1.1em", margin=me.Margin(bottom=10)
                            ),
                        )
                        me.progress_spinner(diameter=40)
                    elif state.result_video:
                        me.text(
                            "Motion Portrait",
                            style=me.Style(
                                font_size="1.2em",
                                font_weight="bold",
                                margin=me.Margin(bottom=10),
                            ),
                        )
                        video_url = state.result_video.replace(
                            "gs://", "https://storage.mtls.cloud.google.com/"
                        )
                        print(f"Displaying result video: {video_url}")
                        me.video(
                            src=video_url,
                            style=me.Style(
                                width="100%",
                                max_width="480px"
                                if state.aspect_ratio == "9:16"
                                else "720px",
                                border_radius=12,
                                margin=me.Margin(top=8),
                            ),
                            # autoplay=True,
                            # controls=True
                        )
                        if state.timing:
                            me.text(
                                state.timing,
                                style=me.Style(
                                    margin=me.Margin(top=10), font_size="0.9em"
                                ),
                            )

                    # Display generated scene direction
                    if state.generated_scene_direction and not state.is_loading:
                        me.text(
                            "Generated Scene Direction:",
                            style=me.Style(
                                font_size="1.1em",
                                font_weight="bold",
                                margin=me.Margin(top=15, bottom=5),
                            ),
                        )
                        me.text(
                            state.generated_scene_direction,
                            style=me.Style(
                                white_space="pre-wrap",
                                font_family="monospace",
                                background=me.theme_var("sys-color-surface-container"),
                                padding=me.Padding.all(10),
                                border_radius=8,
                            ),
                        )

                    # Display error message if any
                    if (
                        state.show_error_dialog
                        and state.error_message
                        and not state.is_loading
                    ):
                        me.text(
                            "Error",
                            style=me.Style(
                                font_size="1.2em",
                                font_weight="bold",
                                color="red",
                                margin=me.Margin(top=15, bottom=5),
                            ),
                        )
                        me.text(
                            state.error_message,
                            style=me.Style(color="red", white_space="pre-wrap"),
                        )

            # # Generated video
            # with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
            #     me.text("Generated Video")
            #     me.box(style=me.Style(height=8))
            #     with me.box(style=me.Style(height="100%")):
            #         if state.is_loading:
            #             me.progress_spinner()
            #         elif state.result_video:
            #             fit_style = me.Style(
            #                 height="90%",
            #                 border_radius=6,
            #             )
            #             if state.aspect_ratio == "9:16":
            #                 fit_style = me.Style(
            #                     width="50%",
            #                     border_radius=6,
            #                 )
            #             print(f"state.aspect_ratio: {state.aspect_ratio}")
            #             video_url = state.result_video.replace(
            #                 "gs://",
            #                 "https://storage.mtls.cloud.google.com/",
            #             )
            #             print(f"video_url: {video_url}")
            #             me.video(src=video_url, style=fit_style)
            #             me.text(state.timing)


_BOX_STYLE = me.Style(
    flex_basis="max(480px, calc(50% - 48px))",
    # background="#fff",
    background=me.theme_var("background"),
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
)


def on_modifier_click(e: me.ClickEvent):
    """Handles click events for modifier content_buttons."""
    state = me.state(PageState)
    # modifier_key = e.key  # The key of the content_button that was clicked
    modifier_key = e.key.split("mod_btn_")[-1]  # Extract original key

    if not modifier_key:
        print("Error: ClickEvent has no key associated with the content_button.")
        return

    # Toggle the presence of the modifier_key in the modifier_array
    if modifier_key in state.modifier_array:
        # If already selected, remove it (deselect)
        new_modifier_array = [
            mod for mod in state.modifier_array if mod != modifier_key
        ]
        state.modifier_array = new_modifier_array
    else:
        # If not selected, add it (select)
        state.modifier_array = [*state.modifier_array, modifier_key]


def on_change_auto_enhance_prompt(e: me.CheckboxChangeEvent):
    """Toggle auto-enhance prompt"""
    state = me.state(PageState)
    state.auto_enhance_prompt = e.checked


def on_selection_change_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video duration length in seconds based on user event"""
    state = me.state(PageState)
    state.video_length = int(e.value)


def on_selection_change_aspect(e: me.SelectSelectionChangeEvent):
    """Adjust aspect ratio based on user event."""
    state = me.state(PageState)
    state.aspect_ratio = e.value


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
    print("clearing ...")
    state = me.state(PageState)
    state.reference_image_file = None
    state.reference_image_file_key += 1
    state.reference_image_uri = ""
    state.reference_image_gcs = ""
    state.reference_image_mime_type = ""
    state.result_video = ""
    state.timing = ""
    state.generated_scene_direction = ""  # Clear generated scene direction
    state.video_length = 5
    state.aspect_ratio = "16:9"
    state.auto_enhance_prompt = False
    state.modifier_array = []
    state.modifier_selected_states = {}
    state.is_loading = False
    state.show_error_dialog = False
    state.error_message = ""
    yield


def on_click_motion_portraits(e: me.ClickEvent):
    """Create the motion portrait"""
    state = me.state(PageState)

    if not state.reference_image_gcs:
        print("No reference image uploaded or GCS URI is missing.")
        state.error_message = "Please upload a reference image first."
        state.show_error_dialog = True
        state.is_loading = False
        yield
        return

    state.is_loading = True
    state.show_error_dialog = False
    state.error_message = ""
    state.result_video = ""
    state.timing = ""
    state.generated_scene_direction = ""
    yield

    # get scene direction
    base_prompt = f"""Scene direction for a motion portrait for an approximately {state.video_length} second scene.

Expand the given direction to include more facial engagement, as if the subject is looking out of the image and interested in the world outside.

Examine the picture provided to improve the scene direction.

Optionally, include is waving of hands and if necessary, and physical motion outside the frame.

Do not describe the frame. There should be no lip movement like speaking, but there can be descriptions of facial movements such as laughter, either in joy or cruelty."""

    final_prompt_for_llm = base_prompt
    if state.modifier_array:
        modifiers_string = ", ".join(state.modifier_array)
        final_prompt_for_llm += (
            f"\n\nUtilize the following modifiers for the subject: {modifiers_string}."
        )

    final_prompt_for_llm += "\n\nScene direction:\n"  # Guide for the LLM

    try:
        print(
            f"Generating scene direction for {state.reference_image_gcs} with prompt:\n{final_prompt_for_llm}"
        )
        # The scene_direction returned here is what we'll use for the video model
        scene_direction_for_video = generate_scene_direction(
            final_prompt_for_llm,
            state.reference_image_gcs,
            state.reference_image_mime_type,
        )
        state.generated_scene_direction = (
            scene_direction_for_video  # Store the generated direction
        )
        print(f"Generated Scene Direction (for video):\n{scene_direction_for_video}")
        yield

        print("Lights, camera, action!")

        aspect_ratio = state.aspect_ratio  # @param ["16:9", "9:16"]
        seed = 120
        sample_count = 1
        rewrite_prompt = state.auto_enhance_prompt
        if rewrite_prompt:
            print("Default auto-enhance prompt is ON")
        duration_seconds = state.video_length

        # invoke i2v
        start_time = time.time()  # Record the starting time
        gcs_uri = ""
        current_error_message = ""

        print(f"I2V invoked. I see you have an image! {state.reference_image_gcs} ")

        op = image_to_video(
            # state.veo_prompt_input,
            scene_direction_for_video,
            state.reference_image_gcs,
            seed,
            aspect_ratio,
            sample_count,
            f"gs://{config.VIDEO_BUCKET}",
            rewrite_prompt,
            duration_seconds,
        )
        print(f"I2V Operation result: {op}")
        print_keys(op)  # Useful for debugging response structure

        # Check for explicit errors in response
        if op.get("done"):
            if op.get("error"):
                current_error_message = op["error"].get(
                    "message", "Unknown API error during video generation."
                )
                print(f"API Error Detected: {current_error_message}")
            elif op.get("response"):
                response_data = op["response"]
                print(f"Response: {response_data}")
                print_keys(op["response"])
                if response_data.get(
                    "raiMediaFilteredCount", 0
                ) > 0 and response_data.get("raiMediaFilteredReasons"):
                    # Extract the first reason provided
                    filter_reason = response_data["raiMediaFilteredReasons"][0]
                    current_error_message = f"Content Filtered: {filter_reason}"
                    print(f"Filtering Detected: {current_error_message}")
                elif response_data.get("generatedSamples") and response_data[
                    "generatedSamples"
                ][0].get("video", {}).get("uri"):
                    gcs_uri = response_data["generatedSamples"][0]["video"]["uri"]
                elif response_data.get("videos") and response_data["videos"][0].get(
                    "gcsUri"
                ):
                    gcs_uri = response_data["videos"][0]["gcsUri"]
                else:
                    current_error_message = (
                        "API reported success but no video URI was found."
                    )
                # else:
                #     # Extract GCS URI from different possible locations
                #     if (
                #         "generatedSamples" in response_data
                #         and response_data["generatedSamples"]
                #     ):
                #         print(f"Generated Samples: {response_data["generatedSamples"]}")
                #         gcs_uri = (
                #             response_data["generatedSamples"][0]
                #             .get("video", {})
                #             .get("uri", "")
                #         )
                #     elif "videos" in response_data and response_data["videos"]:
                #         print(f"Videos: {response_data["videos"]}")
                #         gcs_uri = response_data["videos"][0].get("gcsUri", "")

                if gcs_uri:  # if GCS URI, set to state
                    state.result_video = gcs_uri
                    file_name = gcs_uri.split("/")[-1]
                    print(
                        f"Video generated: {gcs_uri}. To copy: gsutil cp {gcs_uri} {file_name}"
                    )
                elif not current_error_message:
                    current_error_message = "API reported success but no video URI was found in the response."
            else:
                # Success reported, but no video URI found - treat as an error/unexpected state
                current_error_message = (
                    "API operation completed but returned no error or response data."
                )

        else:
            # Handle cases where 'done' is false or response structure is unexpected
            current_error_message = "Video generation operation did not complete or returned an unexpected status. API response structure or operation not done."
        end_time = time.time()
        execution_time = end_time - start_time
        state.timing = f"Generation time: {round(execution_time)} seconds"

        if current_error_message:
            state.error_message = current_error_message
            state.show_error_dialog = True
            state.result_video = ""

        if gcs_uri and not current_error_message:
            try:
                add_video_metadata(
                    gcs_uri,
                    scene_direction_for_video,
                    aspect_ratio,
                    veo_model,
                    execution_time,
                    state.video_length,
                    state.reference_image_gcs,
                    rewrite_prompt,
                    error_message="",
                    comment="motion portrait",
                )
            except Exception as meta_err:
                print(f"CRITICAL: Failed to store metadata: {meta_err}")
                additional_meta_error = f" (Metadata storage failed: {meta_err})"
                state.error_message = (
                    state.error_message or "Video generated but metadata failed."
                ) + additional_meta_error
                state.show_error_dialog = True
        elif not gcs_uri and not current_error_message:
            state.error_message = (
                state.error_message
                or "Video generation completed without error, but no video was produced."
            )
            state.show_error_dialog = True

    except Exception as err:
        print(
            f"Exception during motion portrait generation: {type(err).__name__}: {err}"
        )
        state.error_message = f"An unexpected error occurred: {err}"
        state.show_error_dialog = True
        state.result_video = ""
    finally:
        state.is_loading = False
        yield
        print("Motion portrait generation process finished.")
    print("Cut! That's a wrap!")


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate_scene_direction(
    prompt: str, reference_image_gcs: str, image_mime_type: str
) -> str:
    """Generate scene direction with Gemini."""
    print(
        f"Generating scene direction. Prompt length: {len(prompt)}, Image GCS: {reference_image_gcs}, MIME: {image_mime_type}"
    )
    if not reference_image_gcs:
        raise ValueError(
            "Reference image GCS URI cannot be empty for scene direction generation."
        )
    if not image_mime_type:  # Ensure mime_type is provided
        print(
            "Warning: image_mime_type is empty, defaulting to image/png. This might cause issues."
        )
        image_mime_type = "image/png"

    try:
        contents = types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=reference_image_gcs,
                    mime_type=image_mime_type,
                ),
                types.Part.from_text(text=prompt),
            ],
        )
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=GenerateContentConfig(),  # Simpler config
        )

        # Robust response text extraction
        if hasattr(response, "text") and response.text:
            print(
                f"Scene direction generated successfully (from .text): {response.text[:100]}..."
            )
            return response.text
        elif (
            response.candidates
            and response.candidates[0].content.parts
            and response.candidates[0].content.parts[0].text
        ):
            text_response = response.candidates[0].content.parts[0].text
            print(
                f"Scene direction generated successfully (from candidates): {text_response[:100]}..."
            )
            return text_response
        else:
            print(f"Unexpected response structure from Gemini: {response}")
            raise ValueError(
                "Failed to extract text from Gemini response for scene direction."
            )

    except Exception as e:
        print(f"Error in generate_scene_direction: {type(e).__name__} - {e}")
        raise
