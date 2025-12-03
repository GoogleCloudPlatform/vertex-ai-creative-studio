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
"""Character Asset Sheet Workflow Page."""

import uuid
import datetime
import mesop as me

from common.storage import store_to_gcs
from common.utils import create_display_url
from common.metadata import MediaItem, add_media_item_to_firestore
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from components.snackbar import snackbar
from models.gemini import generate_image_from_prompt_and_images
from state.character_sheet_state import PageState
from state.state import AppState

@me.page(
    path="/character_sheet",
    title="Character Sheet - GenMedia Creative Studio",
)
def page():
    with page_scaffold(page_name="character_sheet"): # pylint: disable=E1129:not-context-manager
        with page_frame(): # pylint: disable=E1129:not-context-manager
            header("Character Sheet", "face")
            character_sheet_content()

def character_sheet_content():
    state = me.state(PageState)
    
    snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)

    with me.box(style=me.Style(display="flex", flex_direction="column", gap=24, padding=me.Padding.all(24))):
        
        # --- Input Section ---
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=24, flex_wrap="wrap")):
            
            # Left: Original Image Upload
            with me.box(style=me.Style(flex_basis="300px", flex_grow=1)):
                me.text("1. Upload Original Character", type="headline-6")
                if state.original_image_display_url:
                    me.image(
                        src=state.original_image_display_url,
                        style=me.Style(width="100%", border_radius=8, margin=me.Margin(bottom=16))
                    )
                    me.button("Clear", on_click=on_clear_original, type="stroked")
                else:
                    me.uploader(
                        label="Upload Image",
                        on_upload=on_upload_original,
                        accepted_file_types=["image/jpeg", "image/png", "image/webp"],
                    )

            # Right: Controls
            with me.box(style=me.Style(flex_basis="400px", flex_grow=2, display="flex", flex_direction="column", gap=16)):
                
                # Step 2: Generate Asset Sheet
                me.text("2. Generate Asset Sheet", type="headline-6")
                me.text("Create a multi-view character sheet to establish consistency.")
                
                me.button(
                    "Generate Asset Sheet",
                    on_click=on_generate_sheet_click,
                    type="raised",
                    disabled=state.is_generating_sheet or not state.original_image_gcs_uri
                )
                
                if state.is_generating_sheet:
                    me.progress_spinner(diameter=24)
                
                if state.asset_sheet_display_url:
                    me.text("Asset Sheet Result:", style=me.Style(font_weight="bold", margin=me.Margin(top=8)))
                    me.image(
                        src=state.asset_sheet_display_url,
                        style=me.Style(width="100%", border_radius=8, border=me.Border.all(me.BorderSide(width=1, color="#ccc")))
                    )

                me.divider()

                # Step 3: Generate Scenario
                me.text("3. Generate Scenario", type="headline-6")
                me.textarea(
                    label="Scenario Description",
                    placeholder="e.g., eating a burger in a diner",
                    value=state.scenario_prompt,
                    on_blur=on_scenario_blur,
                    rows=3,
                    style=me.Style(width="100%")
                )
                
                me.button(
                    "Generate Scenario Image",
                    on_click=on_generate_scenario_click,
                    type="raised",
                    disabled=state.is_generating_scenario or not state.scenario_prompt or not state.original_image_gcs_uri
                )
                
                if state.is_generating_scenario:
                    me.progress_spinner(diameter=24)

                if state.scenario_image_display_url:
                    me.text("Scenario Result:", style=me.Style(font_weight="bold", margin=me.Margin(top=8)))
                    me.image(
                        src=state.scenario_image_display_url,
                        style=me.Style(width="100%", border_radius=8)
                    )


# --- Event Handlers ---

def on_upload_original(e: me.UploadEvent):
    state = me.state(PageState)
    file = e.files[0]
    gcs_uri = store_to_gcs("character_sheet_uploads", file.name, file.mime_type, file.getvalue())
    state.original_image_gcs_uri = gcs_uri
    state.original_image_display_url = create_display_url(gcs_uri)
    yield

def on_clear_original(e: me.ClickEvent):
    state = me.state(PageState)
    state.original_image_gcs_uri = ""
    state.original_image_display_url = ""
    yield

def on_scenario_blur(e: me.InputEvent):
    state = me.state(PageState)
    state.scenario_prompt = e.value

def on_generate_sheet_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_generating_sheet = True
    state.asset_sheet_display_url = ""
    yield
    
    try:
        prompt = "Character sheet of this character, white background, multiple views: front, back, side, three-quarter, close-up face. Consistent style. High quality, detailed. Retain realism of original image."
        
        gcs_uris, _, _, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=[state.original_image_gcs_uri],
            aspect_ratio="16:9", # Wide aspect ratio for a sheet
            gcs_folder="character_sheets"
        )
        
        if gcs_uris:
            state.asset_sheet_gcs_uri = gcs_uris[0]
            state.asset_sheet_display_url = create_display_url(gcs_uris[0])
            
            # Save MediaItem
            media_item = MediaItem(
                id=str(uuid.uuid4()),
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                media_type="image",
                mode="Character Sheet - Asset",
                gcs_uris=[state.asset_sheet_gcs_uri],
                thumbnail_uri=state.asset_sheet_gcs_uri,
                prompt=prompt,
                source_images_gcs=[state.original_image_gcs_uri],
                comment="Generated Character Asset Sheet"
            )
            add_media_item_to_firestore(media_item)
            state.snackbar_message = "Asset sheet saved to library."
            state.show_snackbar = True
            
        else:
            state.snackbar_message = "Failed to generate asset sheet."
            state.show_snackbar = True
            
    except Exception as ex:
        state.snackbar_message = f"Error: {ex}"
        state.show_snackbar = True
    finally:
        state.is_generating_sheet = False
        yield

def on_generate_scenario_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_generating_scenario = True
    state.scenario_image_display_url = ""
    yield
    
    try:
        # Construct prompt
        prompt = f"{state.scenario_prompt}. Use the provided character sheet and reference image to ensure character consistency."
        
        # Inputs: Original + Asset Sheet (if available)
        images = [state.original_image_gcs_uri]
        if state.asset_sheet_gcs_uri:
            images.append(state.asset_sheet_gcs_uri)
            
        gcs_uris, _, _, _ = generate_image_from_prompt_and_images(
            prompt=prompt,
            images=images,
            aspect_ratio="16:9",
            gcs_folder="character_scenarios"
        )
        
        if gcs_uris:
            state.scenario_image_gcs_uri = gcs_uris[0]
            state.scenario_image_display_url = create_display_url(gcs_uris[0])
            
            # Save MediaItem
            media_item = MediaItem(
                id=str(uuid.uuid4()),
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                media_type="image",
                mode="Character Sheet - Scenario",
                gcs_uris=[state.scenario_image_gcs_uri],
                thumbnail_uri=state.scenario_image_gcs_uri,
                prompt=prompt,
                source_images_gcs=images,
                comment="Generated Character Scenario"
            )
            add_media_item_to_firestore(media_item)
            state.snackbar_message = "Scenario image saved to library."
            state.show_snackbar = True
            
        else:
            state.snackbar_message = "Failed to generate scenario image."
            state.show_snackbar = True
            
    except Exception as ex:
        state.snackbar_message = f"Error: {ex}"
        state.show_snackbar = True
    finally:
        state.is_generating_scenario = False
        yield