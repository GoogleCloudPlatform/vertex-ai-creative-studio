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

import base64
import time
import traceback
import uuid

import mesop as me

from common.metadata import add_media_item
from common.storage import store_to_gcs
from common.utils import create_display_url
from components.dialog import dialog
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.selfie_camera.selfie_camera import selfie_camera
from config.default import Default
from pages.styles import _BOX_STYLE_CENTER_DISTRIBUTED
from state.state import AppState
from workflows.retro_games.backend import (
    RetroGameWorkflowState,
    initialize_workflow,
    step_1_generate_8bit,
    step_2_generate_character_sheet,
    step_3_generate_video,
    step_4_append_bumper,
)
from workflows.retro_games.retro_games_config import RetroGameConfig

print(f"DEBUG: retro_games loaded. PROJECT_ID={Default().PROJECT_ID}")


@me.stateclass
class PageState:
    player1_image_uri: str = ""
    player1_image_display_url: str = ""

    player2_image_uri: str = ""
    player2_image_display_url: str = ""

    selected_theme_value: str = "Google"  # Default to Google

    # New Configuration Fields
    theme_context: str = ""
    include_bumper: bool = True
    selected_model: str = "3.1-preview"
    selected_duration: str = "8"  # Stored as string for select component
    selected_scene_count: str = "1" # Stored as string

    # Removed workflow_state from PageState to avoid potential serialization issues
    is_running: bool = False
    current_step: str = ""

    # For UI display of intermediate results
    player1_8bit_display_url: str = ""
    player1_8bit_gcs_uri: str = ""  # Stored for regeneration
    player1_sheet_display_url: str = ""
    player1_sheet_gcs_uri: str = ""  # Stored for regeneration

    player2_8bit_display_url: str = ""
    player2_8bit_gcs_uri: str = ""
    player2_sheet_display_url: str = ""
    player2_sheet_gcs_uri: str = ""
 
    final_video_display_url: str = ""

    error_message: str = ""
    show_selfie_dialog: bool = False
    active_uploader: str = "player1" # Tracks which player initiated the selfie dialog

    start_time: float = 0.0
    total_duration: str = ""


def on_upload_p1(e: me.UploadEvent):
    state = me.state(PageState)
    data = e.file.getvalue()
    gcs_uri = store_to_gcs("uploads", e.file.name, e.file.mime_type, data)
    state.player1_image_uri = gcs_uri
    state.player1_image_display_url = create_display_url(gcs_uri)
    yield

def on_upload_p2(e: me.UploadEvent):
    state = me.state(PageState)
    data = e.file.getvalue()
    gcs_uri = store_to_gcs("uploads", e.file.name, e.file.mime_type, data)
    state.player2_image_uri = gcs_uri
    state.player2_image_display_url = create_display_url(gcs_uri)
    yield

def on_library_select(e: LibrarySelectionChangeEvent):
    state = me.state(PageState)
    # Check the key to know which player
    if e.chooser_id == "retro_lib_p1":
        state.player1_image_uri = e.gcs_uri
        state.player1_image_display_url = create_display_url(e.gcs_uri)
    elif e.chooser_id == "retro_lib_p2":
        state.player2_image_uri = e.gcs_uri
        state.player2_image_display_url = create_display_url(e.gcs_uri)
    yield


def on_theme_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.selected_theme_value = e.key
    yield


def on_theme_context_change(e: me.InputBlurEvent):
    state = me.state(PageState)
    state.theme_context = e.value
    yield


def on_include_bumper_change(e: me.CheckboxChangeEvent):
    state = me.state(PageState)
    state.include_bumper = e.checked
    yield


