"""
Component for generating and displaying the 3D view.
"""

from typing import Callable
import mesop as me

from common.utils import gcs_uri_to_https_url


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
def generated_3d_view(
    storyboard: dict,
    is_generating: bool,
    on_generate: Callable,
):
    """
    Component for generating and displaying the 3D view.
    """
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=10,
            align_items="center",
        )
    ):
        me.text("Generated 3D View", type="headline-6")
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=8,
                align_items="center",
                min_height=48,
            )
        ):
            me.button(
                "Generate 3D View",
                on_click=on_generate,
                disabled=not (storyboard and storyboard.get("original_floor_plan_uri")) or is_generating,
                type="raised",
            )
        with me.box(style=IMAGE_PLACEHOLDER_STYLE):
            if is_generating:
                me.progress_spinner()
            elif storyboard and storyboard.get("generated_3d_view_uri"):
                me.image(
                    src=gcs_uri_to_https_url(storyboard["generated_3d_view_uri"]),
                    style=me.Style(
                        height="100%",
                        width="100%",
                        border_radius=8,
                        object_fit="contain",
                    ),
                )
            else:
                me.icon("view_in_ar")
                me.text("Your 3D view will appear here")
