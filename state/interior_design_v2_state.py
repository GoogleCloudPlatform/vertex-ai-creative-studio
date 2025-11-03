"""
State for the Interior Design V2 page.
"""

from dataclasses import field
import mesop as me


@me.stateclass
class PageState:
    """State for the Interior Design page."""

    storyboard: dict = field(default_factory=dict)
    is_generating: bool = False
    is_generating_zoom: bool = False
    is_designing: bool = False
    is_generating_video: bool = False
    video_generation_status: str = ""
    show_snackbar: bool = False
    snackbar_message: str = ""
    final_video_uri: str = ""
    is_detail_dialog_open: bool = False
    selected_room_for_dialog: str | None = None
    error_message: str = ""
    design_prompt: str = ""
    design_image_uri: str = ""

    info_dialog_open: bool = False
