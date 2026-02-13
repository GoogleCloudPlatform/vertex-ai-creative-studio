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

import json
import time
import base64
import uuid
from dataclasses import field

import mesop as me
from google.genai import types
from google.genai.types import GenerateContentConfig
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.analytics import log_ui_click, track_click
from common.metadata import MediaItem, add_media_item_to_firestore
from common.storage import store_to_gcs
from common.utils import create_display_url
from components.dialog import dialog
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from components.selfie_camera.selfie_camera import selfie_camera
from config.default import ABOUT_PAGE_CONTENT, Default
from models.model_setup import GeminiModelSetup, VeoModelSetup
from models.veo import VideoGenerationRequest, generate_video
from models.video_processing import convert_mp4_to_gif
from pages.styles import (
    _BOX_STYLE_CENTER_DISTRIBUTED,
    _BOX_STYLE_CENTER_DISTRIBUTED_MARGIN,
)
from state.state import AppState

client = GeminiModelSetup.init()


config = Default()
veo_model_name = VeoModelSetup.init()


with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    MOTION_PORTRAITS_INFO = next(
        (s for s in about_content["sections"] if s.get("id") == "motion_portraits"), None
    )

@me.stateclass
class PageState:
    """Local Page State"""

    is_loading: bool = False
    show_error_dialog: bool = False
    error_message: str = ""
    result_video_gcs_uri: str = ""
    result_video_display_url: str = ""
    timing: str = ""

    aspect_ratio: str = "16:9"
    video_length: int = 8
    auto_enhance_prompt: bool = False

    generated_scene_direction: str = ""
    
    gif_gcs_uri: str = ""
    gif_display_url: str = ""
    is_converting_gif: bool = False

    veo_model: str = "3.1-fast"
    veo_prompt_input: str = ""

    # I2V reference Image
    reference_image_file: me.UploadedFile = None
    reference_image_file_key: int = 0
    reference_image_gcs: str = ""
    reference_image_display_url: str = ""
    reference_image_mime_type: str = ""

    # Style modifiers
    modifier_array: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    modifier_selected_states: dict[str, bool] = field(default_factory=dict)  # pylint: disable=invalid-field-call

    info_dialog_open: bool = False
    show_selfie_dialog: bool = False


from config.portrait_styles import PORTRAIT_STYLES
from config.veo_models import VEO_MODELS, get_veo_model_config


@me.page(path="/motion_portraits", title="Motion Portraits - GenMedia Creative Studio")
def motion_portraits_page():
    """Implement the Motion Portraits page."""
    state = me.state(AppState)
    with page_scaffold(page_name="motion_portraits"):  # pylint: disable=not-context-manager
        motion_portraits_content(state)


