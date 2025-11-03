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
"""A test library page using the new media_tile component."""

import json
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import datetime

import mesop as me
from common.analytics import log_ui_click

from common.metadata import MediaItem, get_media_for_page, get_media_item_by_id
from common.utils import gcs_uri_to_https_url, https_url_to_gcs_uri
from components.header import header
from components.lightbox_dialog.lightbox_dialog import lightbox_dialog
from components.library.image_details import CarouselState
from components.media_detail_viewer.media_detail_viewer import media_detail_viewer
from components.media_tile.media_tile import media_tile, get_pills_for_item
from components.page_scaffold import page_frame, page_scaffold
from components.dialog import dialog
from components.interior_design.storyboard_video_tile import storyboard_video_tile
from components.scroll_sentinel.scroll_sentinel import scroll_sentinel
from state.state import AppState


@me.stateclass
@dataclass
class PageState:
    """State for the library page."""

    is_loading: bool = True
    media_items: List[MediaItem] = field(default_factory=list)
    show_details_dialog: bool = False
    selected_media_item_id: Optional[str] = None
    initial_load_complete: bool = False
    current_page: int = 1
    all_items_loaded: bool = False
    user_filter: str = "mine"  # "all" or "mine"
    type_filters: list[str] = field(
        default_factory=lambda: ["all"]
    )  # "all", "images", "videos", "audio"
    error_filter: str = "all"  # "all", "no_errors", "only_errors"


def on_load(e: me.LoadEvent):
    """Handles page load events for permalinks and initial data fetch."""
    pagestate = me.state(PageState)
    if not pagestate.initial_load_complete:
        yield from _load_media(pagestate, is_filter_change=True)
        pagestate.initial_load_complete = True

        media_id = me.query_params.get("media_id")
        if media_id:
            item = next((i for i in pagestate.media_items if i.id == media_id), None)
            if not item:
                item = get_media_item_by_id(media_id)
                if item:
                    pagestate.media_items.insert(0, item)

            if item:
                pagestate.selected_media_item_id = media_id
                pagestate.show_details_dialog = True
    yield


def _load_media(pagestate: PageState, is_filter_change: bool = False):
    """Central function to load media based on current filters and pagination."""
    app_state = me.state(AppState)
    user_email_to_filter = (
        app_state.user_email if pagestate.user_filter == "mine" else None
    )

    if is_filter_change:
        pagestate.current_page = 1
        pagestate.media_items = []
        pagestate.all_items_loaded = False

    pagestate.is_loading = True
    yield

    new_items = get_media_for_page(
        page=pagestate.current_page,
        media_per_page=20,
        sort_by_timestamp=True,
        type_filters=pagestate.type_filters,
        filter_by_user_email=user_email_to_filter,
        error_filter=pagestate.error_filter,
    )

    if not new_items:
        pagestate.all_items_loaded = True
    else:
        if is_filter_change:
            pagestate.media_items = new_items
        else:
            pagestate.media_items.extend(new_items)

    pagestate.is_loading = False
    yield


def on_load_more(e: me.WebEvent):
    """Event handler for infinite scroll, fetches the next page of items."""
    pagestate = me.state(PageState)
    if pagestate.is_loading or pagestate.all_items_loaded:
        return

    pagestate.current_page += 1
    yield from _load_media(pagestate)


def on_user_filter_change(e: me.ButtonToggleChangeEvent):
    """Handles changes to the user filter."""
    pagestate = me.state(PageState)
    pagestate.user_filter = e.value
    yield from _load_media(pagestate, is_filter_change=True)


def on_type_filter_change(e: me.ButtonToggleChangeEvent):
    """Handles changes to the media type filter."""
    pagestate = me.state(PageState)
    new_filters = e.values
    if not new_filters:
        pagestate.type_filters = ["all"]
    elif "all" in new_filters and len(new_filters) > 1:
        pagestate.type_filters = [val for val in new_filters if val != "all"]
    else:
        pagestate.type_filters = new_filters
    yield from _load_media(pagestate, is_filter_change=True)


def on_error_filter_change(e: me.ButtonToggleChangeEvent):
    """Handles changes to the error filter."""
    pagestate = me.state(PageState)
    pagestate.error_filter = e.value
    yield from _load_media(pagestate, is_filter_change=True)


