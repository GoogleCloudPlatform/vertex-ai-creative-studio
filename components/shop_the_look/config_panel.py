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

from common.utils import gcs_uri_to_https_url
from models import shop_the_look_workflow
from state.shop_the_look_state import PageState
from state.state import AppState

@me.component
def config_panel():
    """Renders the configuration panel for the Shop The Look feature.

    This component includes settings for VTO (Virtual Try-On), VEO (video
    generation), and displays the currently selected apparel and models.
    """
    state = me.state(PageState)
    app_state = me.state(AppState)

    with me.box():
        with me.box(
            style=me.Style(
                height="100%",
                width="100%",
                display="flex",
                flex_direction="row",
                flex_wrap="wrap",
            )
        ):
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.text(
                    text="VTO",
                    type="headline-6",
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.checkbox(
                    "Upload model/clothing for all access?",
                    checked=state.upload_everyone,
                    on_change=on_config_upload_everyone,
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.select(
                    label="VTO Sample Count",
                    options=[
                        me.SelectOption(label="1 image", value="1"),
                        me.SelectOption(label="2 images", value="2"),
                        me.SelectOption(label="3 images", value="3"),
                        me.SelectOption(label="4 images", value="4"),
                    ],
                    on_selection_change=on_sample_count_change,
                    style=me.Style(width=180),
                    multiple=False,
                    appearance="outline",
                    value=state.vto_sample_count,
                )
                me.select(
                    label="Max Auto Retry",
                    options=[
                        me.SelectOption(label="1 times", value="1"),
                        me.SelectOption(label="2 times", value="2"),
                        me.SelectOption(label="3 times", value="3"),
                        me.SelectOption(label="4 times", value="4"),
                    ],
                    on_selection_change=max_retry_change,
                    style=me.Style(width=180),
                    multiple=False,
                    appearance="outline",
                    value=state.max_retry,
                )

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.text(
                    text="VEO",
                    type="headline-6",
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.select(
                    label="Version",
                    options=[
                        me.SelectOption(label="Veo 3", value="3.0"),
                        me.SelectOption(label="Veo 2", value="2.0"),
                    ],
                    on_selection_change=on_veo_version_change,
                    style=me.Style(width=140),
                    multiple=False,
                    appearance="outline",
                    value=state.veo_model,
                )
                me.checkbox(
                    "Generate videos (in addition)",
                    checked=state.generate_video,
                    on_change=on_config_generate_videos,
                )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                )
            ):
                me.text(
                    text="Base Prompt",
                    style=me.Style(
                        font_size="12px",
                    ),
                )
            me.native_textarea(
                autosize=True,
                min_rows=10,
                max_rows=13,
                placeholder="Base prompt",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=me.theme_var("secondary-container"),
                    outline="none",
                    width="1200px",
                    overflow_y="auto",
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                    flex_grow=1,
                ),
                on_blur=on_blur_veo_prompt,
                value=state.veo_prompt_input,
            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                    margin=me.Margin(top=10),
                )
            ):
                me.text(
                    text="Apparel",
                    type="headline-6",
                )
            if state.articles:
                for item in state.articles:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=5,
                            align_items="left",
                        )
                    ):
                        img = gcs_uri_to_https_url(item.clothing_image)
                        with me.box(
                            key=f"{item.item_id}-{item.article_type}",
                            style=me.Style(
                                position="relative",
                                height="100%",
                                margin=me.Margin(left=10, top=10),
                            ),
                        ):
                            with me.box(
                                key=f"{img}",
                                on_click=shop_the_look_workflow.article_on_delete,
                                style=me.Style(
                                    cursor="pointer",
                                ),
                            ):
                                me.icon(
                                    "delete",
                                    style=me.Style(
                                        color="red",
                                        position="absolute",
                                        top="5px",
                                        left="5px",
                                        height="30px",
                                        width="30px",
                                        font_size="30px",
                                    ),
                                )

                            me.image(
                                src=img,
                                style=me.Style(
                                    width="150px",
                                    height="150px",
                                    object_fit="cover",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                                ),
                            )
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=5,
                    align_items="top",
                    width="100%",
                    margin=me.Margin(top=10),
                )
            ):
                me.text(
                    text="Models",
                    type="headline-6",
                )
            if state.models:
                for model in state.models:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="row",
                            gap=5,
                            align_items="left",
                        )
                    ):
                        img = gcs_uri_to_https_url(model.model_image)
                        with me.box(
                            style=me.Style(
                                position="relative",
                                height="100%",
                                margin=me.Margin(left=10, top=10),
                            ),
                        ):
                            with me.box(
                                key=f"{img}",
                                on_click=shop_the_look_workflow.model_on_delete,
                                style=me.Style(
                                    cursor="pointer",
                                ),
                            ):
                                me.icon(
                                    "delete",
                                    style=me.Style(
                                        color="red",
                                        position="absolute",
                                        top="5px",
                                        left="5px",
                                        height="30px",
                                        width="30px",
                                        font_size="30px",
                                    ),
                                )

                            me.image(
                                src=img,
                                style=me.Style(
                                    width="150px",
                                    height="150px",
                                    object_fit="cover",
                                    border_radius="5px",
                                    box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                                ),
                            )


# Config Events
def on_config_generate_videos(event: me.CheckboxChangeEvent):
    """Updates the state when the 'Generate videos' checkbox is changed.

    Args:
        event: The Mesop checkbox change event.
    """
    state = me.state(PageState)
    state.generate_video = event.checked


def on_config_upload_everyone(event: me.CheckboxChangeEvent):
    """Updates the state when the 'Upload for everyone' checkbox is changed.

    Args:
        event: The Mesop checkbox change event.
    """
    state = me.state(PageState)
    state.upload_everyone = event.checked


def on_veo_version_change(e: me.SelectSelectionChangeEvent):
    """Updates the state when the VEO model version is changed.

    Args:
        e: The Mesop select selection change event.
    """
    s = me.state(PageState)
    s.veo_model = e.value


def on_sample_count_change(e: me.SelectSelectionChangeEvent):
    """Updates the state when the VTO sample count is changed.

    Args:
        e: The Mesop select selection change event.
    """
    s = me.state(PageState)
    s.vto_sample_count = e.value


def max_retry_change(e: me.SelectSelectionChangeEvent):
    """Updates the state when the max auto retry count is changed.

    Args:
        e: The Mesop select selection change event.
    """
    s = me.state(PageState)
    s.max_retry = e.value


def on_blur_veo_prompt(e: me.InputBlurEvent):
    """Updates the state with the VEO prompt when the input field loses focus.

    Args:
        e: The Mesop input blur event.
    """
    me.state(PageState).veo_prompt_input = e.value