def motion_portraits_content(app_state: me.state):
    """Implement the Motion Portraits Mesop Page content."""
    state = me.state(PageState)
    selfie_dialog()

    state = me.state(PageState)
    # Get current model config
    selected_model_config = get_veo_model_config(state.veo_model)

    # Ensure video length is valid for the selected model (e.g. initial load)
    if selected_model_config.supported_durations:
        if state.video_length not in selected_model_config.supported_durations:
            state.video_length = selected_model_config.default_duration
    elif not (
        selected_model_config.min_duration
        <= state.video_length
        <= selected_model_config.max_duration
    ):
        state.video_length = selected_model_config.default_duration

    # Generate dynamic options
    aspect_ratio_options = [
        me.SelectOption(label=ratio, value=ratio)
        for ratio in selected_model_config.supported_aspect_ratios
    ]
    video_length_options = [
        me.SelectOption(label=f"{i} seconds", value=str(i))
        for i in (selected_model_config.supported_durations or range(selected_model_config.min_duration, selected_model_config.max_duration + 1))
    ]
    auto_enhance_disabled = not selected_model_config.supports_prompt_enhancement

    if state.info_dialog_open:
        with dialog(is_open=state.info_dialog_open):  # pylint: disable=not-context-manager
            me.text(f'About {MOTION_PORTRAITS_INFO["title"]}', type="headline-6")
            me.markdown(MOTION_PORTRAITS_INFO["description"])
            me.divider()
            me.text("Current Settings", type="headline-6")
            me.text(f"Veo Model: {state.veo_model}")
            me.text(f"Prompt used: {state.veo_prompt_input}")
            with me.box(style=me.Style(margin=me.Margin(top=16))):
                me.button("Close", on_click=close_info_dialog, type="flat")

    with page_frame():  # pylint: disable=not-context-manager
            header(
                "Motion Portraits",
                "portrait",
                show_info_button=True,
                on_info_click=open_info_dialog,
            )

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

                    if state.reference_image_display_url:
                        output_url = state.reference_image_display_url
                        print(f"Displaying reference image: {output_url}")
                        me.image(
                            src=output_url,
                            style=me.Style(
                                height=200, border_radius=12, object_fit="contain"
                            ),
                            key=str(state.reference_image_file_key),
                        )
                    else:
                        me.box(
                            style=me.Style(
                                height=200,
                                width=200,
                                display="flex",
                                align_items="center",
                                justify_content="center",
                                background=me.theme_var(
                                    "sys-color-surface-container-highest",
                                ),
                                border_radius=12,
                                border=me.Border.all(
                                    me.BorderSide(
                                        color=me.theme_var("sys-color-outline"),
                                    ),
                                ),
                            ),
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
                        me.uploader(
                            label="Upload",
                            accepted_file_types=["image/jpeg", "image/png"],
                            on_upload=on_click_upload,
                            type="flat",
                            color="primary",
                            style=me.Style(font_weight="bold"),
                        )
                        library_chooser_button(
                            on_library_select=on_portrait_image_from_library,
                            button_type="icon",
                            key="portrait_library_chooser",
                        )
                        with me.content_button(type="icon", on_click=on_open_selfie_dialog):
                            me.icon("camera_alt")
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
                            label="model",
                            appearance="outline",
                            options=[
                                me.SelectOption(
                                    label=model.display_name, value=model.version_id
                                )
                                for model in VEO_MODELS
                            ],
                            value=state.veo_model,
                            on_selection_change=on_model_selection_change,
                        )
                        me.select(
                            label="aspect",
                            appearance="outline",
                            options=aspect_ratio_options,
                            value=state.aspect_ratio,
                            on_selection_change=on_selection_change_aspect,
                        )
                        me.select(
                            label="length",
                            options=video_length_options,
                            appearance="outline",
                            style=me.Style(),
                            value=f"{state.video_length}",
                            on_selection_change=on_selection_change_length,
                        )
                        me.checkbox(
                            label="auto-enhance prompt",
                            checked=state.auto_enhance_prompt,
                            on_change=on_change_auto_enhance_prompt,
                            disabled=auto_enhance_disabled,
                        )

                    me.text(
                        "Style options",
                        style=me.Style(font_size="1.1em", font_weight="bold"),
                    )
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=10,
                            flex_wrap="wrap",
                        )
                    ):
                        for style in PORTRAIT_STYLES:
                            num_selected = len(state.modifier_array)
                            is_selected = style.id in state.modifier_array
                            is_disabled = num_selected >= 2 and not is_selected

                            # Define styles based on state
                            if is_disabled:
                                button_style = me.Style(
                                    padding=me.Padding.symmetric(
                                        vertical=8, horizontal=16
                                    ),
                                    border_radius=20,
                                    border=me.Border.all(
                                        me.BorderSide(
                                            color=me.theme_var(
                                                "sys-color-outline-variant"
                                            )
                                        )
                                    ),
                                    background=me.theme_var(
                                        "sys-color-surface-container"
                                    ),
                                )
                                text_color = me.theme_var(
                                    "sys-color-on-surface-variant"
                                )
                            elif is_selected:
                                button_style = me.Style(
                                    padding=me.Padding.symmetric(
                                        vertical=8, horizontal=16
                                    ),
                                    border_radius=20,
                                    border=me.Border.all(
                                        me.BorderSide(
                                            width=1,
                                            color=me.theme_var("sys-color-primary"),
                                        )
                                    ),
                                    background=me.theme_var(
                                        "sys-color-primary-container"
                                    ),
                                )
                                text_color = me.theme_var(
                                    "sys-color-on-primary-container"
                                )
                            else:  # Default
                                button_style = me.Style(
                                    padding=me.Padding.symmetric(
                                        vertical=8, horizontal=16
                                    ),
                                    border_radius=20,
                                    border=me.Border.all(
                                        me.BorderSide(
                                            width=1,
                                            color=me.theme_var("sys-color-outline"),
                                        )
                                    ),
                                    background="transparent",
                                )
                                text_color = me.theme_var("sys-color-on-surface")

                            with me.content_button(
                                key=f"mod_btn_{style.id}",
                                on_click=on_modifier_click,
                                disabled=is_disabled,
                                style=button_style,
                            ):
                                with me.box(
                                    style=me.Style(
                                        display="flex",
                                        flex_direction="row",
                                        align_items="center",
                                        gap=6,
                                    )
                                ):
                                    if is_selected:
                                        me.icon(
                                            "check", style=me.Style(color=text_color)
                                        )
                                    me.text(
                                        style.label, style=me.Style(color=text_color)
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
                    disabled=state.is_loading or not state.reference_image_display_url,
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

            if (
                state.is_loading
                or state.result_video_display_url
                or state.error_message
                or state.generated_scene_direction
            ):
                with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED_MARGIN):
                    if state.is_loading:
                        state.gif_display_url = ""
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="column",
                                justify_content="center",  # Horizontal center
                                align_items="center",  # Vertical center
                                height=350,  # Give it a height to center within
                                width="100%",
                            )
                        ):
                            me.text(
                                "Generating your moving portrait, please wait...",
                                style=me.Style(
                                    font_size="1.1em",
                                    margin=me.Margin(bottom=16),
                                ),
                            )
                            me.progress_spinner(diameter=40)
                    elif state.result_video_display_url:
                        me.text(
                            "Motion Portrait",
                            style=me.Style(
                                font_size="1.2em",
                                font_weight="bold",
                                margin=me.Margin(bottom=10),
                            ),
                        )
                        video_url = state.result_video_display_url
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
                        )
                        if state.timing:
                            me.text(
                                state.timing,
                                style=me.Style(
                                    margin=me.Margin(top=10), font_size="0.9em"
                                ),
                            )
                            
                        me.button("Convert to GIF", key=state.result_video_gcs_uri, on_click=on_convert_to_gif_click, disabled=state.is_converting_gif)
                        
                        if state.is_converting_gif:
                            with me.box(style=me.Style(display="flex", justify_content="center")):
                                me.progress_spinner()
                                
                        
                    if state.gif_display_url:
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="column",
                                align_items="center",
                                gap=10,
                            )
                        ):
                            me.text("Video as GIF:", type="headline-5")
                            me.image(
                                src=state.gif_display_url,
                                style=me.Style(width="100%", max_width="480px", border_radius=8),
                            )

                    if state.generated_scene_direction and not state.is_loading:
                        with me.expansion_panel(title="Generated Scene Direction"):
                        #     me.text(state.character_description)
                        # me.text(
                        #     "Generated Scene Direction:",
                        #     style=me.Style(
                        #         font_size="1.1em",
                        #         font_weight="bold",
                        #         margin=me.Margin(top=15, bottom=5),
                        #     ),
                        # )
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