@me.page(
    path="/library_v2",
    title="GenMedia Creative Studio - Library",
    on_load=on_load,
)
def page():
    """Main Page."""
    with page_scaffold(page_name="library"):  # pylint: disable=E1129:not-context-manager
        library_content()  # pylint: disable=E1129:not-context-manager


def library_content():
    """The main content of the library page."""
    pagestate = me.state(PageState)

    with page_frame():  # pylint: disable=E1129:not-context-manager
        header("Library", "perm_media")

        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=10,
                margin=me.Margin(bottom=20),
            )
        ):
            me.button_toggle(
                value=pagestate.type_filters,
                buttons=[
                    me.ButtonToggleButton(label="All Types", value="all"),
                    me.ButtonToggleButton(label="Images", value="images"),
                    me.ButtonToggleButton(label="Videos", value="videos"),
                    me.ButtonToggleButton(label="Audio", value="audio"),
                ],
                multiple=True,
                on_change=on_type_filter_change,
            )
            me.button_toggle(
                value=pagestate.user_filter,
                buttons=[
                    me.ButtonToggleButton(label="All Users", value="all"),
                    me.ButtonToggleButton(label="Mine Only", value="mine"),
                ],
                on_change=on_user_filter_change,
            )
            me.button_toggle(
                value=pagestate.error_filter,
                buttons=[
                    me.ButtonToggleButton(label="Show All", value="all"),
                    me.ButtonToggleButton(label="No Errors", value="no_errors"),
                    me.ButtonToggleButton(label="Only Errors", value="only_errors"),
                ],
                on_change=on_error_filter_change,
            )

        with me.box(
            style=me.Style(
                display="grid",
                grid_template_columns="repeat(auto-fill, minmax(300px, 1fr))",
                gap="16px",
                width="100%",
            )
        ):
            if not pagestate.media_items and not pagestate.is_loading:
                with me.box(
                    style=me.Style(padding=me.Padding.all(20), text_align="center")
                ):
                    me.text("No media items found for the selected filters.")
            else:
                for item in pagestate.media_items:
                    gcs_uri = (
                        item.gcsuri
                        if item.gcsuri
                        else (item.gcs_uris[0] if item.gcs_uris else None)
                    )
                    https_url = gcs_uri_to_https_url(gcs_uri) if gcs_uri else ""

                    # Determine the render type based on mime_type for reliability
                    render_type = "image" # Default to image
                    if item.mime_type:
                        if item.mime_type.startswith("video/"):
                            render_type = "video"
                        elif item.mime_type.startswith("audio/"):
                            render_type = "audio"
                    # Fallback to URL check if mime_type is missing
                    elif https_url:
                        if ".mp4" in https_url or ".webm" in https_url:
                            render_type = "video"
                        elif ".wav" in https_url or ".mp3" in https_url:
                            render_type = "audio"

                    media_tile(
                        key=item.id,
                        on_click=on_media_item_click,
                        media_type=render_type,
                        https_url=https_url,
                        pills_json=get_pills_for_item(item, https_url),
                    )

        scroll_sentinel(
            on_visible=on_load_more,
            is_loading=pagestate.is_loading,
            all_items_loaded=pagestate.all_items_loaded,
        )

        library_dialog(pagestate)


def on_media_item_click(e: me.ClickEvent):
    """Saves the selected item's ID to the state and opens the dialog."""
    pagestate = me.state(PageState)
    pagestate.selected_media_item_id = e.key
    pagestate.show_details_dialog = True
    yield


