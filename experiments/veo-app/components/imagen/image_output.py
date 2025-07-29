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

from state.imagen_state import PageState
from svg_icon.svg_icon_component import svg_icon_component


@me.component
def image_output():
    """Image output display"""
    state = me.state(PageState)
    print(f"Rendering image_output, commentary: {state.image_commentary}")
    with me.box(style=_BOX_STYLE):
        me.text("Output", style=me.Style(font_weight=500))
        me.box(style=me.Style(height=10))

        if state.is_loading:
            with me.box(
                style=me.Style(
                    display="flex",
                    justify_content="center",
                    align_items="center",
                    flex_direction="column",
                    min_height="200px",
                )
            ):
                me.progress_spinner()
                me.text(
                    "Generating, please wait...",
                    style=me.Style(margin=me.Margin(top=10)),
                )

        elif state.image_output:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                )
            ):
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_wrap="wrap",
                        gap="15px",
                        justify_content="center",
                    )
                ):
                    for img_uri in state.image_output:
                        if img_uri:
                            final_img_src = img_uri
                            if img_uri.startswith("gs://"):
                                final_img_src = img_uri.replace(
                                    "gs://",
                                    "https://storage.mtls.cloud.google.com/",
                                )

                            me.image(
                                src=final_img_src,
                                style=me.Style(
                                    width="300px",
                                    height="300px",
                                    object_fit="contain",
                                    border_radius="12px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                                ),
                            )
                if state.imagen_watermark:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            align_items="center",
                            margin=me.Margin(top=15),
                        )
                    ):
                        svg_icon_component(
                            svg="""<svg data-icon-name="digitalWatermarkIcon" viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true"><path fill="#3367D6" d="M12 22c-.117 0-.233-.008-.35-.025-.1-.033-.2-.075-.3-.125-2.467-1.267-4.308-2.833-5.525-4.7C4.608 15.267 4 12.983 4 10.3V6.2c0-.433.117-.825.35-1.175.25-.35.575-.592.975-.725l6-2.15a7.7 7.7 0 00.325-.1c.117-.033.233-.05.35-.05.15 0 .375.05.675.15l6 2.15c.4.133.717.375.95.725.25.333.375.717.375 1.15V10.3c0 2.683-.625 4.967-1.875 6.85-1.233 1.883-3.067 3.45-5.5 4.7-.1.05-.2.092-.3.125-.1.017-.208.025-.325.025zm0-2.075c2.017-1.1 3.517-2.417 4.5-3.95 1-1.55 1.5-3.442 1.5-5.675V6.175l-6-2.15-6 2.15V10.3c0 2.233.492 4.125 1.475 5.675 1 1.55 2.508 2.867 4.525 3.95z"></path><path fill="#3367D6" d="M12 16.275c0-.68-.127-1.314-.383-1.901a4.815 4.815 0 00-1.059-1.557 4.813 4.813 0 00-1.557-1.06 4.716 4.716 0 00-1.9-.382c.68 0 1.313-.128 1.9-.383a4.916 4.916 0 002.616-2.616A4.776 4.776 0 0012 6.475c0 .672.128 1.306.383 1.901a5.07 5.07 0 001.046 1.57 5.07 5.07 0 001.57 1.046 4.776 4.776 0 001.901.383c-.672 0-1.306.128-1.901.383a4.916 4.916 0 00-2.616 2.616A4.716 4.716 0 0012 16.275z"></path></svg>"""
                        )
                        me.text(
                            text="Images watermarked by SynthID (Google)",
                            style=me.Style(
                                padding=me.Padding.all(10),
                                font_size="0.9em",
                                color="#5f6368",
                            ),
                        )
                if state.image_commentary:
                    with me.box(style=_BOX_STYLE):
                        with me.box(
                            style=me.Style(
                                display="flex",
                                align_items="center",
                                gap="8px",
                                margin=me.Margin(bottom=10),
                            )
                        ):
                            me.icon("assistant")
                            me.text(
                                "Magazine Editor's Critique",
                                style=me.Style(font_weight=500),
                            )
                        me.markdown(
                            text=state.image_commentary,
                            style=me.Style(
                                padding=me.Padding(left=15, right=15, bottom=15)
                            ),
                        )
        else:
            me.text(
                text="Generate some images to see them here!",
                style=me.Style(
                    display="flex",
                    justify_content="center",
                    padding=me.Padding.all(20),
                    color=me.theme_var("outline"),
                    min_height="100px",
                    align_items="center",
                ),
            )


_BOX_STYLE = me.Style(
    background=me.theme_var("surface"),
    border_radius=12,
    box_shadow=me.theme_var("shadow_elevation_2"),
    padding=me.Padding.all(16),
    display="flex",
    flex_direction="column",
    margin=me.Margin(bottom=28),
)