def on_convert_to_gif_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_converting_gif = True
    yield

    try:
        print(f"Converting {e.key} to GIF ...")
        # e.key is the GCS URI, convert it to a proxy URL for display
        gif_gcs_uri = convert_mp4_to_gif(e.key, user_email=app_state.user_email)
        state.gif_gcs_uri = gif_gcs_uri
        state.gif_display_url = create_display_url(gif_gcs_uri)
    finally:
        state.is_converting_gif = False
        yield

@track_click(element_id="portraits_clear_button")
def on_click_clear_reference_image(e: me.ClickEvent):
    """Clear reference image"""
    print("clearing ...")
    state = me.state(PageState)
    state.reference_image_file = None
    state.reference_image_file_key += 1
    state.reference_image_display_url = ""
    state.reference_image_gcs = ""
    state.reference_image_mime_type = ""
    state.result_video_gcs_uri = ""
    state.result_video_display_url = ""
    state.timing = ""
    state.generated_scene_direction = ""
    state.video_length = 5
    state.aspect_ratio = "16:9"
    state.auto_enhance_prompt = False
    state.modifier_array = []
    state.modifier_selected_states = {}
    state.is_loading = False
    state.show_error_dialog = False
    state.error_message = ""
    state.gif_gcs_uri = ""
    state.gif_display_url = ""
    yield