@me.component
def library_dialog(pagestate: PageState):
    """
    Renders the details dialog. Fetches the item on-demand to avoid state issues.
    """
    # The dialog is always in the DOM, just hidden/shown via is_open.
    # We only fetch and render the content if an item is selected.
    if pagestate.show_details_dialog and pagestate.selected_media_item_id:
        # FETCH ON DEMAND
        item_to_display = get_media_item_by_id(pagestate.selected_media_item_id)

        with lightbox_dialog(is_open=True, on_close=on_close_details_dialog): # pylint: disable=E1129:not-context-manager
            if not item_to_display:
                with me.box(style=me.Style(padding=me.Padding.all(16))):
                    me.text("Error: Could not load media item details.")
                return

            # If the item has a storyboard_id, fetch the data and render the tour dialog.
            if item_to_display.storyboard_id:
                from config.firebase_config import FirebaseClient

                db = FirebaseClient().get_client()
                doc_ref = db.collection("interior_design_storyboards").document(
                    item_to_display.storyboard_id
                )
                doc = doc_ref.get()
                if doc.exists:
                    # Pass the fetched storyboard dict as a parameter
                    render_tour_detail_dialog(storyboard=doc.to_dict())
                else:
                    me.text(
                        f"Error: Could not find storyboard with ID: {item_to_display.storyboard_id}"
                    )
            else:
                # Pass the freshly fetched item as a parameter
                render_default_detail_dialog(item=item_to_display)
    else:
        # Render an empty, closed dialog if nothing is selected.
        # This is important so the dialog can be opened by changing the state.
        with lightbox_dialog(is_open=False, on_close=on_close_details_dialog):  # pylint: disable=E1129:not-context-manager
            pass  # Render nothing inside the closed dialog


def on_close_details_dialog(e: me.ClickEvent):
    pagestate = me.state(PageState)
    carousel_state = me.state(CarouselState)
    pagestate.show_details_dialog = False
    pagestate.selected_media_item_id = None
    carousel_state.current_index = 0
    yield


def handle_edit_click(e: me.WebEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="media_detail_viewer_edit_button",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
    gcs_uri = https_url_to_gcs_uri(e.value["url"])
    me.navigate("/nano-banana", query_params={"image_uri": gcs_uri})


def on_veo_click(e: me.WebEvent):
    """Event handler for when the VEO button is clicked in the detail viewer."""
    # The event value contains the https URL of the currently displayed image
    https_url = e.value["url"]
    if https_url:
        # Convert the HTTPS URL back to a GCS URI to pass as a query param
        gcs_uri = https_url_to_gcs_uri(https_url)
        me.navigate(url="/veo", query_params={"image_uri": gcs_uri})
    yield


def json_default_serializer(o):
    """A default serializer for json.dumps to handle datetimes."""
    if isinstance(o, (datetime.datetime, datetime.date)):
        return o.isoformat()
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


@me.component
def render_tour_detail_dialog(storyboard: dict):
    """Renders a dedicated dialog for viewing Interior Design Tours."""

    if not storyboard:
        return

    with lightbox_dialog(is_open=True, on_close=on_close_details_dialog):  # pylint: disable=E1129:not-context-manager
        me.text(f"Interior Design Tour", type="headline-5")

        with me.box(style=me.Style(display="flex", flex_direction="row", gap=24, margin=me.Margin(top=16))):
            # Left Column: Video and Carousel
            with me.box(style=me.Style(flex_grow=1, display="flex", flex_direction="column", gap=16)):
                final_video_uri = storyboard.get("final_video_uri")
                if final_video_uri:
                    me.video(
                        src=gcs_uri_to_https_url(final_video_uri),
                        style=me.Style(width="100%", border_radius=8),
                    )

                with me.box():
                    me.text("Storyboard Clips", type="headline-6")
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=16,
                            overflow_x="auto",
                            padding=me.Padding(top=8, bottom=16),
                        )
                    ):
                        for item in storyboard.get("storyboard_items", []):
                            if item.get("generated_video_uri"):
                                storyboard_video_tile(
                                    key=item["room_name"],
                                    video_url=item["generated_video_uri"],
                                    room_name=item["room_name"],
                                    on_click=lambda e: None,
                                )
            
            # Right Column: Metadata
            with me.box(style=me.Style(width=300, flex_shrink=0)):
                me.text("Details", type="headline-6")
                with me.box(style=me.Style(margin=me.Margin(top=8, bottom=16))):
                    me.text(f"Storyboard ID: {storyboard.get('id')}")
                    me.text(f"Created: {storyboard.get('timestamp')}")
                    # You can add more metadata here as needed

                me.divider()

                me.text("Raw Metadata", type="headline-6", style=me.Style(margin=me.Margin(top=16)))
                with me.box(style=me.Style(background=me.theme_var("surface-container"), border_radius=8, padding=me.Padding.all(8), margin=me.Margin(top=8))):
                    me.code(json.dumps(storyboard, indent=2), language="json")

        with me.box(
            style=me.Style(
                display="flex",
                justify_content="flex-end",
                gap=8,
                margin=me.Margin(top=24),
            )
        ):
            me.button("Close", on_click=on_close_details_dialog, type="stroked")
            me.button(
                "Continue Styling", on_click=on_continue_styling_click, key=storyboard.get("id"), type="raised"
            )


