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
from dataclasses import dataclass, field
from typing import Callable

import mesop as me
import requests

from common.analytics import log_ui_click
from common.utils import create_display_url
from common.veo_utils import start_async_veo_job
from components.dialog import dialog, dialog_actions
from config.default import Default
from config.veo_models import VEO_MODELS, get_veo_model_config
from models.requests import VideoGenerationRequest
from state.state import AppState


@me.stateclass
@dataclass
class VeoExtendDialogState:
    """State for the Veo Extend Dialog."""

    is_open: bool = False
    input_video_uri: str = ""  # GCS URI
    prompt: str = ""
    model_id: str = "3.1-fast-preview"
    duration: int = 7
    is_loading: bool = False
    loading_message: str = ""
    error_message: str = ""
    job_id: str = ""
    job_status: str = ""
    generated_video_uri: str = ""  # GCS URI of result


@me.component
def extend_dialog(state: VeoExtendDialogState, on_close: Callable):
    """
    Renders a dialog to extend a Veo video.
    """
    print(f"DEBUG: Rendering extend_dialog. is_open={state.is_open}")

    with dialog(is_open=state.is_open, dialog_style=me.Style(width="800px", max_width="90vw")):  # pylint: disable=E1129:not-context-manager
        if state.is_open:
            me.text("Extend Video", type="headline-5")

            if state.is_loading:
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                        gap=16,
                        padding=me.Padding.all(24),
                    )
                ):
                    me.progress_spinner()
                    me.text(state.loading_message)
                return

            if state.generated_video_uri:
                _render_success_view(state, on_close)
                return

        # Main Layout: Row with Preview and Form
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", gap=24, margin=me.Margin(top=16)
            )
        ):
            # Left: Input Video Preview
            with me.box(
                style=me.Style(
                    flex_basis="40%", display="flex", flex_direction="column", gap=8
                )
            ):
                me.text(
                    "Input Video",
                    style=me.Style(
                        font_weight="bold", color=me.theme_var("on-surface-variant")
                    ),
                )
                if state.input_video_uri:
                    input_display_url = create_display_url(state.input_video_uri)
                    me.video(
                        src=input_display_url,
                        style=me.Style(width="100%", border_radius=8),
                    )

            # Right: Input Form
            with me.box(
                style=me.Style(
                    flex_basis="60%", display="flex", flex_direction="column", gap=16
                )
            ):
                # Prompt Input
                me.textarea(
                    label="Prompt for extension",
                    value=state.prompt,
                    on_blur=on_prompt_blur,
                    style=me.Style(width="100%"),
                    rows=4,
                    appearance="outline",
                )

                # Configuration Row
                with me.box(
                    style=me.Style(display="flex", flex_direction="row", gap=16)
                ):
                    # Filter models that support extension
                    extension_models = [
                        m for m in VEO_MODELS if m.supports_video_extension
                    ]

                    me.select(
                        label="Model",
                        options=[
                            me.SelectOption(label=m.display_name, value=m.version_id)
                            for m in extension_models
                        ],
                        value=state.model_id,
                        on_selection_change=on_model_change,
                        style=me.Style(flex_grow=1),
                        appearance="outline",
                    )

                    # Durations
                    current_model_config = get_veo_model_config(state.model_id)
                    durations = (
                        current_model_config.supported_extension_durations
                        if current_model_config
                        and current_model_config.supported_extension_durations
                        else [7]
                    )

                    me.select(
                        label="Extension Length",
                        options=[
                            me.SelectOption(label=f"{d}s", value=str(d))
                            for d in durations
                        ],
                        value=str(state.duration),
                        on_selection_change=on_duration_change,
                        style=me.Style(width="120px"),
                        appearance="outline",
                    )

                if state.error_message:
                    me.text(
                        state.error_message, style=me.Style(color=me.theme_var("error"))
                    )

        with dialog_actions(): # pylint: disable=E1129:not-context-manager
            me.button("Cancel", on_click=on_close)
            me.button(
                "Extend",
                on_click=on_extend_click,
                type="raised",
                disabled=not state.prompt,
            )