def on_model_selection_change(e: me.SelectSelectionChangeEvent):
    """Handles model selection change."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_model_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.veo_model = e.value

    selected_model_config = get_veo_model_config(state.veo_model)

    # Validate aspect ratio
    if state.aspect_ratio not in selected_model_config.supported_aspect_ratios:
        state.aspect_ratio = selected_model_config.supported_aspect_ratios[0]

    # Validate video length
    if selected_model_config.supported_durations:
        if state.video_length not in selected_model_config.supported_durations:
            state.video_length = selected_model_config.default_duration
    elif not (
        selected_model_config.min_duration
        <= state.video_length
        <= selected_model_config.max_duration
    ):
        state.video_length = selected_model_config.default_duration

    yield


def on_modifier_click(e: me.ClickEvent):
    """Handles click events for modifier content_buttons."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_modifier_button",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"key": e.key},
    )
    state = me.state(PageState)
    modifier_key = e.key.split("mod_btn_")[-1]

    if not modifier_key:
        print("Error: ClickEvent has no key associated with the content_button.")
        return

    # If the key is already selected, deselect it.
    if modifier_key in state.modifier_array:
        new_modifier_array = [
            mod for mod in state.modifier_array if mod != modifier_key
        ]
        state.modifier_array = new_modifier_array
    # If the key is not selected, add it, but only if less than 2 are already selected.
    elif len(state.modifier_array) < 2:
        state.modifier_array = [*state.modifier_array, modifier_key]
    # If 2 are already selected, do nothing (or we could show a message).
    else:
        print("Maximum of 2 modifiers can be selected.")


def on_change_auto_enhance_prompt(e: me.CheckboxChangeEvent):
    """Toggle auto-enhance prompt"""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_auto_enhance_prompt",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"checked": e.checked},
    )
    state = me.state(PageState)
    state.auto_enhance_prompt = e.checked


def on_selection_change_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video duration length in seconds based on user event"""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_length_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.video_length = int(e.value)


def on_selection_change_aspect(e: me.SelectSelectionChangeEvent):
    """Adjust aspect ratio based on user event."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_aspect_ratio_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(PageState)
    state.aspect_ratio = e.value


def on_open_selfie_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_selfie_dialog = True
    yield


def on_selfie_capture(e: me.WebEvent):
    state = me.state(PageState)
    state.show_selfie_dialog = False
    
    # The data is a base64-encoded data URL, e.g., "data:image/png;base64,iVBORw0KGgo..."
    data_url = e.value["value"]
    # Simple split to get the actual base64 data
    try:
        header, encoded = data_url.split(",", 1)
        # Get mime type from header
        mime_type = header.split(";")[0].split(":")[1]
        # Decode the base64 string
        image_data = base64.b64decode(encoded)
        
        # Store to GCS
        gcs_uri = store_to_gcs(
            folder="selfies",
            file_name=f"selfie_{uuid.uuid4()}.png",
            mime_type=mime_type,
            contents=image_data,
        )
        
        # Update state
        state.reference_image_gcs = gcs_uri
        state.reference_image_display_url = create_display_url(gcs_uri)
        state.reference_image_mime_type = mime_type

    except Exception as ex:
        state.error_message = f"Failed to process selfie: {ex}"
        state.show_error_dialog = True

    yield




def on_click_upload(e: me.UploadEvent):
    """Upload image to GCS"""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_upload_button",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
    state = me.state(PageState)
    state.reference_image_file = e.file
    state.reference_image_mime_type = e.file.mime_type
    contents = e.file.getvalue()
    destination_blob_name = store_to_gcs(
        "uploads", e.file.name, e.file.mime_type, contents
    )
    state.reference_image_gcs = destination_blob_name
    # url
    state.reference_image_display_url = create_display_url(destination_blob_name)
    # log
    print(
        f"{destination_blob_name} with contents len {len(contents)} of type {e.file.mime_type} uploaded to {config.GENMEDIA_BUCKET}."
    )


def on_portrait_image_from_library(e: LibrarySelectionChangeEvent):
    """Portrait image from library handler."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="portraits_library_chooser_button",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
    state = me.state(PageState)
    state.reference_image_gcs = e.gcs_uri
    state.reference_image_display_url = create_display_url(e.gcs_uri)
    yield


@track_click(element_id="portraits_create_button")
def on_click_motion_portraits(e: me.ClickEvent):
    """Create the motion portrait"""
    app_state = me.state(AppState)
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

    base_prompt = f"""Scene direction for a motion portrait for an approximately {state.video_length} second scene.

Expand the given direction to include more facial engagement, as if the subject is looking out of the image and interested in the world outside.

