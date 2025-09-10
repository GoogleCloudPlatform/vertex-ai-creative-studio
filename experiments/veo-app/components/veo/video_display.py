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
from state.veo_state import PageState


@me.component
def video_display():
    """Display the generated video"""
    state = me.state(PageState)
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            align_items="center",
            height="100%",
        )
    ):
        me.text("Generated Video")
        me.box(style=me.Style(height=8))
        with me.box(style=me.Style(height="100%")):
            if state.is_loading:
                me.progress_spinner()
            elif state.result_video:
                video_url = gcs_uri_to_https_url(state.result_video)
                print(f"video_url: {video_url}")
                me.video(
                    src=video_url,
                    style=me.Style(
                        border_radius=12,
                        width="100%",  # Ensures the video scales to the container width
                        max_width="90vh",  # Prevents the video from becoming excessively large on wide screens
                        display="block",  # Ensures proper block-level layout
                        margin=me.Margin(left="auto", right="auto"), # Centers the video horizontally
                    ),
                )
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=5,
                        align_items="center",
                        padding=me.Padding(top=10),
                    )
                ):
                    me.text(state.timing)
                    if not state.veo_model == "3.0":
                        me.select(
                            label="extend",
                            options=[
                                me.SelectOption(label="None", value="0"),
                                me.SelectOption(label="4 seconds", value="4"),
                                me.SelectOption(label="5 seconds", value="5"),
                                me.SelectOption(label="6 seconds", value="6"),
                                me.SelectOption(label="7 seconds", value="7"),
                            ],
                            appearance="outline",
                            style=me.Style(),
                            value=f"{state.video_extend_length}",
                            on_selection_change=on_selection_change_extend_length,
                        )
                        me.button(
                            label="Extend",
                            on_click=on_click_extend,
                            disabled=True if state.video_extend_length == 0 else False,
                        )


def on_selection_change_extend_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video extend length in seconds based on user event"""
    state = me.state(PageState)
    state.video_extend_length = int(e.value)


def on_click_extend(e: me.ClickEvent):
    """Extend video"""
    state = me.state(PageState)
    print(
        f"You would like to extend {state.result_video} by {state.video_extend_length} seconds."
    )
    print(f"Continue the scene {state.veo_prompt_input} ...")