def _render_success_view(state: VeoExtendDialogState, on_close: Callable):
    """Renders the success view with the new video."""
    with me.box(
        style=me.Style(
            display="flex", flex_direction="column", gap=16, align_items="center"
        )
    ):
        me.text(
            "Video Extended Successfully!",
            style=me.Style(color="green", font_weight="bold"),
        )

        display_url = create_display_url(state.generated_video_uri)
        me.video(
            src=display_url,
            style=me.Style(width="100%", max_height="400px", border_radius=8),
        )

        with me.box(style=me.Style(display="flex", gap=8, margin=me.Margin(top=16))):
            me.button("Close", on_click=on_close, type="stroked")


def on_prompt_blur(e: me.InputBlurEvent):
    state = _get_dialog_state()
    state.prompt = e.value
    yield


# --- Event Handlers ---
# NOTE: Because Mesop event handlers cannot accept custom arguments (like the state object),
# we have to import the specific PageState that holds this dialog's state.
# This creates a dependency on the parent page.
# To make this component generic, we would need a Registry or a way to inject the State class.
# For this implementation, we will explicitly import PageState from pages.library_v2
# BUT pages.library_v2 imports THIS file. Circular Import!
# SOLUTION: Define the handlers in library_v2.py OR use a common state module.
# Since we want to keep logic here, we will use a trick:
# pass the state instance to the render function, but for handlers we need to fetch it.
# We will defer the implementation of the handlers to be inside 'pages/library_v2.py'
# OR we move the state definition to a shared location.

# Alternative: We define the handlers here but they will fail unless we can import the state class.
# Let's use `me.state(object)`? No, must be a class.

# Decision: We will put the HANDLERS in this file, but we will do the import inside the function
# to avoid top-level circular imports.


def _get_dialog_state():
    from pages.library_v2 import PageState

    return me.state(PageState).extend_dialog_state


def _get_app_state():
    return me.state(AppState)


def on_model_change(e: me.SelectSelectionChangeEvent):
    state = _get_dialog_state()
    state.model_id = e.value
    yield


def on_duration_change(e: me.SelectSelectionChangeEvent):
    state = _get_dialog_state()
    state.duration = int(e.value)
    yield


def on_extend_click(e: me.ClickEvent):
    state = _get_dialog_state()
    app_state = _get_app_state()
    config = Default()

    if not state.prompt:
        state.error_message = "Please enter a prompt."
        yield
        return

    state.is_loading = True
    state.loading_message = "Starting extension job..."
    state.error_message = ""
    yield

    # 1. Start Job
    try:
        request = VideoGenerationRequest(
            prompt=state.prompt,
            model_version_id=state.model_id,
            duration_seconds=state.duration,
            video_count=1,
            aspect_ratio="16:9",  # Default, will be overridden by video input usually or model logic
            resolution="720p",  # Extension typically requires 720p
            enhance_prompt=False,
            generate_audio=True,
            person_generation="Allow (Adults only)",
            video_input_gcs=state.input_video_uri,
            video_input_mime_type="video/mp4",
        )

        response_data = start_async_veo_job(
            request, app_state.user_email, mode="video_extension"
        )
        state.job_id = response_data["job_id"]
        state.job_status = response_data["status"]
        state.loading_message = "Extending video..."
        yield
    except Exception as e:
        state.is_loading = False
        state.error_message = str(e)
        yield
        return

    # 2. Poll
    while state.job_status in ["pending", "processing", "created"]:
        time.sleep(2)
        try:
            status_url = f"{config.API_BASE_URL}/api/veo/job/{state.job_id}"
            resp = requests.get(status_url)
            resp.raise_for_status()
            status_data = resp.json()
            state.job_status = status_data["status"]

            if state.job_status == "complete":
                state.generated_video_uri = (
                    status_data.get("video_uri") or status_data.get("video_uris")[0]
                )
                state.is_loading = False
                yield
                # Trigger a library refresh?
                # We can't easily trigger the parent's refresh from here without a callback mechanism
                # that Mesop doesn't fully support across modules easily.
                # The user will see the success screen and click close.
                break
            elif state.job_status == "failed":
                state.is_loading = False
                state.error_message = status_data.get("error_message", "Unknown error")
                yield
                break

            yield
        except Exception as e:
            state.is_loading = False
            state.error_message = f"Polling failed: {e}"
            yield
            break