Examine the picture provided to improve the scene direction.
"""

    final_prompt_for_llm = base_prompt
    if state.modifier_array:
        # Get the full style objects for the selected IDs
        selected_styles = [s for s in PORTRAIT_STYLES if s.id in state.modifier_array]

        # Append each style's full description
        final_prompt_for_llm += "\n\nIncorporate the following stylistic directions:\n"
        for style in selected_styles:
            final_prompt_for_llm += f"- {style.description}\n"

    else:
        # base prompt - waving
        final_prompt_for_llm += """Optionally, include is waving of hands and if necessary, and physical motion outside the frame.

Do not describe the frame. There should be no lip movement like speaking, but there can be descriptions of facial movements such as laughter, either in joy or cruelty."""

    final_prompt_for_llm += "\n\nScene direction:\n"

    gcs_uri = ""
    current_error_message = ""
    execution_time = 0

    try:
        print(
            f"Generating scene direction for {state.reference_image_gcs} with prompt:\n{final_prompt_for_llm}"
        )
        scene_direction_for_video = generate_scene_direction(
            final_prompt_for_llm,
            state.reference_image_gcs,
            state.reference_image_mime_type,
        )
        state.generated_scene_direction = scene_direction_for_video
        state.veo_prompt_input = scene_direction_for_video
        print(f"Generated Scene Direction (for video):\n{scene_direction_for_video}")
        yield

        print("Lights, camera, action!")
        start_time = time.time()

        request = VideoGenerationRequest(
            prompt=scene_direction_for_video,
            duration_seconds=state.video_length,
            aspect_ratio=state.aspect_ratio,
            resolution="720p",  # Motion portraits default to 720p
            enhance_prompt=state.auto_enhance_prompt,
            generate_audio=True,
            model_version_id=state.veo_model,
            reference_image_gcs=state.reference_image_gcs,
            reference_image_mime_type=state.reference_image_mime_type,
            person_generation="allow_adult",
            video_count=1
        )

        gcs_uri, _ = generate_video(request)

        end_time = time.time()
        execution_time = end_time - start_time
        state.timing = f"Generation time: {round(execution_time)} seconds"

        if gcs_uri:
            gcs_uri = gcs_uri[0]
            state.result_video_gcs_uri = gcs_uri
            state.result_video_display_url = create_display_url(gcs_uri)
            print(f"Video generated: {gcs_uri}.")
        else:
            current_error_message = "Video generation failed to return a GCS URI."

    except Exception as err:
        print(
            f"Exception during motion portrait generation: {type(err).__name__}: {err}"
        )
        current_error_message = f"An unexpected error occurred: {err}"

    if current_error_message:
        state.error_message = current_error_message
        state.show_error_dialog = True
        state.result_video = ""

    if gcs_uri and not current_error_message:
        try:
            add_media_item_to_firestore(
                MediaItem(
                    gcsuri=gcs_uri,
                    prompt=state.veo_prompt_input,
                    aspect=state.aspect_ratio,
                    model=state.veo_model,
                    generation_time=execution_time,
                    duration=float(state.video_length),
                    reference_image=state.reference_image_gcs,
                    enhanced_prompt_used=state.auto_enhance_prompt,
                    error_message="",
                    comment="motion portrait",
                    last_reference_image=None,
                    user_email=app_state.user_email,
                    mime_type="video/mp4",
                )
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

    state.is_loading = False
    yield
    print("Motion portrait generation process finished.")


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
    if not image_mime_type:
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
            model=config.MODEL_ID,
            contents=contents,
            config=GenerateContentConfig(),
        )

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


def on_click_close_error_dialog(e: me.ClickEvent):
    """Close error dialog"""
    state = me.state(PageState)
    state.show_error_dialog = False
    state.error_message = ""
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


@me.component
def selfie_dialog():
    state = me.state(PageState)
    with dialog(is_open=state.show_selfie_dialog):
        # Only render the camera component if the dialog is actually open
        # to prevent it from activating the camera on page load.
        if state.show_selfie_dialog:
            with me.box(style=me.Style(padding=me.Padding.all(16))):
                me.text("Take a Selfie", type="headline-6")
                selfie_camera(on_capture=on_selfie_capture)
                with me.box(style=me.Style(display="flex", justify_content="flex-end", margin=me.Margin(top=16))):
                    me.button("Cancel", on_click=lambda e: setattr(state, "show_selfie_dialog", False), type="flat")