@me.component
def render_default_detail_dialog(item: MediaItem):
    """Renders the default detail view for standard media items."""
    # Consolidate the primary URI(s) into a single list for processing.
    urls_to_process = []
    if item.gcs_uris:
        urls_to_process.extend(item.gcs_uris)
    elif item.gcsuri:
        urls_to_process.append(item.gcsuri)
    primary_urls = [gcs_uri_to_https_url(uri) for uri in urls_to_process]

    # Consolidate all potential source assets into a single list for backward compatibility
    all_source_uris = []
    if item.source_uris:
        all_source_uris.extend(item.source_uris)
    if item.source_images_gcs:
        all_source_uris.extend(item.source_images_gcs)
    if item.r2v_reference_images:
        all_source_uris.extend(item.r2v_reference_images)
    if item.r2v_style_image:
        all_source_uris.append(item.r2v_style_image)
    if item.reference_image:
        all_source_uris.append(item.reference_image)

    # Handle case where timestamp might be a string from Firestore
    timestamp_display = "N/A"
    if isinstance(item.timestamp, datetime.datetime):
        timestamp_display = item.timestamp.isoformat()
    elif isinstance(item.timestamp, str):
        timestamp_display = item.timestamp

    metadata = {
        "Prompt": item.prompt,
        "Model": item.model,
        "Timestamp": timestamp_display,
        "Generation Time (s)": item.generation_time,
    }

    # Determine the render type based on mime_type for reliability
    render_type = "image"  # Default to image
    if item.mime_type:
        if item.mime_type.startswith("video/"):
            render_type = "video"
        elif item.mime_type.startswith("audio/"):
            render_type = "audio"
    # Fallback to URL check if mime_type is missing
    elif primary_urls:
        url = primary_urls[0]
        if ".mp4" in url or ".webm" in url:
            render_type = "video"
        elif ".wav" in url or ".mp3" in url:
            render_type = "audio"

    # The main detail viewer now only shows the primary asset and metadata
    media_detail_viewer(
        media_type=render_type,
        primary_urls_json=json.dumps(primary_urls),
        source_urls_json="[]",  # Pass empty list as sources are rendered below
        metadata_json=json.dumps(metadata),
        id=item.id,
        raw_metadata_json=json.dumps(
            asdict(item), indent=2, default=json_default_serializer
        ),
        on_edit_click=handle_edit_click,
        on_veo_click=on_veo_click,
    )

    # New section to render source assets using media_tile
    if all_source_uris:
        with me.box(style=me.Style(margin=me.Margin(top=24))):
            me.text("Source Assets", type="headline-6")
            with me.box(
                style=me.Style(
                    display="grid",
                    grid_template_columns="repeat(auto-fill, minmax(200px, 1fr))",
                    gap="16px",
                    margin=me.Margin(top=16),
                )
            ):
                for source_uri in all_source_uris:
                    https_url = gcs_uri_to_https_url(source_uri)
                    # Determine media type from URL extension
                    render_type = "image"  # Default
                    if ".mp4" in https_url or ".webm" in https_url:
                        render_type = "video"
                    elif ".wav" in https_url or ".mp3" in https_url:
                        render_type = "audio"

                    # Create a dummy MediaItem for pill generation
                    source_item = MediaItem(gcsuri=source_uri, media_type=render_type)
                    media_tile(
                        key=source_uri,
                        media_type=render_type,
                        https_url=https_url,
                        pills_json=get_pills_for_item(source_item, https_url),
                        # Not clickable for now, but could be in the future
                        on_click=None,
                    )


def on_continue_styling_click(e: me.ClickEvent):
    """Navigates the user to the interior design page to continue styling."""
    storyboard_id = e.key
    if storyboard_id:
        me.navigate(
            url="/interior_design",
            query_params={
                "storyboard_id": f"{storyboard_id}",
            },
        )
                
    yield



