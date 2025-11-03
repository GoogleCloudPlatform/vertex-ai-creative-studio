"""
Component for displaying a single item in the storyboard.
"""

import mesop as me
from typing import Callable

from common.utils import gcs_uri_to_https_url


@me.component
def storyboard_item_tile(
    image_url: str,
    room_name: str,
    on_click: Callable,
    key: str,
):
    """
    A simple tile for displaying a storyboard item.
    """
    with me.box(
        key=key,
        on_click=on_click,
        style=me.Style(
            width=200,
            height=150,
            border_radius=8,
            background=f"url({gcs_uri_to_https_url(image_url)}) center / cover",
            position="relative",
            cursor="pointer",
            border=me.Border.all(me.BorderSide(color=me.theme_var("outline-variant"))),
            flex_shrink=0,
        ),
    ):
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
