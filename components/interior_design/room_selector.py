"""
Component for selecting a room.
"""

from typing import Callable
import mesop as me


@me.component
def room_selector(
    storyboard: dict,
    is_generating_zoom: bool,
    on_room_select: Callable,
):
    """
    Component for selecting a room.
    """
    if storyboard and storyboard.get("room_names"):
        print(f"room_selector: Rendering buttons for rooms: {storyboard.get('room_names')}")
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
                align_items="center",
                gap=10,
            )
        ):
            me.text("Identified Rooms", type="headline-6")
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=10,
                    flex_wrap="wrap",
                    justify_content="center",
                )
            ):
                for room in storyboard["room_names"]:
                    me.text(f"TEST: {room}")