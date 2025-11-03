"""
Component for displaying the room view.
"""

import mesop as me

from common.utils import gcs_uri_to_https_url


@me.component
def room_view(storyboard: dict, is_generating_zoom: bool):
    """
    Component for displaying the room view.
    """
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            align_items="center",
            gap=10,
            flex_grow=1,
        )
    ):
        storyboard_item = next((item for item in storyboard["storyboard_items"] if item["room_name"] == storyboard["selected_room"]), None)
        if storyboard_item:
            me.text(f"Room View: {storyboard_item['room_name']}", type="headline-6")
            if is_generating_zoom:
                me.progress_spinner()
            elif storyboard_item["styled_image_uri"]:
                me.image(
                    src=gcs_uri_to_https_url(storyboard_item["styled_image_uri"]),
                    style=me.Style(
                        height="100%",
                        width="100%",
                        max_width="600px",
                        border_radius=8,
                        object_fit="contain",
                    ),
                )
