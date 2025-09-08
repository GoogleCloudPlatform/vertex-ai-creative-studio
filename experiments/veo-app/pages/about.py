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
from components.page_scaffold import page_frame, page_scaffold
from config.default import ABOUT_PAGE_CONTENT
from components.pill import pill


def render_section(section_data: dict):
    """Render a single section with text and media."""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            gap=24,
            align_items="center",
            margin=me.Margin(top=24, bottom=24),
            border=me.Border.all(
                me.BorderSide(style="solid", width=1, color=me.theme_var("outline"))
            ),
            padding=me.Padding.all(16),
            border_radius=12,
        )
    ):
        # Text content on the left
        with me.box(style=me.Style(flex_grow=1)):
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="row", gap=5,
                ),
            ):
                me.text(section_data["title"], type="headline-5")
                if section_data.get("stage"):
                    pill(section_data["stage"], "stage")
            me.markdown(section_data["description"])

        # Media content on the right
        with me.box(style=me.Style(width="300px")):
            if section_data.get("image"):
                me.image(
                    src=section_data["image"],
                    style=me.Style(width="100%", border_radius=8),
                )
            elif section_data.get("video"):
                me.video(
                    src=section_data["video"],
                    style=me.Style(width="100%", border_radius=8),
                )


def about_page_content():
    """About page."""
    with page_frame():
        header("About This Application", "info")

        if ABOUT_PAGE_CONTENT:
            # Render header
            me.text(ABOUT_PAGE_CONTENT["header"]["title"], type="headline-4")
            me.markdown(ABOUT_PAGE_CONTENT["header"]["introduction"])
            me.divider()

            # Render each section
            for section in ABOUT_PAGE_CONTENT.get("sections", []):
                render_section(section)
        else:
            me.text(
                "Could not load the About page content. Please ensure 'config/about_content.json' is valid."
            )


@me.page(
    path="/about",
    title="About - GenMedia Creative Studio",
)
def page():
    with page_scaffold(page_name="about"):
        about_page_content()