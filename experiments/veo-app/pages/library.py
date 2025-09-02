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
"""A library page that displays media items from Firestore."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import mesop as me
from google.cloud import firestore  # Explicitly import for firestore.Query

# Imports from your project structure
from common.metadata import (
    MediaItem,
    config,
    db,
    get_media_for_page,  # This might need adjustment if we want truly accurate filtered counts server-side
    get_media_item_by_id,
)
from components.dialog import (
    dialog,
    dialog_actions,
)
from components.header import header
from components.library.image_details import CarouselState, image_details
from components.page_scaffold import (
    page_frame,
    page_scaffold,
)
from components.pill import pill
from state.state import AppState


@me.stateclass
@dataclass
class PageState:
    """State for the library page."""

    is_loading: bool = False
    current_page: int = 1
    media_per_page: int = 9
    total_media: int = 0
    media_items: List[MediaItem] = field(default_factory=list)
    key: int = 0  # Used to force re-render of the media grid
    show_details_dialog: bool = False
    selected_media_item_id: Optional[str] = None
    dialog_instance_key: int = 0
    selected_values: list[str] = field(
        default_factory=lambda: ["all"]
    )  # Default to "all" media types
    error_filter_value: str = (
        "all"  # New state for error filter: "all", "no_errors", "only_errors"
    )
    user_filter: str = "all"  # New state for user filter: "all", "mine"
    initial_url_param_processed: bool = False
    url_item_not_found_message: Optional[str] = None


def _load_media_and_update_state(pagestate: PageState, is_filter_change: bool = False):
    """Loads media from Firestore and updates the page state.

    Args:
        pagestate: The current page state.
        is_filter_change: Whether the media is being loaded due to a filter change.
    """
    app_state = me.state(AppState)  # Get global app state for user email
    user_email_to_filter = (
        app_state.user_email if pagestate.user_filter == "mine" else None
    )

    if is_filter_change:
        pagestate.current_page = 1  # Reset to first page on any filter change

    # Fetch all items matching current filters to correctly determine total_media for pagination
    # This fetches up to 'fetch_limit' defined in get_media_for_page.
    # For very large datasets, a server-side count with filters would be more performant.
    all_matching_items = get_media_for_page(
        page=1,  # Fetch from page 1
        media_per_page=1000,  # Effectively fetch all matching items up to the internal limit
        type_filters=pagestate.selected_values,
        error_filter=pagestate.error_filter_value,
        filter_by_user_email=user_email_to_filter,
        sort_by_timestamp=True,
    )
    pagestate.total_media = len(all_matching_items)

    # Then fetch just the items for the current page
    pagestate.media_items = get_media_for_page(
        pagestate.current_page,
        pagestate.media_per_page,
        pagestate.selected_values,
        pagestate.error_filter_value,
        filter_by_user_email=user_email_to_filter,
        sort_by_timestamp=True,
    )
    pagestate.key += 1  # Force re-render of the grid


def _item_matches_filters(
    item: MediaItem, pagestate: PageState, app_state: AppState
) -> bool:
    """Checks if a media item matches the current filter state."""
    # User filter check
    if pagestate.user_filter == "mine" and item.user_email != app_state.user_email:
        return False

    # Error filter check
    error_message_present = bool(item.error_message)
    if pagestate.error_filter_value == "no_errors" and error_message_present:
        return False
    if pagestate.error_filter_value == "only_errors" and not error_message_present:
        return False

    # Type filter check
    if "all" not in pagestate.selected_values:
        mime_type = item.raw_data.get("mime_type", "") if item.raw_data else ""
        passes_type_filter = False
        if "videos" in pagestate.selected_values and mime_type.startswith("video/"):
            passes_type_filter = True
        elif "images" in pagestate.selected_values and mime_type.startswith("image/"):
            passes_type_filter = True
        elif "music" in pagestate.selected_values and mime_type.startswith("audio/"):
            passes_type_filter = True

        if not passes_type_filter:
            return False

    return True


def library_content(app_state: me.state):
    """The main content of the library page.

    Args:
        app_state: The global application state.
    """
    pagestate = me.state(PageState)

    if not pagestate.initial_url_param_processed:
        # Load initial data respecting all filters
        _load_media_and_update_state(
            pagestate, is_filter_change=True
        )  # Treat initial load as a filter change for count

        query_params = me.query_params
        media_id_from_url = query_params.get("media_id")

        if media_id_from_url:
            item_in_current_list = next(
                (v for v in pagestate.media_items if v.id == media_id_from_url), None
            )
            if item_in_current_list:
                pagestate.selected_media_item_id = media_id_from_url
                pagestate.show_details_dialog = True
                pagestate.dialog_instance_key += 1
            else:
                fetched_item = get_media_item_by_id(media_id_from_url)
                if fetched_item:
                    # NEW: Check if the fetched item matches current filters before adding
                    if _item_matches_filters(fetched_item, pagestate, app_state):
                        if not any(
                            v.id == fetched_item.id for v in pagestate.media_items
                        ):
                            pagestate.media_items.insert(
                                0, fetched_item
                            )  # Prepend for visibility
                        pagestate.selected_media_item_id = fetched_item.id
                        pagestate.show_details_dialog = True
                        pagestate.dialog_instance_key += 1
                    else:
                        pagestate.url_item_not_found_message = (
                            f"Item '{media_id_from_url}' exists but is hidden by your current filters. "
                            "Try adjusting the 'All Users' or 'Media Type' filters."
                        )
                else:
                    pagestate.url_item_not_found_message = (
                        f"Media item with ID '{media_id_from_url}' not found."
                    )
        pagestate.initial_url_param_processed = True

    total_pages = (
        (pagestate.total_media + pagestate.media_per_page - 1)
        // pagestate.media_per_page
        if pagestate.media_per_page > 0 and pagestate.total_media > 0
        else 1  # Ensure at least 1 page if total_media is 0 to avoid division by zero or 0 pages
    )
    if pagestate.total_media == 0:
        total_pages = 0  # Show 0 pages if no items

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Library", "perm_media")

            if pagestate.url_item_not_found_message:
                with me.box(
                    style=me.Style(
                        padding=me.Padding.all(16),
                        background=me.theme_var("error-container"),
                        color=me.theme_var("on-error-container"),
                        border_radius=8,
                        margin=me.Margin(bottom=16),
                    )
                ):
                    me.text(pagestate.url_item_not_found_message)

            # Filter Toggles Container
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=10,
                    margin=me.Margin(bottom=20),
                    align_items="center",
                )
            ):
                # Media Type Filter
                me.button_toggle(
                    value=pagestate.selected_values,  # This is a list
                    buttons=[
                        me.ButtonToggleButton(label="All Types", value="all"),
                        me.ButtonToggleButton(label="Images", value="images"),
                        me.ButtonToggleButton(label="Videos", value="videos"),
                        me.ButtonToggleButton(label="Music", value="music"),
                    ],
                    multiple=True,
                    on_change=on_change_selected_type_filters,
                )
                # Error Message Filter
                me.button_toggle(
                    value=pagestate.error_filter_value,  # This is a string
                    buttons=[
                        me.ButtonToggleButton(label="Show All", value="all"),
                        me.ButtonToggleButton(label="No Errors", value="no_errors"),
                        me.ButtonToggleButton(label="Only Errors", value="only_errors"),
                    ],
                    on_change=on_change_error_filter,
                    # multiple=False is default for single value
                )
                # User Filter
                me.button_toggle(
                    value=pagestate.user_filter,
                    buttons=[
                        me.ButtonToggleButton(label="All Users", value="all"),
                        me.ButtonToggleButton(label="Mine Only", value="mine"),
                    ],
                    on_change=on_change_user_filter,
                )
                with (
                    me.content_button(
                        type="icon",
                        on_click=on_refresh_click,
                        style=me.Style(margin=me.Margin(left="auto")),
                    ),
                    me.tooltip(message="Refresh Library"),
                ):
                    me.icon(icon="refresh")

            with me.box(
                key=str(pagestate.key),  # Refreshes the grid when key changes
                style=me.Style(
                    display="grid",
                    grid_template_columns="repeat(auto-fill, minmax(300px, 1fr))",
                    gap="16px",
                    width="100%",
                ),
            ):
                if pagestate.is_loading and not pagestate.show_details_dialog:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            justify_content="center",
                            padding=me.Padding.all(20),
                        )
                    ):
                        me.progress_spinner()
                elif not pagestate.media_items:
                    with me.box(
                        style=me.Style(padding=me.Padding.all(20), text_align="center")
                    ):
                        me.text("No media items found for the selected filters.")
                else:
                    for i, m_item in enumerate(pagestate.media_items):
                        mime_type = (
                            m_item.raw_data.get("mime_type", "")
                            if m_item.raw_data
                            else ""
                        )
                        media_type_group = ""
                        if mime_type.startswith("video/"):
                            media_type_group = "video"
                        elif mime_type.startswith("image/"):
                            media_type_group = "image"
                        elif mime_type.startswith("audio/"):
                            media_type_group = "audio"

                        item_url = (
                            m_item.gcsuri.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            )
                            if m_item.gcsuri
                            else (
                                m_item.gcs_uris[0].replace(
                                    "gs://", "https://storage.mtls.cloud.google.com/"
                                )
                                if m_item.gcs_uris
                                else ""
                            )
                        )

                        if media_type_group == "image":
                            prompt_full = m_item.rewritten_prompt or m_item.prompt or ""
                        else:
                            prompt_full = m_item.prompt or ""
                        prompt_display_grid = (
                            (prompt_full[:100] + "...")
                            if len(prompt_full) > 100
                            else prompt_full
                        )

                        timestamp_display_str = "N/A"
                        if m_item.timestamp:
                            try:
                                # Ensure timestamp is a string before parsing
                                ts_str = m_item.timestamp
                                if isinstance(
                                    m_item.timestamp, datetime
                                ):  # Should not happen if MediaItem.timestamp is str
                                    ts_str = m_item.timestamp.isoformat()

                                timestamp_display_str = datetime.fromisoformat(
                                    ts_str.replace("Z", "+00:00")  # Handle Z for UTC
                                ).strftime("%Y-%m-%d %H:%M")
                            except (ValueError, TypeError) as e_ts:
                                # print(f"Timestamp parsing error for '{m_item.timestamp}': {e_ts}")
                                timestamp_display_str = str(
                                    m_item.timestamp
                                )  # Fallback to string if parsing fails

                        item_duration_str = (
                            f"{m_item.duration} sec"
                            if m_item.duration is not None
                            else "N/A"
                        )

                        with me.box(
                            key=m_item.id,  # Use item ID if available and unique, otherwise index is fine for local list
                            # key=m_item.id or str(i), # Prefer item ID for key if stable
                            on_click=on_media_item_click,
                            style=me.Style(
                                padding=me.Padding.all(16),
                                display="flex",
                                flex_direction="column",
                                width="100%",
                                gap=10,
                                cursor="pointer",
                                border=me.Border.all(
                                    me.BorderSide(
                                        width=1, color=me.theme_var("outline-variant")
                                    )
                                ),
                                border_radius=12,
                                background=me.theme_var("surface-container-low"),
                            ),
                        ):
                            me.text(
                                f"Generated: {timestamp_display_str}",
                                style=me.Style(
                                    font_weight="bold",
                                    font_size="0.9em",
                                    color=me.theme_var("onsecondarycontainer"),
                                ),
                            )

                            # Pills section
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_wrap="wrap",
                                    gap=5,
                                    margin=me.Margin(bottom=8),
                                )
                            ):
                                if media_type_group == "video":
                                    pill("Video", "media_type_video")
                                    pill(
                                        "t2v" if not m_item.reference_image else "i2v",
                                        "gen_t2v"
                                        if not m_item.reference_image
                                        else "gen_i2v",
                                    )
                                    if m_item.aspect:
                                        pill(m_item.aspect, "aspect")
                                    if m_item.duration is not None:
                                        pill(item_duration_str, "duration")
                                    if m_item.resolution:
                                        pill(m_item.resolution, "resolution")
                                    pill("24 fps", "fps")
                                    if (
                                        m_item.enhanced_prompt_used
                                        and media_type_group == "video"
                                    ):
                                        with me.tooltip(
                                            message="Prompt was auto-enhanced"
                                        ):
                                            me.icon(
                                                "auto_fix_normal",
                                                style=me.Style(
                                                    color=me.theme_var("primary")
                                                ),
                                            )

                                elif media_type_group == "image":
                                    pill("Image", "media_type_image")
                                    if m_item.aspect:
                                        pill(m_item.aspect, "aspect")
                                    if len(m_item.gcs_uris) > 1:
                                        pill(str(len(m_item.gcs_uris)), "multi_image_count")

                                elif media_type_group == "audio":
                                    pill("Audio", "media_type_audio")
                                    if m_item.duration is not None:
                                        pill(item_duration_str, "duration")

                                    if m_item.rewritten_prompt is not None:
                                        with me.tooltip(
                                            message="Custom prompt rewriter"
                                        ):
                                            me.icon(
                                                "auto_fix_normal",
                                                style=me.Style(
                                                    color=me.theme_var("primary")
                                                ),
                                            )

                                # Pill for error message
                                if m_item.error_message:
                                    pill(
                                        "Error",
                                        "error_present",
                                    )

                            me.text(
                                f'"{prompt_display_grid}"'
                                if prompt_display_grid
                                else "No prompt provided",
                                style=me.Style(
                                    font_size="10pt",
                                    font_style="italic"
                                    if prompt_display_grid
                                    else "normal",
                                    min_height="40px",  # Ensure consistent height
                                ),
                            )

                            # Media Preview Section
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_direction="row",  # Changed to row for side-by-side potential
                                    gap=8,
                                    align_items="center",  # Align items vertically in center
                                    justify_content="center",  # Center content horizontally
                                    margin=me.Margin(top=8, bottom=8),
                                    min_height="150px",  # Ensure consistent height for preview area
                                )
                            ):
                                if m_item.error_message:
                                    # Display error message prominently if it exists, instead of media
                                    me.text(
                                        f"Error: {m_item.error_message}",
                                        style=me.Style(
                                            width="100%",  # Take full width of the preview area
                                            font_style="italic",
                                            font_size="10pt",
                                            margin=me.Margin.all(3),
                                            padding=me.Padding.all(8),
                                            border=me.Border.all(
                                                me.BorderSide(
                                                    style="solid",
                                                    width=1,
                                                    color=me.theme_var("error"),
                                                )
                                            ),
                                            border_radius=5,
                                            background=me.theme_var(
                                                "error-container"
                                            ),  # Corrected theme var
                                            color=me.theme_var(
                                                "on-error-container"
                                            ),  # Corrected theme var
                                        ),
                                    )
                                else:  # Only show media preview if no error
                                    if media_type_group == "video" and item_url:
                                        me.video(
                                            src=item_url,
                                            style=me.Style(
                                                width="100%",  # Take full width
                                                height="150px",  # Fixed height for consistency
                                                border_radius=6,
                                                object_fit="cover",
                                            ),
                                        )
                                    elif media_type_group == "image" and item_url:
                                        me.image(
                                            src=item_url,
                                            # alt_text=m_item.prompt or "Generated Image",
                                            style=me.Style(
                                                max_width="100%",  # Ensure it doesn't overflow
                                                max_height="150px",  # Max height for consistency
                                                height="auto",  # Maintain aspect ratio
                                                border_radius=6,
                                                object_fit="contain",  # Use contain to see whole image
                                            ),
                                        )
                                    elif media_type_group == "audio" and item_url:
                                        me.audio(
                                            src=item_url,
                                            # style=me.Style(width="100%"), # Audio player width
                                        )
                                    else:  # Fallback if no URL or unknown type (and no error)
                                        me.text(
                                            f"{media_type_group.capitalize() if media_type_group else 'Media'} not available.",
                                            style=me.Style(
                                                height="150px",
                                                display="flex",
                                                align_items="center",
                                                justify_content="center",
                                                color=me.theme_var("onsurfacevariant"),
                                            ),
                                        )

                                # Reference images for video (only if no error)
                                if (
                                    media_type_group == "video"
                                    and not m_item.error_message
                                ):
                                    with me.box(
                                        style=me.Style(
                                            display="flex",
                                            flex_direction="column",  # Stack reference images
                                            gap=5,
                                            # margin=me.Margin(left=8) # Add some space if side-by-side with video
                                        )
                                    ):
                                        if m_item.reference_image:
                                            ref_img_url = m_item.reference_image.replace(
                                                "gs://",
                                                "https://storage.mtls.cloud.google.com/",
                                            )
                                            me.image(
                                                src=ref_img_url,
                                                style=me.Style(
                                                    height="70px",  # Smaller reference images
                                                    width="auto",
                                                    border_radius=4,
                                                    object_fit="contain",
                                                ),
                                            )
                                        if m_item.last_reference_image:
                                            last_ref_img_url = m_item.last_reference_image.replace(
                                                "gs://",
                                                "https://storage.mtls.cloud.google.com/",
                                            )
                                            me.image(
                                                src=last_ref_img_url,
                                                style=me.Style(
                                                    height="70px",
                                                    width="auto",
                                                    border_radius=4,
                                                    object_fit="contain",
                                                ),
                                            )
                            # Generation time
                            if m_item.generation_time is not None:
                                me.text(
                                    f"Generated in {round(m_item.generation_time)} seconds.",
                                    style=me.Style(
                                        font_size="0.8em",
                                        color=me.theme_var("onsurfacevariant"),
                                    ),
                                )
            # Dialog for Media Details
            library_dialog_style = me.Style(
                max_width="80vw",
                width="80vw",
                min_width="600px",  # Responsive width
            )
            with dialog(  # pylint: disable=not-context-manager
                key=str(pagestate.dialog_instance_key),
                is_open=pagestate.show_details_dialog,
                dialog_style=library_dialog_style,
            ):
                item_to_display: Optional[MediaItem] = None
                if pagestate.selected_media_item_id:
                    # Try to find in current list first
                    item_to_display = next(
                        (
                            v
                            for v in pagestate.media_items
                            if v.id == pagestate.selected_media_item_id
                        ),
                        None,
                    )
                    # If not found (e.g., direct URL access to an item not on current page/filters)
                    # This case is partially handled by initial load, but good to have a fallback.
                    # if not item_to_display:
                    # item_to_display = get_media_item_by_id(pagestate.selected_media_item_id)

                if item_to_display:
                    item = item_to_display

                    dialog_mime_type = (
                        item.raw_data.get("mime_type", "") if item.raw_data else ""
                    )
                    dialog_media_type_group = ""
                    if dialog_mime_type.startswith("video/"):
                        dialog_media_type_group = "video"
                    elif dialog_mime_type.startswith("image/"):
                        dialog_media_type_group = "image"
                    elif dialog_mime_type.startswith("audio/"):
                        dialog_media_type_group = "audio"

                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="column",
                            gap=12,
                            width="100%",
                            max_height="80vh",  # Max viewport height
                            overflow_y="auto",  # Scroll if content exceeds max height
                            padding=me.Padding.all(24),
                        )
                    ):
                        me.text(
                            "Media Details",
                            style=me.Style(
                                font_size="1.5rem",
                                font_weight="bold",
                                margin=me.Margin(bottom=16),
                                color=me.theme_var("on-surface-variant"),
                                flex_shrink=0,  # Prevent title from shrinking
                            ),
                        )

                        item_display_url = (
                            item.gcsuri.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            )
                            if item.gcsuri
                            else (
                                item.gcs_uris[0].replace(
                                    "gs://", "https://storage.mtls.cloud.google.com/"
                                )
                                if item.gcs_uris
                                else ""
                            )
                        )
                        if (
                            item.media_type == "character_consistency"
                            and item.best_candidate_image
                        ):
                            me.video(
                                src=item_display_url,
                                style=me.Style(
                                    width="100%",
                                    max_height="40vh",
                                    border_radius=8,
                                    background="#000",
                                    display="block",
                                    margin=me.Margin(bottom=16),
                                ),
                            )
                            best_candidate_url = item.best_candidate_image.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            )
                            me.text(
                                "Best Candidate Image:",
                                style=me.Style(
                                    font_weight="500", margin=me.Margin(top=8)
                                ),
                            )
                            me.image(
                                src=best_candidate_url,
                                style=me.Style(
                                    max_width="250px",
                                    height="auto",
                                    border_radius=6,
                                    margin=me.Margin(top=4),
                                ),
                            )
                        elif dialog_media_type_group == "image":
                            image_details(item)
                        elif (
                            dialog_media_type_group == "video"
                            and item_display_url
                            and not item.error_message
                        ):
                            me.video(
                                src=item_display_url,
                                style=me.Style(
                                    width="100%",
                                    max_height="40vh",
                                    border_radius=8,
                                    background="#000",  # Background for video player
                                    display="block",  # Ensure it takes block space
                                    margin=me.Margin(bottom=16),
                                ),
                            )
                        elif (
                            dialog_media_type_group == "audio"
                            and item_display_url
                            and not item.error_message
                        ):
                            me.audio(
                                src=item_display_url,
                                # style=me.Style(width="100%", margin=me.Margin(top=8, bottom=16))
                            )

                        if item.error_message:
                            me.text(
                                f"Error: {item.error_message}",
                                style=me.Style(
                                    color=me.theme_var("error"),
                                    font_style="italic",
                                    padding=me.Padding.all(8),
                                    background=me.theme_var("error-container"),
                                    border_radius=4,
                                    margin=me.Margin(bottom=10),
                                ),
                            )

                        me.text(f"Model: {item.raw_data['model']}")

                        if dialog_media_type_group != "image":
                            me.text(f'Prompt: "{item.prompt or "N/A"}"')
                            if item.negative_prompt:
                                me.text(f'Negative Prompt: "{item.negative_prompt}"')
                            if item.enhanced_prompt_used:
                                me.text(
                                    f'Enhanced Prompt: "{item.enhanced_prompt_used}"'
                                )

                        dialog_timestamp_str_detail = "N/A"
                        if item.timestamp:
                            try:
                                ts_str_detail = item.timestamp
                                if isinstance(item.timestamp, datetime):
                                    ts_str_detail = item.timestamp.isoformat()
                                dialog_timestamp_str_detail = datetime.fromisoformat(
                                    ts_str_detail.replace("Z", "+00:00")
                                ).strftime(
                                    "%Y-%m-%d %H:%M:%S %Z"
                                )  # More detailed timestamp
                            except Exception:
                                dialog_timestamp_str_detail = str(item.timestamp)
                        me.text(f"Generated: {dialog_timestamp_str_detail}")

                        if item.generation_time is not None:
                            me.text(
                                f"Generation Time: {round(item.generation_time, 2)} seconds"
                            )

                        if item.model is not None:
                            me.text(f"Model: {item.model}")

                        if (
                            dialog_media_type_group == "video"
                            or dialog_media_type_group == "image"
                        ):
                            if item.aspect:
                                me.text(f"Aspect Ratio: {item.aspect}")
                        if (
                            dialog_media_type_group == "video"
                            or dialog_media_type_group == "audio"
                        ):
                            if item.duration is not None:
                                me.text(f"Duration: {item.duration} seconds")

                        if dialog_media_type_group == "video":
                            me.text(f"Resolution: {item.resolution or '720p'}")

                        if dialog_media_type_group == "video":
                            if item.reference_image:
                                ref_url = item.reference_image.replace(
                                    "gs://", "https://storage.mtls.cloud.google.com/"
                                )
                                me.text(
                                    "Reference Image:",
                                    style=me.Style(
                                        font_weight="500",
                                        margin=me.Margin(
                                            top=8
                                        ),  # medium is not a valid value
                                    ),
                                )
                                me.image(
                                    src=ref_url,
                                    style=me.Style(
                                        max_width="250px",
                                        height="auto",
                                        border_radius=6,
                                        margin=me.Margin(top=4),
                                    ),
                                )
                            if item.last_reference_image:
                                last_ref_url = item.last_reference_image.replace(
                                    "gs://", "https://storage.mtls.cloud.google.com/"
                                )
                                me.text(
                                    "Last Reference Image:",
                                    style=me.Style(
                                        font_weight="500", margin=me.Margin(top=8)
                                    ),
                                )
                                me.image(
                                    src=last_ref_url,
                                    style=me.Style(
                                        max_width="250px",
                                        height="auto",
                                        border_radius=6,
                                        margin=me.Margin(top=4),
                                    ),
                                )
                        elif (
                            item.media_type == "character_consistency"
                            and item.best_candidate_image
                        ):
                            print("I'm in character consistency")
                            best_candidate_url = item.best_candidate_image.replace(
                                "gs://", "https://storage.mtls.cloud.google.com/"
                            )
                            me.text(
                                "Best Candidate Image:",
                                style=me.Style(
                                    font_weight="500", margin=me.Margin(top=8)
                                ),
                            )
                            me.image(
                                src=best_candidate_url,
                                style=me.Style(
                                    max_width="250px",
                                    height="auto",
                                    border_radius=6,
                                    margin=me.Margin(top=4),
                                ),
                            )
                            if item.source_character_images:
                                me.text(
                                    "Source Images:",
                                    style=me.Style(
                                        font_weight="500", margin=me.Margin(top=8)
                                    ),
                                )
                                with me.box(
                                    style=me.Style(
                                        display="flex", flex_direction="row", gap=10
                                    )
                                ):
                                    for src_image_uri in item.source_character_images[
                                        :3
                                    ]:
                                        src_url = src_image_uri.replace(
                                            "gs://",
                                            "https://storage.mtls.cloud.google.com/",
                                        )
                                        me.image(
                                            src=src_url,
                                            style=me.Style(
                                                max_width="150px",
                                                height="auto",
                                                border_radius=6,
                                                margin=me.Margin(top=4),
                                            ),
                                        )

                        with me.content_button(
                            on_click=on_click_set_permalink,
                            key=item.id or "",  # Ensure key is not None
                        ):
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_direction="row",
                                    align_items="center",
                                    gap=5,
                                )
                            ):
                                me.icon(icon="link")
                                me.text("permalink")

                        if item.raw_data:
                            with me.expansion_panel(
                                key="raw_metadata_panel_dialog",  # Unique key for dialog panel
                                title="Firestore Metadata",
                                description=item.id or "N/A",
                                icon="dataset",
                            ):
                                try:
                                    json_string = json.dumps(
                                        item.raw_data,
                                        indent=2,
                                        default=str,  # Use default=str for non-serializable
                                    )
                                    me.markdown(f"```json\n{json_string}\n```")
                                except Exception as e_json:
                                    print(
                                        f"Error serializing raw_data to JSON in dialog: {e_json}"
                                    )
                                    me.text(
                                        "Could not display raw data (serialization error)."
                                    )
                        else:
                            me.text("Raw Firestore data not available.")
                else:
                    with me.box(style=me.Style(padding=me.Padding.all(16))):
                        me.text("No media item selected or found for the given ID.")

                me.button(
                    "Close",
                    on_click=on_close_details_dialog,
                    type="flat",
                    style=me.Style(margin=me.Margin(top=24)),
                )

            # Pagination controls
            if total_pages > 1:
                with me.box(
                    style=me.Style(
                        display="flex",
                        justify_content="center",
                        align_items="center",
                        gap=16,
                        margin=me.Margin(top=24, bottom=24),
                    )
                ):
                    me.button(
                        "Previous",
                        key="-1",  # Key for direction
                        on_click=handle_page_change,
                        disabled=pagestate.current_page == 1 or pagestate.is_loading,
                        type="stroked",
                    )
                    me.text(f"Page {pagestate.current_page} of {total_pages}")
                    me.button(
                        "Next",
                        key="1",  # Key for direction
                        on_click=handle_page_change,
                        disabled=pagestate.current_page == total_pages
                        or pagestate.is_loading,
                        type="stroked",
                    )


def on_click_set_permalink(e: me.ClickEvent):
    """set the permalink from dialog"""
    if e.key:  # Ensure key is not None or empty
        me.query_params["media_id"] = e.key


def on_media_item_click(e: me.ClickEvent):
    pagestate = me.state(PageState)
    item_id = e.key
    clicked_item = next(
        (item for item in pagestate.media_items if item.id == item_id), None
    )

    if clicked_item:
        pagestate.selected_media_item_id = clicked_item.id
        pagestate.show_details_dialog = True
        pagestate.dialog_instance_key += 1
        pagestate.url_item_not_found_message = None  # Clear any old not found message
    else:
        print(f"Error: Could not find media item with ID '{item_id}' in the current list.")
    yield


def on_close_details_dialog(e: me.ClickEvent):
    pagestate = me.state(PageState)
    carousel_state = me.state(CarouselState)  # Get the state

    pagestate.show_details_dialog = False
    pagestate.selected_media_item_id = None
    pagestate.url_item_not_found_message = (
        None  # Clear message when dialog is closed by user
    )
    carousel_state.current_index = 0  # Reset the index

    # Optionally, clear media_id from URL params if desired
    # if "media_id" in me.query_params:
    #    del me.query_params["media_id"]
    yield


def handle_page_change(e: me.ClickEvent):
    pagestate = me.state(PageState)
    if pagestate.is_loading:
        yield
        return

    pagestate.is_loading = True
    yield  # Show loading spinner

    direction = int(e.key)
    new_page = pagestate.current_page + direction

    # No need to recalculate total_pages here if total_media is up-to-date
    # It's calculated at the start of library_content

    if (
        1
        <= new_page
        <= (
            (pagestate.total_media + pagestate.media_per_page - 1)
            // pagestate.media_per_page
            if pagestate.media_per_page > 0 and pagestate.total_media > 0
            else 1
        )
    ):
        app_state = me.state(AppState)
        user_email_to_filter = (
            app_state.user_email if pagestate.user_filter == "mine" else None
        )
        pagestate.current_page = new_page
        # Fetch only the items for the new page with current filters
        pagestate.media_items = get_media_for_page(
            pagestate.current_page,
            pagestate.media_per_page,
            pagestate.selected_values,
            pagestate.error_filter_value,
            filter_by_user_email=user_email_to_filter,
            sort_by_timestamp=True,
        )
        pagestate.key += 1  # Refresh grid
        pagestate.url_item_not_found_message = None

    pagestate.is_loading = False
    yield


def on_change_selected_type_filters(e: me.ButtonToggleChangeEvent):
    pagestate = me.state(PageState)
    new_filters = e.values

    if not new_filters:  # If all are deselected
        pagestate.selected_values = ["all"]  # Default to "all"
    elif "all" in new_filters and len(new_filters) > 1:
        # If "all" is selected along with specific types, prioritize specific types
        pagestate.selected_values = [val for val in new_filters if val != "all"]
    elif "all" in new_filters and len(new_filters) == 1:
        pagestate.selected_values = ["all"]
    else:
        pagestate.selected_values = new_filters

    pagestate.url_item_not_found_message = None
    pagestate.is_loading = True
    yield

    _load_media_and_update_state(pagestate, is_filter_change=True)

    pagestate.is_loading = False
    yield


def on_change_error_filter(e: me.ButtonToggleChangeEvent):
    """Handles changes to the error message filter."""
    pagestate = me.state(PageState)
    pagestate.error_filter_value = e.value  # This is a single string value

    pagestate.url_item_not_found_message = None
    pagestate.is_loading = True
    yield

    _load_media_and_update_state(pagestate, is_filter_change=True)

    pagestate.is_loading = False
    yield


def on_change_user_filter(e: me.ButtonToggleChangeEvent):
    """Handles changes to the user filter."""
    pagestate = me.state(PageState)
    pagestate.user_filter = e.value

    pagestate.url_item_not_found_message = None
    pagestate.is_loading = True
    yield

    _load_media_and_update_state(pagestate, is_filter_change=True)

    pagestate.is_loading = False
    yield


def on_refresh_click(e: me.ClickEvent):
    """Handles the click event for the refresh button."""
    pagestate = me.state(PageState)
    pagestate.is_loading = True
    yield

    _load_media_and_update_state(pagestate, is_filter_change=True)

    pagestate.is_loading = False
    yield


@me.page(
    path="/library",
    title="GenMedia Studio - Library",
)
def page():
    """The main entry point for the library page."""
    app_state = me.state(AppState)
    with me.box(style=me.Style(display="flex", flex_direction="row")):
        library_content(app_state)
