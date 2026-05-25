# Copyright 2025 Google LLC
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

import mesop as me

from components.header import header
from components.page_scaffold import on_theme_load
from components.svg_icon.svg_icon import svg_icon
from components.theme_manager.theme_manager import theme_manager
from state.state import AppState


def on_navigate(e: me.ClickEvent):
    me.navigate(e.key)


@me.page(path="/labs", title="Labs: GenMedia Creative Studio")
def page():
    app_state = me.state(AppState)
    theme_manager(theme=app_state.theme_mode, on_theme_load=on_theme_load)

    test_pages = [
        {
            "title": "Retro Games Workflow",
            "description": "Create a retro game video from an image.",
            "route": "/retro_games",
        },

        {
            "title": "Character Asset Sheet",
            "description": "Generate consistent character sheets and scenarios.",
            "route": "/character_sheet",
        },
        {
            "title": "Brand Adherence",
            "description": "Generate on-brand images using PDF guidelines.",
            "route": "/brand_adherence",
        },
        {
            "title": "Banana Studio",
            "description": "An experimental Gemini Image Generation page.",
            "route": "/banana-studio",
        },
        {
            "title": "Object Rotation",
            "description": "Given an object, create images of each side and then create a rotation video",
            "route": "/object-rotation",
        },
        {
            "title": "Guideline Analysis",
            "description": "A page to analyze a media item's prompt and generate guideline criteria.",
            "route": "/guideline-analysis",
        },
        {
            "title": "Imagen Upscale Test",
            "description": "Test page for Imagen 4 Upscale.",
            "route": "/imagen-upscale",
        },
        {
            "title": "VTO Model Composite Card Generator",
            "description": "A tool to generate a matrix of virtual models with different attributes.",
            "route": "/test_vto_prompt_generator",
        },
        {
            "title": "Selfie Camera",
            "description": "A test page for the selfie camera component.",
            "route": "/selfie",
        },
        {
            "title": "Uploader",
            "description": "A test page for determining uploader component capabilities.",
            "route": "/test_uploader",
        },
        {
            "title": "Character Consistency Test",
            "description": "A test page for the character consistency workflow.",
            "route": "/test_character_consistency",
        },
        {
            "title": "Pixie Compositor Test",
            "description": "A test page for the Pixie Compositor web component.",
            "route": "/test_pixie_compositor",
        },
        {
            "title": "Media Chooser Test",
            "description": "A test page for the generic, high-performance media chooser component.",
            "route": "/test_media_chooser",
        },
        {
            "title": "Proxy Caching Test",
            "description": "A page to compare the performance of signed URLs vs. a caching proxy endpoint.",
            "route": "/test_proxy_caching",
        },
        {
            "title": "Async Veo Test",
            "description": "Test page for the new non-blocking Veo generation flow.",
            "route": "/test_async_veo",
        },
    ]

    # Main container - use min_height and flex column
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            min_height="100vh",
        )
    ):
        # Content area - set to grow and scroll
        with me.box(
            style=me.Style(
                background=me.theme_var("background"),
                flex_grow=1,  # Let this area grow
                overflow_y="auto",
            )
        ):
            with me.box(
                style=me.Style(
                    background=me.theme_var("background"),
                    padding=me.Padding(top=24, left=24, right=24, bottom=24),
                    display="flex",
                    flex_direction="column",
                )
            ):
                header("Labs", "science")

                me.text(
                    "A list of automations, workflows, and components - for debugging and exploring new features."
                )

                with me.box(style=me.Style(margin=me.Margin(top=24))):
                    with me.box(
                        style=me.Style(
                            display="grid",
                            grid_template_columns="repeat(auto-fill, minmax(250px, 1fr))",
                            gap=15,
                        ),
                    ):
                        for test_page in test_pages:
                            with me.box(
                                key=test_page["route"],
                                on_click=on_navigate,
                                style=me.Style(
                                    border=me.Border.all(
                                        me.BorderSide(
                                            width=1,
                                            style="solid",
                                            color=me.theme_var("outline"),
                                        )
                                    ),
                                    background=me.theme_var("surface-container-lowest"),
                                    padding=me.Padding.all(15),
                                    border_radius=12,
                                    cursor="pointer",
                                ),
                            ):
                                me.text(test_page["title"], type="subtitle-1")
                                me.text(
                                    test_page["description"],
                                    type="body-2",
                                    style=me.Style(margin=me.Margin(top=8)),
                                )

        # Footer - back home (now it will be at the bottom)
        with me.box(
            style=me.Style(
                padding=me.Padding.all(16),
                border=me.Border(top=me.BorderSide(width=1, color=me.theme_var("tertiary-fixed-variant"))),
                display="flex",
                align_items="center",
                gap=12,
                background=me.theme_var("inverse-surface"),
                color=me.theme_var("inverse-on-surface"),
                cursor="pointer",
            ),
            on_click=on_home_click,
        ):
            with me.tooltip(message="Back to Welcome Page"):
                me.icon(icon="auto_awesome", style=me.Style(color=me.theme_var("inverse-on-surface")))
            me.text("Return to GenMedia Creative Studio")


def on_home_click(e: me.ClickEvent) -> None:  # pylint: disable=W0613:unused-argument
    """Navigates back home."""
    me.navigate("/welcome")