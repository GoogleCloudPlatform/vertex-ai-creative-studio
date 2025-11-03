"""
Component for displaying a single video item in the storyboard.
"""

import mesop as me
from typing import Callable

from common.utils import gcs_uri_to_https_url
from components.video_thumbnail.video_thumbnail import video_thumbnail


@me.component
def storyboard_video_tile(
    video_url: str,
    room_name: str,
    on_click: Callable,
    key: str,
):
    """
    A tile for displaying a storyboard video item with a text overlay.
    """
    with me.box(
        key=key,
        on_click=on_click,
        style=me.Style(
            width=200,
            height=150,
            position="relative",
            cursor="pointer",
            flex_shrink=0,
        ),
    ):
        video_thumbnail(
            video_src=gcs_uri_to_https_url(video_url),
            selected=False, # Not used in this context, but required
        )
        # Overlay for the room name
        with me.box(
            style=me.Style(
                position="absolute",
                bottom=0,
                left=0,
                right=0,
                background="rgba(0, 0, 0, 0.6)",
                padding=me.Padding(top=4, bottom=4, left=8, right=8),
                border_radius="0 0 8px 8px",
            )
        ):
            me.text(
                room_name,
                style=me.Style(
                    color="white",
                    font_size=14,
                    font_weight=500,
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
            )
