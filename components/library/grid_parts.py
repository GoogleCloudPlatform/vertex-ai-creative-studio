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
"""Reusable parts for the library grid items."""

import mesop as me
from common.metadata import MediaItem
from common.utils import gcs_uri_to_https_url
from components.pill import pill
from ..video_thumbnail.video_thumbnail import video_thumbnail


@me.component
def render_video_pills(item: MediaItem):
    """Renders the pills for a video item."""
    item_duration_str = f"{item.duration} sec" if item.duration is not None else "N/A"

    pill("Video", "media_type_video")
    if item.gcs_uris and len(item.gcs_uris) > 1:
        pill(f"{len(item.gcs_uris)}", "multi_video")
    pill(
        "t2v" if not item.reference_image else "i2v",
        "gen_t2v" if not item.reference_image else "gen_i2v",
    )
    if item.aspect:
        pill(item.aspect, "aspect")
    if item.duration is not None:
        pill(item_duration_str, "duration")
    if item.resolution:
        pill(item.resolution, "resolution_4k" if item.resolution == "4k" else "resolution")
    pill("24 fps", "fps")
    if item.enhanced_prompt_used:
        with me.tooltip(message="Prompt was auto-enhanced"):
            me.icon(
                "auto_fix_normal",
                style=me.Style(color=me.theme_var("primary")),
            )


@me.component
def render_image_pills(item: MediaItem):
    """Renders the pills for an image item."""
    pill("Image", "media_type_image")
    if item.aspect:
        pill(item.aspect, "aspect")
    if len(item.gcs_uris) > 1:
        pill(str(len(item.gcs_uris)), "multi_image_count")


@me.component
def render_audio_pills(item: MediaItem):
    """Renders the pills for an audio item."""
    item_duration_str = f"{item.duration} sec" if item.duration is not None else "N/A"
    pill("Audio", "media_type_audio")
    if item.duration is not None:
        pill(item_duration_str, "duration")

    if item.rewritten_prompt is not None:
        with me.tooltip(message="Custom prompt rewriter"):
            me.icon(
                "auto_fix_normal",
                style=me.Style(color=me.theme_var("primary")),
            )


@me.component
def render_video_preview(item: MediaItem, item_url: str):
    """Renders the preview for a video item."""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            gap=8,
            align_items="center",
            justify_content="center",
            margin=me.Margin(top=8, bottom=8),
            height="150px",  # Set a fixed height for the container
        )
    ):
        if item_url:
            # Use the new, robust video_thumbnail component
            with me.box(style=me.Style(width="100%", height="100%")): # Add a sized wrapper
                video_thumbnail(
                    video_src=item_url,
                    # This component is not selectable in the grid, so on_click is not set
                )
        else:
            me.text(
                "Video not available.",
                style=me.Style(
                    height="150px", # Match the container height
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    color=me.theme_var("onsurfacevariant"),
                ),
            )

        # Reference images for video
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                gap=5,
            )
        ):
            if item.reference_image:
                ref_img_url = gcs_uri_to_https_url(item.reference_image)
                me.image(
                    src=ref_img_url,
                    style=me.Style(
                        height="70px",
                        width="auto",
                        border_radius=4,
                        object_fit="contain",
                    ),
                )
            if item.last_reference_image:
                last_ref_img_url = gcs_uri_to_https_url(item.last_reference_image)
                me.image(
                    src=last_ref_img_url,
                    style=me.Style(
                        height="70px",
                        width="auto",
                        border_radius=4,
                        object_fit="contain",
                    ),
                )

@me.component
def render_image_preview(item: MediaItem, item_url: str):
    """Renders the preview for an image item."""
    if item_url:
        me.image(
            src=item_url,
            style=me.Style(
                max_width="100%",
                max_height="150px",
                height="auto",
                border_radius=6,
                object_fit="contain",
            ),
        )
    else:
        me.text(
            "Image not available.",
            style=me.Style(
                height="150px",
                display="flex",
                align_items="center",
                justify_content="center",
                color=me.theme_var("onsurfacevariant"),
            ),
        )

@me.component
def render_audio_preview(item: MediaItem, item_url: str):
    """Renders the preview for an audio item."""
    if item_url:
        me.audio(
            src=item_url,
        )
    else:
        me.text(
            "Audio not available.",
            style=me.Style(
                height="150px",
                display="flex",
                align_items="center",
                justify_content="center",
                color=me.theme_var("onsurfacevariant"),
            ),
        )