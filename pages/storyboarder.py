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
"""Storyboarder Workflow Page."""

import time
import uuid
import datetime
import mesop as me

from common.analytics import log_ui_click, track_model_call
from common.storage import store_to_gcs
from common.utils import create_display_url, https_url_to_gcs_uri
from common.metadata import MediaItem, add_media_item_to_firestore
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from components.snackbar import snackbar
from components.dialog import dialog
from config.default import Default as cfg
from models.gemini import generate_image_from_prompt_and_images, describe_image
from models.veo import generate_video, VideoGenerationRequest
from models.video_processing import process_videos
from state.storyboarder_state import PageState
from state.state import AppState

@me.page(
    path="/storyboarder",
    title="Storyboarder - GenMedia Creative Studio",
)
def page():
    with page_scaffold(page_name="storyboarder"):
        with page_frame():
            header("Storyboarder", "movie_filter")
            storyboarder_content()

def storyboarder_content():
    state = me.state(PageState)
    
    snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)

    with me.box(style=me.Style(display="flex", flex_direction="column", gap=24, padding=me.Padding.all(24))):
        
        # --- Input Section ---
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=16, width="100%", max_width="800px", margin=me.Margin.symmetric(horizontal="auto"))):
            me.text("Create a video storyboard from a prompt.", type="headline-5")
            
            me.textarea(
                label="Storyboard Prompt",
                value=state.prompt,
                on_blur=on_prompt_blur,
                rows=3,
                style=me.Style(width="100%")
            )
            
            with me.box(style=me.Style(display="flex", gap=16, align_items="center")):
                me.select(
                    label="Aspect Ratio",
                    value=state.aspect_ratio,
                    options=[
                        me.SelectOption(label="16:9", value="16:9"),
                        me.SelectOption(label="9:16", value="9:16"),
                        me.SelectOption(label="1:1", value="1:1"),
                    ],
                    on_selection_change=on_aspect_ratio_change
                )
                
                me.button(
                    "Generate Storyboard Images",
                    on_click=on_generate_images_click,
                    type="raised",
                    disabled=state.is_generating_images or not state.prompt
                )
                
                if state.is_generating_images:
                    me.progress_spinner(diameter=24)

        # --- Image Results Section ---
        if state.generated_image_urls:
            me.divider()
            me.text("Storyboard Frames", type="headline-6")
            
            with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=16, justify_content="center")):
                for url in state.generated_image_urls:
                    me.image(
                        src=url,
                        style=me.Style(height="200px", border_radius=8, border=me.Border.all(me.BorderSide(width=1, color="#ccc")))
                    )
            
            # --- Video Generation Controls ---
            with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center", gap=16, margin=me.Margin(top=32))):
                me.button(
                    "Generate Video Sequence",
                    on_click=on_generate_video_click,
                    type="raised",
                    disabled=state.is_generating_video
                )
                
                if state.is_generating_video:
                    with me.box(style=me.Style(display="flex", align_items="center", gap=8)):
                        me.progress_spinner(diameter=24)
                        me.text(state.video_generation_status)

        # --- Final Video Section ---
        if state.final_video_display_url:
            me.divider()
            with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center", gap=16)):
                me.text("Final Storyboard Video", type="headline-5")
                me.video(
                    src=state.final_video_display_url,
                    style=me.Style(width="100%", max_width="800px", border_radius=12)
                )


# --- Event Handlers ---

def on_prompt_blur(e: me.InputEvent):
    state = me.state(PageState)
    state.prompt = e.value

def on_aspect_ratio_change(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.aspect_ratio = e.value

def on_generate_images_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.is_generating_images = True
    state.generated_image_urls = []
    state.generated_image_gcs_uris = []
    state.image_captions = []
    state.final_video_display_url = "" # Reset video
    yield
    
    try:
        gcs_uris, _, captions, _ = generate_image_from_prompt_and_images(
            prompt=state.prompt,
            images=[],
            aspect_ratio=state.aspect_ratio,
            gcs_folder="storyboard_images",
        )
        
        # If we only got 1, let's loop to get more.
        if len(gcs_uris) < 4:
            for _ in range(4 - len(gcs_uris)):
                new_uris, _, new_captions, _ = generate_image_from_prompt_and_images(
                    prompt=state.prompt,
                    images=[],
                    aspect_ratio=state.aspect_ratio,
                    gcs_folder="storyboard_images"
                )
                gcs_uris.extend(new_uris)
                captions.extend(new_captions)
        
        state.generated_image_gcs_uris = gcs_uris[:4] # Limit to 4
        state.image_captions = captions[:4]
        state.generated_image_urls = [create_display_url(uri) for uri in state.generated_image_gcs_uris]
        
    except Exception as ex:
        state.snackbar_message = f"Error generating images: {ex}"
        state.show_snackbar = True
    finally:
        state.is_generating_images = False
        yield

def on_generate_video_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_generating_video = True
    state.video_generation_status = "Initializing..."
    state.generated_video_clips = []
    yield
    
    try:
        # 1. Generate video clips for each image
        for i, image_uri in enumerate(state.generated_image_gcs_uris):
            state.video_generation_status = f"Generating clip {i+1}/{len(state.generated_image_gcs_uris)}..."
            yield
            
            # Construct enhanced prompt
            caption = state.image_captions[i] if i < len(state.image_captions) else ""
            description = describe_image(image_uri)
            
            veo_prompt = f"{state.prompt}. {caption}. {description}"
            print(f"Veo Prompt for clip {i}: {veo_prompt}")
            
            request = VideoGenerationRequest(
                model_version_id="3.1-fast", # Use Veo 3.1 Fast
                reference_image_gcs=image_uri,
                reference_image_mime_type="image/png",
                duration_seconds=4, # 4s is supported
                prompt=veo_prompt, # Use enhanced prompt
                aspect_ratio=state.aspect_ratio,
                video_count=1,
                resolution="720p",
                enhance_prompt=True,
                generate_audio=True,
                person_generation="Allow (Adults only)",
            )
            
            video_uris, _ = generate_video(request)
            if video_uris:
                state.generated_video_clips.append(video_uris[0])
            else:
                print(f"Failed to generate video for image {i}")
        
        # 2. Concatenate
        if state.generated_video_clips:
            state.video_generation_status = "Concatenating clips..."
            yield
            
            final_uri = process_videos(state.generated_video_clips, "concat")
            state.final_video_uri = final_uri
            state.final_video_display_url = create_display_url(final_uri)
            
            # 3. Save to Library
            media_item = MediaItem(
                id=str(uuid.uuid4()),
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                media_type="video",
                mime_type="video/mp4",
                mode="Storyboarder",
                gcs_uris=[final_uri],
                thumbnail_uri=final_uri,
                prompt=state.prompt,
                comment="Generated by Storyboarder",
                source_images_gcs=state.generated_image_gcs_uris,
                captions=state.image_captions,
            )
            add_media_item_to_firestore(media_item)
            
            state.video_generation_status = "Complete!"
            state.snackbar_message = "Storyboard video saved to library!"
            state.show_snackbar = True
        else:
            state.snackbar_message = "Failed to generate any video clips."
            state.show_snackbar = True
            
    except Exception as ex:
        state.snackbar_message = f"Error generating video: {ex}"
        state.show_snackbar = True
    finally:
        state.is_generating_video = False
        yield