def on_model_change(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.selected_model = e.value
    yield


def on_duration_change(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.selected_duration = e.value
    yield

def on_scene_count_change(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.selected_scene_count = e.value
    yield


def _run_video_generation_steps(
    state: PageState, wf_state: RetroGameWorkflowState, app_state: AppState, theme: str
):
    """Executes Step 3 (Video) and Step 4 (Bumper) and handles persistence."""
    # Step 3
    state.current_step = "Generating video (this may take a minute)..."
    yield
    wf_state = step_3_generate_video(wf_state)
    if wf_state.status == "error":
        raise Exception(wf_state.error_message)
    yield

    # Step 4
    state.current_step = "Finalizing video..."
    yield
    wf_state = step_4_append_bumper(wf_state)
    if wf_state.status == "error":
        raise Exception(wf_state.error_message)
    if wf_state.final_video_uri:
        state.final_video_display_url = create_display_url(wf_state.final_video_uri)

        # Persist to Firestore
        try:
            config = RetroGameConfig()
            theme_8bit_logo = config.get_theme_8bit_logo(theme)

            r2v_refs = [
                wf_state.player1_8bit_uri,
                wf_state.player1_sheet_uri,
                wf_state.player2_8bit_uri,
                wf_state.player2_sheet_uri,
                theme_8bit_logo,
            ]
            # Filter out None
            r2v_refs = [r for r in r2v_refs if r]

            add_media_item(
                user_email=app_state.user_email,
                prompt=wf_state.scene_direction,  # Use scene direction as prompt for video
                gcsuri=wf_state.final_video_uri,
                mime_type="video/mp4",
                media_type="video",
                model=state.selected_model,
                duration=float(state.selected_duration),
                comment=f"Retro Game Workflow ({theme} Theme)",
                r2v_reference_images=r2v_refs,
                mode="r2v",
            )
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
            traceback.print_exc()


def on_click_generate(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)

    if not state.player1_image_uri:
        state.error_message = "Please select an input image first."
        yield
        return

    state.is_running = True
    state.error_message = ""
    
    # Reset output display
    state.player1_8bit_display_url = ""
    state.player1_sheet_display_url = ""
    state.player2_8bit_display_url = ""
    state.player2_sheet_display_url = ""
    state.final_video_display_url = ""
    
    state.current_step = "Initializing..."
    state.start_time = time.time()
    state.total_duration = ""
    yield

    try:
        theme = state.selected_theme_value
        wf_state = initialize_workflow(
            user_email=app_state.user_email,
            theme=theme,
            player1_image_uri=state.player1_image_uri,
            player2_image_uri=state.player2_image_uri if state.player2_image_uri else None,
            theme_context=state.theme_context,
            include_bumper=state.include_bumper,
            model_version=state.selected_model,
            duration=int(state.selected_duration),
            scene_count=int(state.selected_scene_count),
        )
        yield

        # Step 1
        state.current_step = "Generating 8-bit images..."
        yield
        wf_state = step_1_generate_8bit(wf_state)
        if wf_state.status == "error":
            raise Exception(wf_state.error_message)
            
        if wf_state.player1_8bit_uri:
            state.player1_8bit_gcs_uri = wf_state.player1_8bit_uri
            state.player1_8bit_display_url = create_display_url(wf_state.player1_8bit_uri)
            
        if wf_state.player2_8bit_uri:
            state.player2_8bit_gcs_uri = wf_state.player2_8bit_uri
            state.player2_8bit_display_url = create_display_url(wf_state.player2_8bit_uri)
        yield

        # Step 2
        state.current_step = "Generating character sheets..."
        yield
        wf_state = step_2_generate_character_sheet(wf_state)
        if wf_state.status == "error":
            raise Exception(wf_state.error_message)

        if wf_state.player1_sheet_uri:
            state.player1_sheet_gcs_uri = wf_state.player1_sheet_uri 
            state.player1_sheet_display_url = create_display_url(wf_state.player1_sheet_uri)
            
        if wf_state.player2_sheet_uri:
            state.player2_sheet_gcs_uri = wf_state.player2_sheet_uri
            state.player2_sheet_display_url = create_display_url(wf_state.player2_sheet_uri)
        yield

        # Run Video Steps
        yield from _run_video_generation_steps(state, wf_state, app_state, theme)

        duration = time.time() - state.start_time
        state.total_duration = f"Total time: {int(duration)} seconds"
        state.current_step = "Complete!"
    except Exception as ex:
        traceback.print_exc()
        state.error_message = str(ex)
        state.current_step = "Failed"
    finally:
        state.is_running = False
        yield


def on_click_regenerate_video(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)

    if not state.player1_8bit_gcs_uri or not state.player1_sheet_gcs_uri:
        state.error_message = "Cannot regenerate: Missing intermediate assets."
        yield
        return

    state.is_running = True
    state.error_message = ""
    state.final_video_display_url = ""
    state.current_step = "Regenerating Video..."
    op_start_time = time.time()
    yield

    try:
        theme = state.selected_theme_value
        # Initialize new workflow state but pre-populate assets
        wf_state = initialize_workflow(
            user_email=app_state.user_email,
            theme=theme,
            player1_image_uri=state.player1_image_uri,
            player2_image_uri=state.player2_image_uri if state.player2_image_uri else None,
            theme_context=state.theme_context,
            include_bumper=state.include_bumper,
            model_version=state.selected_model,
            duration=int(state.selected_duration),
            scene_count=int(state.selected_scene_count),
        )

        # Manually inject existing assets
        wf_state.player1_8bit_uri = state.player1_8bit_gcs_uri
        wf_state.player1_sheet_uri = state.player1_sheet_gcs_uri
        
        if state.player2_8bit_gcs_uri:
            wf_state.player2_8bit_uri = state.player2_8bit_gcs_uri
        if state.player2_sheet_gcs_uri:
            wf_state.player2_sheet_uri = state.player2_sheet_gcs_uri

        # Run Video Steps
        yield from _run_video_generation_steps(state, wf_state, app_state, theme)

        duration = time.time() - op_start_time
        state.total_duration = f"Regeneration time: {int(duration)} seconds"
        state.current_step = "Complete!"

    except Exception as ex:
        traceback.print_exc()
        state.error_message = str(ex)
        state.current_step = "Failed"
    finally:
        state.is_running = False
        yield


def on_clear_p2(e: me.ClickEvent):
    state = me.state(PageState)
    state.player2_image_uri = ""
    state.player2_image_display_url = ""
    state.player2_8bit_display_url = ""
    state.player2_sheet_display_url = ""
    yield

def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.player1_image_uri = ""
    state.player1_image_display_url = ""
    state.player2_image_uri = ""
    state.player2_image_display_url = ""
    
    state.player1_8bit_display_url = ""
    state.player1_sheet_display_url = ""
    state.player2_8bit_display_url = ""
    state.player2_sheet_display_url = ""
    
    state.final_video_display_url = ""
    state.error_message = ""
    state.is_running = False
    state.current_step = ""
    state.total_duration = ""
    state.theme_context = ""
    # Do not clear config preferences like model/bumper
    yield


# Selfie handlers
def on_open_selfie_dialog_p1(e: me.ClickEvent):
    state = me.state(PageState)
    state.active_uploader = "player1"
    state.show_selfie_dialog = True
    yield

def on_open_selfie_dialog_p2(e: me.ClickEvent):
    state = me.state(PageState)
    state.active_uploader = "player2"
    state.show_selfie_dialog = True
    yield


def on_close_selfie_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_selfie_dialog = False
    yield


def on_selfie_capture(e: me.WebEvent):
    state = me.state(PageState)
    # Don't close dialog immediately, wait for processing

    try:
        data_url = e.value["value"]
        header, encoded = data_url.split(",", 1)
        mime_type = header.split(";")[0].split(":")[1]
        image_data = base64.b64decode(encoded)

        gcs_uri = store_to_gcs(
            folder="selfies",
            file_name=f"selfie_{uuid.uuid4()}.png",
            mime_type=mime_type,
            contents=image_data,
        )

        if state.active_uploader == "player1":
            state.player1_image_uri = gcs_uri
            state.player1_image_display_url = create_display_url(gcs_uri)
        elif state.active_uploader == "player2":
            state.player2_image_uri = gcs_uri
            state.player2_image_display_url = create_display_url(gcs_uri)

        state.show_selfie_dialog = False  # Close on success
    except Exception as ex:
        traceback.print_exc()
        state.error_message = f"Failed to process selfie: {ex}"
        # Keep dialog open on error so they can try again? Or close it?
        # Let's close it for now to avoid getting stuck.
        state.show_selfie_dialog = False
    yield


@me.page(path="/retro_games", title="Retro Games Workflow")
def page():
    with page_scaffold(page_name="retro_games"):  # pylint: disable=E1129:not-context-manager
        retro_games_content()


def retro_games_content():
    state = me.state(PageState)
    config = RetroGameConfig()

    # Selfie Dialog
    if state.show_selfie_dialog:
        with dialog(is_open=state.show_selfie_dialog):  # pylint: disable=E1129:not-context-manager
            with me.box(
                style=me.Style(
                    padding=me.Padding.all(16), width="500px", height="600px"
                )
            ):  # Added fixed size for dialog content
                me.text("Take a Selfie", type="headline-6")
                # Ensure selfie camera fits
                with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
                    selfie_camera(on_capture=on_selfie_capture)
                with me.box(
                    style=me.Style(
                        display="flex",
                        justify_content="flex-end",
                        margin=me.Margin(top=16),
                    )
                ):
                    me.button("Cancel", on_click=on_close_selfie_dialog, type="flat")

    with page_frame():  # pylint: disable=E1129:not-context-manager
        header("Retro Games", "videogame_asset")

        # Main Content Container
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=24)):
            # Top Section: Two Columns
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="row", gap=24,
                )
            ):
                # Left Column: Inputs
                with me.box(
                    style=me.Style(flex_grow=1, flex_basis="300px", min_width="200px")
                ):
                    # Player 1 & 2
                    with me.box(
                        style=me.Style(
                            display="flex", flex_direction="row", gap=16
                        ),
                    ):
                        # Player 1 Input
                        with me.box(style=_BOX_STYLE_CENTER_DISTRIBUTED):
                            me.text("Player 1", type="headline-6")

                            # Image Display
                            if state.player1_image_display_url:
                                me.image(
                                    src=state.player1_image_display_url,
                                    style=me.Style(
                                        height=150,
                                        object_fit="contain",
                                        margin=me.Margin(top=16, bottom=16),
                                    ),
                                )
                            else:
                                with me.box(
                                    style=me.Style(
                                        height=150,
                                        width="100%",
                                        background=me.theme_var("surface-variant"),
                                        border_radius=8,
                                        margin=me.Margin(top=16, bottom=16),
                                        display="flex",
                                        justify_content="center",
                                        align_items="center",
                                    )
                                ):
                                    me.icon(
                                        "person",
                                        style=me.Style(
                                            font_size=24,
                                            color=me.theme_var("on-surface-variant"),
                                        ),
                                    )

                            # Input Controls
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    gap=8,
                                    flex_wrap="wrap",
                                    justify_content="center",
                                )
                            ):
                                me.uploader(
                                    label="Upload",
                                    on_upload=on_upload_p1,
                                    accepted_file_types=["image/jpeg", "image/png"],
                                    type="flat",
                                )
                                library_chooser_button(
                                    on_library_select=on_library_select,
                                    button_type="icon",
                                    key="retro_lib_p1",
                                )
                                with me.content_button(
                                    type="icon", on_click=on_open_selfie_dialog_p1
                                ):
                                    me.icon("camera_alt")
                                    
                        # Player 2 Input (Optional)
                        with me.box(
                            style=_BOX_STYLE_CENTER_DISTRIBUTED
                            # me.Style(
                            #     flex_basis="max(480px, calc(50% - 48px))",
                            #     background=me.theme_var("background"),
                            #     border_radius=12,
                            #     box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
                            #     padding=me.Padding.all(16),
                            #     display="flex",
                            #     flex_direction="column",
                            #     align_items="center",
                            #     justify_content="space-between",
                            #     width="100%",
                            #     margin=me.Margin(top=24),
                            # )
                        ):
                            me.text("Player 2 (Optional)", type="headline-6")

                            # Image Display
                            if state.player2_image_display_url:
                                me.image(
                                    src=state.player2_image_display_url,
                                    style=me.Style(
                                        height=150,
                                        object_fit="contain",
                                        margin=me.Margin(top=16, bottom=16),
                                    ),
                                )
                            else:
                                with me.box(
                                    style=me.Style(
                                        height=150,
                                        width="100%",
                                        background=me.theme_var("surface-variant"),
                                        border_radius=8,
                                        margin=me.Margin(top=16, bottom=16),
                                        display="flex",
                                        justify_content="center",
                                        align_items="center",
                                    )
                                ):
                                    #me.text("No P2 Selected", style=me.Style(color=me.theme_var("on-surface-variant")))
                                    me.icon(
                                        "person",
                                        style=me.Style(
                                            font_size=24,
                                            color=me.theme_var("on-surface-variant"),
                                        ),
                                    )

                            # Input Controls
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    gap=8,
                                    flex_wrap="wrap",
                                    justify_content="center",
                                )
                            ):
                                me.uploader(
                                    label="Upload",
                                    on_upload=on_upload_p2,
                                    accepted_file_types=["image/jpeg", "image/png"],
                                    type="flat",
                                )
                                library_chooser_button(
                                    on_library_select=on_library_select,
                                    button_type="icon",
                                    key="retro_lib_p2",
                                )
                                with me.content_button(
                                    type="icon", on_click=on_open_selfie_dialog_p2
                                ):
                                    me.icon("camera_alt")
                                if state.player2_image_uri:
                                    me.button("Clear P2", on_click=on_clear_p2, type="flat", color="warn")

                    # Advanced Options
                    with me.box(
                        style=me.Style(
                            background=me.theme_var("background"),
                            border_radius=12,
                            box_shadow=(
                                "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
                            ),
                            padding=me.Padding.all(2),
                            display="flex",
                            flex_direction="column",
                            gap=16,
                            margin=me.Margin(top=24),
                        )
                    ):
                        me.text("Configuration", type="headline-6")
                        me.input(
                            label="Theme Context (Optional)",
                            value=state.theme_context,
                            on_blur=on_theme_context_change,
                            placeholder="e.g. 'in a futuristic NYC', 'on a pirate ship'",
                            style=me.Style(width="100%"),
                        )

                        with me.box(
                            style=me.Style(display="flex", gap=16, flex_wrap="wrap")
                        ):
                            me.select(
                                label="Model",
                                options=[
                                    me.SelectOption(
                                        label="Veo 3.1 Preview",
                                        value="3.1-preview",
                                    )
                                ],
                                value=state.selected_model,
                                on_selection_change=on_model_change,
                                style=me.Style(flex_grow=1),
                            )
                            me.select(
                                label="Scene Length",
                                options=[
                                    #me.SelectOption(label="4s", value="4"),
                                    me.SelectOption(label="8s", value="8"),
                                ],
                                value=state.selected_duration,
                                on_selection_change=on_duration_change,
                                style=me.Style(width="100px"),
                            )
                            me.select(
                                label="Scenes",
                                options=[
                                    me.SelectOption(label="1", value="1"),
                                    me.SelectOption(label="2", value="2"),
                                    me.SelectOption(label="3", value="3"),
                                ],
                                value=state.selected_scene_count,
                                on_selection_change=on_scene_count_change,
                                style=me.Style(width="100px"),
                            )
                            me.checkbox(
                                label="Append Theme Bumper",
                                checked=state.include_bumper,
                                on_change=on_include_bumper_change,
                            )

                    # Theme Selection with Logos
                    with me.box(
                        style=me.Style(
                            # flex_basis="max(480px, calc(50% - 48px))", # Removed to let parent control
                            background=me.theme_var("background"),
                            border_radius=12,
                            box_shadow=(
                                "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
                            ),
                            padding=me.Padding.all(16),
                            display="flex",
                            flex_direction="column",
                            margin=me.Margin(top=24),
                        )
                    ):
                        me.text("Theme Selection", type="headline-6")
                        with me.box(
                            style=me.Style(
                                display="flex",
                                gap=16,
                                flex_wrap="wrap",
                                margin=me.Margin(top=16),
                                justify_content="center",
                            )
                        ):
                            for theme_name in config.get_theme_names():
                                is_selected = state.selected_theme_value == theme_name
                                logo_uri = config.get_theme_logo(theme_name)
                                display_url = (
                                    create_display_url(logo_uri) if logo_uri else ""
                                )

                                with me.box(
                                    key=theme_name,
                                    on_click=on_theme_click,
                                    style=me.Style(
                                        cursor="pointer",
                                        display="flex",
                                        flex_direction="column",
                                        align_items="center",
                                        gap=8,
                                        padding=me.Padding.all(8),
                                        border=me.Border.all(
                                            me.BorderSide(
                                                width=3 if is_selected else 1,
                                                color=me.theme_var("primary")
                                                if is_selected
                                                else me.theme_var("outline"),
                                            )
                                        ),
                                        border_radius=12,
                                        background=me.theme_var("secondary-container")
                                        if is_selected
                                        else "transparent",
                                    ),
                                ):
                                    if display_url:
                                        me.image(
                                            src=display_url,
                                            style=me.Style(
                                                height=80,
                                                width=80,
                                                object_fit="contain",
                                            ),
                                        )
                                    else:
                                        # Fallback if no logo
                                        with me.box(
                                            style=me.Style(
                                                height=80,
                                                width=80,
                                                display="flex",
                                                justify_content="center",
                                                align_items="center",
                                                background="#eee",
                                            )
                                        ):
                                            me.text(theme_name[0])

                                    me.text(
                                        theme_name,
                                        type="body-1" if is_selected else "body-2",
                                        style=me.Style(
                                            font_weight="bold"
                                            if is_selected
                                            else "normal"
                                        ),
                                    )

                        with me.box(
                            style=me.Style(margin=me.Margin(top=24), width="100%")
                        ):
                            me.button(
                                "Generate Retro Game",
                                on_click=on_click_generate,
                                type="raised",
                                style=me.Style(width="100%"),
                                disabled=state.is_running or not state.player1_image_uri,
                            )

                            if state.player1_sheet_display_url:
                                with me.box(style=me.Style(margin=me.Margin(top=12))):
                                    me.button(
                                        "Regenerate Video Only",
                                        on_click=on_click_regenerate_video,
                                        type="stroked",
                                        style=me.Style(width="100%"),
                                        disabled=state.is_running,
                                    )

                # Right Column: Status & Intermediate Results
                with me.box(
                    style=me.Style(
                        flex_grow=1,
                        flex_basis="400px",
                        min_width="300px",
                        display="flex",
                        flex_direction="column",
                        gap=24,
                    )
                ):
                    if state.error_message:
                        with me.box(
                            style=me.Style(
                                background=me.theme_var("error-container"),
                                color=me.theme_var("on-error-container"),
                                padding=me.Padding.all(16),
                                border_radius=8,
                            )
                        ):
                            me.text(state.error_message)

                    if state.is_running:
                        with me.box(
                            style=me.Style(display="flex", align_items="center", gap=16)
                        ):
                            me.progress_spinner()
                            me.text(state.current_step, type="headline-6")
                    elif state.current_step == "Complete!":
                        with me.box(
                            style=me.Style(display="flex", flex_direction="column")
                        ):
                            me.text(
                                "Generation Complete!",
                                type="headline-5",
                                style=me.Style(color=me.theme_var("primary")),
                            )
                            if state.total_duration:
                                me.text(state.total_duration, type="body-1")

                    # Intermediate Results Row
                    with me.box(style=me.Style(display="flex", flex_direction="column", gap=16)):
                        # Player 1 Results
                        if state.player1_8bit_display_url:
                            with me.box(
                                style=me.Style(
                                    background=me.theme_var("surface-variant"),
                                    border_radius=12,
                                    padding=me.Padding.all(12),
                                    display="flex",
                                    flex_direction="row",
                                    align_items="center",
                                    gap=16,
                                )
                            ):
                                me.text("Player 1", type="subtitle-1", style=me.Style(font_weight="bold", width="80px"))

                                # 8-bit
                                with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center")):
                                    me.image(
                                        src=state.player1_8bit_display_url,
                                        style=me.Style(height="250px", width="250px", border_radius=8, object_fit="cover", border=me.Border.all(me.BorderSide(width=1, color=me.theme_var("outline-variant")))),
                                    )
                                    me.text("8-bit", type="caption", style=me.Style(font_size="10px"))

                                # Sheet
                                if state.player1_sheet_display_url:
                                    with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center")):
                                        me.image(
                                            src=state.player1_sheet_display_url,
                                            style=me.Style(height="250px", width="250px", border_radius=8, object_fit="cover", border=me.Border.all(me.BorderSide(width=1, color=me.theme_var("outline-variant")))),
                                        )
                                        me.text("Sheet", type="caption", style=me.Style(font_size="10px"))

                        # Player 2 Results
                        if state.player2_8bit_display_url:
                            with me.box(
                                style=me.Style(
                                    background=me.theme_var("surface-variant"),
                                    border_radius=12,
                                    padding=me.Padding.all(12),
                                    display="flex",
                                    flex_direction="row",
                                    align_items="center",
                                    gap=16,
                                )
                            ):
                                me.text("Player 2", type="subtitle-1", style=me.Style(font_weight="bold", width="80px"))

                                # 8-bit
                                with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center")):
                                    me.image(
                                        src=state.player2_8bit_display_url,
                                        style=me.Style(height="250px", width="250px", border_radius=8, object_fit="cover", border=me.Border.all(me.BorderSide(width=1, color=me.theme_var("outline-variant")))),
                                    )
                                    me.text("8-bit", type="caption", style=me.Style(font_size="10px"))

                                # Sheet
                                if state.player2_sheet_display_url:
                                    with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center")):
                                        me.image(
                                            src=state.player2_sheet_display_url,
                                            style=me.Style(height="250px", width="250px", border_radius=8, object_fit="cover", border=me.Border.all(me.BorderSide(width=1, color=me.theme_var("outline-variant")))),
                                        )
                                        me.text("Sheet", type="caption", style=me.Style(font_size="10px"))

            # Bottom Section: Final Video (Full Width)
            if state.final_video_display_url:
                with me.box(
                    style=me.Style(
                        background=me.theme_var("background"),
                        border_radius=12,
                        box_shadow=(
                            "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
                        ),
                        padding=me.Padding.all(16),
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                        width="100%",  # Ensure full width
                    )
                ):
                    me.text(
                        "Final Retro Game Video", type="headline-4"
                    )  # Larger headline
                    me.video(
                        src=state.final_video_display_url,
                        style=me.Style(
                            width="100%",
                            max_width="960px",
                            border_radius=12,
                            margin=me.Margin(top=24),
                        ),
                    )  # Larger max width
