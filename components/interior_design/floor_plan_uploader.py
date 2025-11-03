"""
Component for uploading a floor plan.
"""

from typing import Callable
import mesop as me

from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from state.interior_design_v2_state import PageState


IMAGE_PLACEHOLDER_STYLE = me.Style(
    width=400,
    height=400,
    border=me.Border.all(
        me.BorderSide(width=2, style="dashed", color=me.theme_var("outline-variant")),
    ),
    border_radius=8,
    display="flex",
    align_items="center",
    justify_content="center",
    flex_direction="column",
    gap=8,
)


@me.component
def floor_plan_uploader(
    storyboard: dict,
    on_upload: Callable,
    on_library_select: Callable,
):
    """
    Component for uploading a floor plan.
    """
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=10,
            align_items="center",
        )
    ):
        me.text("Floor Plan", type="headline-6")
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=8,
                align_items="center",
                min_height=48,
            )
        ):
            me.uploader(
                label="Upload Floor Plan",
                on_upload=on_upload,
                accepted_file_types=["image/jpeg", "image/png", "image/webp"],
                style=me.Style(width="100%"),
            )
            library_chooser_button(
                key="floor_plan", on_library_select=on_library_select
            )
        with me.box(style=IMAGE_PLACEHOLDER_STYLE):
            if storyboard and storyboard.get("original_floor_plan_uri"):
                me.image(
                    src=gcs_uri_to_https_url(storyboard["original_floor_plan_uri"]),
                    style=me.Style(
                        height="100%",
                        width="100%",
                        border_radius=8,
                        object_fit="contain",
                    ),
                )
            else:
                me.icon("floorplan")
                me.text("Add a floor plan")
