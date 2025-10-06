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

from typing import Callable
import mesop as me

from common.utils import gcs_uri_to_https_url
from state.state import AppState
from state.veo_state import PageState
from ..video_thumbnail.video_thumbnail import video_thumbnail
from models.video_processing import convert_mp4_to_gif

@me.component
def video_display(on_thumbnail_click: Callable):
    """Display the generated video(s) in a gallery format."""
    state = me.state(PageState)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            align_items="center",
            width="100%",
        )
    ):
        if state.is_loading:
            with me.box(style=me.Style(display="flex", justify_content="center", margin=me.Margin(top=24))):
                me.progress_spinner()
            me.text(state.timing if state.timing else "Generating video...", style=me.Style(margin=me.Margin(top=16)))
            state.gif_url = ""
            return

        if not state.result_videos:
            me.text("Your generated videos will appear here.", style=me.Style(padding=me.Padding.all(24), color=me.theme_var("on-surface-variant")))
            return

        # Determine the main video to display
        main_video_url = state.selected_video_url if state.selected_video_url else state.result_videos[0]

        # Main video player
        me.video(
            key=main_video_url, # Add key to force re-render
            src=gcs_uri_to_https_url(main_video_url),
            style=me.Style(
                border_radius=12,
                width="100%",
                max_width="90vh",
                display="block",
                margin=me.Margin(left="auto", right="auto"),
            ),
        )

        # Generation time and Extend functionality
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=15,
                align_items="center",
                justify_content="center",
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
                    value=f"{state.video_extend_length}",
                    on_selection_change=on_selection_change_extend_length,
                )
                me.button(
                    label="Extend",
                    on_click=on_click_extend,
                    disabled=True if state.video_extend_length == 0 else False,
                )
            
            me.button("Convert to GIF", key=main_video_url, on_click=on_convert_to_gif_click, disabled=state.is_converting_gif)

            if state.is_converting_gif:
                with me.box(style=me.Style(display="flex", justify_content="center")):
                    me.progress_spinner()

        # Thumbnail strip for multiple videos
        if len(state.result_videos) > 1:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="row",
                    gap=16,
                    justify_content="center",
                    margin=me.Margin(top=16),
                    flex_wrap="wrap",
                )
            ):
                for url in state.result_videos:
                    is_selected = url == main_video_url
                    with me.box(style=me.Style(height="90px", width="160px")):
                        video_thumbnail(
                            key=url,
                            video_src=gcs_uri_to_https_url(url),
                            selected=is_selected,
                            on_click=on_thumbnail_click,
                        )

        if state.gif_url:
            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    gap=10,
                )
            ):
                me.text("Video as GIF:", type="headline-5")
                me.image(
                    src=state.gif_url,
                    style=me.Style(width="100%", max_width="480px", border_radius=8),
                )


def on_selection_change_extend_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video extend length in seconds based on user event"""
    state = me.state(PageState)
    state.video_extend_length = int(e.value)
    yield


def on_click_extend(e: me.ClickEvent):
    """Extend video"""
    state = me.state(PageState)
    video_to_extend = state.selected_video_url if state.selected_video_url else state.result_videos[0]
    print(
        f"You would like to extend {video_to_extend} by {state.video_extend_length} seconds."
    )
    print(f"Continue the scene {state.veo_prompt_input} ...")
    yield

def on_convert_to_gif_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_converting_gif = True
    yield

    try:
        print(f"Converting {e.key} to GIF ...")
        state.gif_url = gcs_uri_to_https_url(convert_mp4_to_gif(e.key, user_email=app_state.user_email))
    finally:
        state.is_converting_gif = False
        yield
