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

from state.state import AppState
from state.veo_state import PageState
from ..video_thumbnail.video_thumbnail import video_thumbnail
from ..pill import pill
from models.video_processing import convert_mp4_to_gif
from common.utils import https_url_to_gcs_uri, create_display_url
from config.veo_models import get_veo_model_config

@me.component
def video_display(on_thumbnail_click: Callable, on_click_extend: Callable):
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

        if not state.result_display_urls:
            me.text("Your generated videos will appear here.", style=me.Style(padding=me.Padding.all(24), color=me.theme_var("on-surface-variant")))
            return

        # Determine the main video to display
        main_video_url = state.selected_video_url if state.selected_video_url else state.result_display_urls[0]

        # Parse aspect ratio string "w:h" into "w / h" for CSS
        aspect_ratio_css = state.aspect_ratio.replace(":", " / ")

        # Main video player container
        with me.box(
            style=me.Style(
                width="100%",
                max_width="90vh",
                max_height="85vh",
                margin=me.Margin(left="auto", right="auto"),
                aspect_ratio=aspect_ratio_css,
                position="relative", # Allow for absolute positioning of badge
            )
        ):
            me.video(
                key=main_video_url,
                src=main_video_url,
                style=me.Style(
                    border_radius=12,
                    width="100%",
                    height="100%",
                    display="block",
                ),
            )
            
            # 4K badge overlay (Hidden by default to avoid confusion with video content)
            # To enable, uncomment the block below.
            # if state.resolution == "4k":
            #     with me.box(
            #         style=me.Style(
            #             position="absolute",
            #             top=16,
            #             right=16,
            #             z_index=1,
            #         )
            #     ):
            #         pill(label="4K Ultra HD", pill_type="resolution_4k")

        # Find the corresponding GCS URI for the selected video URL to pass to the GIF converter.
        try:
            selected_index = state.result_display_urls.index(main_video_url)
            gcs_uri_for_gif = state.result_gcs_uris[selected_index]
        except (ValueError, IndexError):
            gcs_uri_for_gif = "" # Fallback in case of an issue

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
            
            model_config = get_veo_model_config(state.veo_model)
            if model_config and model_config.supports_video_extension:
                options = [me.SelectOption(label="None", value="0")]
                
                # Use configured durations if available, otherwise fallback to generic range
                if model_config.supported_extension_durations:
                    for duration in model_config.supported_extension_durations:
                        options.append(me.SelectOption(label=f"{duration} seconds", value=str(duration)))
                else:
                    # Fallback for models that might support extension but don't have explicit duration config yet
                    options.extend([
                        me.SelectOption(label="4 seconds", value="4"),
                        me.SelectOption(label="5 seconds", value="5"),
                        me.SelectOption(label="6 seconds", value="6"),
                        me.SelectOption(label="7 seconds", value="7"),
                    ])

                me.select(
                    label="extend",
                    options=options,
                    appearance="outline",
                    value=f"{state.video_extend_length}",
                    on_selection_change=on_selection_change_extend_length,
                )
                me.button(
                    label="Extend",
                    on_click=on_click_extend,
                    disabled=True if state.video_extend_length == 0 else False,
                )

            me.button("Convert to GIF", key=gcs_uri_for_gif, on_click=on_convert_to_gif_click, disabled=state.is_converting_gif)

            if state.is_converting_gif:
                with me.box(style=me.Style(display="flex", justify_content="center")):
                    me.progress_spinner()

        # Thumbnail strip for multiple videos
        if len(state.result_display_urls) > 1:
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
                for url in state.result_display_urls:
                    is_selected = url == main_video_url
                    with me.box(style=me.Style(height="90px", width="160px")):
                        video_thumbnail(
                            key=url,
                            video_src=url,
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

def on_convert_to_gif_click(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.is_converting_gif = True
    state.gif_url = ""
    yield

    try:
        # Get the display URL of the currently selected video.
        video_to_convert = state.selected_video_url if state.selected_video_url else state.result_display_urls[0]
        print(f"Converting {video_to_convert} to GIF ...")

        # Convert the display URL back to a GCS URI for the backend function.
        gcs_uri = https_url_to_gcs_uri(video_to_convert)

        # This function returns the GCS URI of the new GIF
        new_gif_gcs_uri = convert_mp4_to_gif(gcs_uri, user_email=app_state.user_email)

        # Convert the new GCS URI into a display URL
        state.gif_url = create_display_url(new_gif_gcs_uri)

    except Exception as ex:
        # Handle errors if necessary
        print(f"Error converting to GIF: {ex}")
        state.error_message = f"Failed to convert to GIF: {ex}"
        state.show_error_dialog = True
    finally:
        state.is_converting_gif = False
        yield
