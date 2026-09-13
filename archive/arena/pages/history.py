# Copyright 2024 Google LLC
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
""" History page"""
import mesop as me

from common.metadata import get_latest_votes

from components.header import header
from components.dialog import dialog

from components.page_scaffold import (
    page_scaffold,
    page_frame,
)


@me.stateclass
class PageState:
    is_open: bool = False
    image_url: str = ""


def history_page_content(app_state: me.state):
    """History Mesop Page"""
    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            page_state = me.state(PageState)
            header("History", "history")

            votes = get_latest_votes(app_state.study)
            print(f"retrieved {len(votes)} votes")

            with dialog(  # pylint: disable=not-context-manager
                is_open=page_state.is_open,
                on_click_background=on_click_background_close,
            ):
                me.image(src=page_state.image_url)

            with me.box(
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    width="90hv",
                )
            ):
                for v in votes:
                    model1 = v.get("model1")
                    image1 = v.get("image1")
                    model2 = v.get("model2")
                    image2 = v.get("image2")
                    winner = v.get("winner")
                    timestamp = v.get("timestamp").strftime("%Y-%m-%d %H:%M")
                    prompt = v.get("prompt")
                    with me.box(
                        style=me.Style(
                            padding=me.Padding.all(10),
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                            width="50%",
                            gap=10,
                        )
                    ):
                        # images
                        image1_url = gcs_to_http(image1)
                        image2_url = gcs_to_http(image2)
                        with me.box(
                            style=me.Style(
                                display="flex",
                                flex_direction="column",
                                gap=10,
                                align_items="center"
                            ),
                        ):
                            with me.box(
                                style=me.Style(
                                    flex_direction="row",
                                    display="flex",
                                    align_items="center",
                                    padding=me.Padding(bottom=40, top=45)
                                ),
                            ):
                                with me.content_button(
                                    key=image1_url,
                                    on_click=on_click_image_dialog,
                                    style=me.Style(
                                        flex_direction="column",
                                        display="flex",
                                        align_items="center",
                                    ),
                                ):
                                    me.image(
                                        src=image1_url,
                                        style=(
                                            WINNER_THUMBNAIL_STYLE if winner == model1 else THUMBNAIL_STYLE
                                        ),
                                    )
                                    me.text(
                                        model1,
                                        style=me.Style(font_size="10pt", color="black"),
                                    )

                                with me.content_button(
                                    key=image2_url,
                                    on_click=on_click_image_dialog,
                                    style=me.Style(
                                        flex_direction="column",
                                        display="flex",
                                        align_items="center",
                                    ),
                                ):
                                    me.image(
                                        src=image2_url,
                                        style=(
                                            WINNER_THUMBNAIL_STYLE if winner == model2 else THUMBNAIL_STYLE
                                        ),
                                    )
                                    me.text(
                                        model2,
                                        style=me.Style(font_size="10pt", color="black"),
                                    )
                            me.html(
                                html=f"{timestamp}: {model1} vs. {model2}:  <strong>{winner}</strong> won."
                            )
                            me.html(html=f'With prompt: "<em>{prompt}</em>"')


def on_click_image_dialog(e: me.ClickEvent):
    """show larger image"""
    page_state = me.state(PageState)
    page_state.image_url = e.key
    page_state.is_open = True


def on_click_background_close(e: me.ClickEvent):
    """implementation dialog component's close event """
    page_state = me.state(PageState)
    page_state.is_open = False


def gcs_to_http(gcs_uri: str) -> str:
    """replaces gcsuri with http uri"""
    return gcs_uri.replace(
        "gs://",
        #"https://storage.mtls.cloud.google.com/", # secure
        "https://storage.googleapis.com/" # public
    )


WINNER_THUMBNAIL_STYLE = me.Style(
    height="100px",
    margin=me.Margin(top=10),
    border_radius="18px",
    border=me.Border().all(me.BorderSide(color="green", style="inset", width="5px")),
)

THUMBNAIL_STYLE = me.Style(
    height="100px",
    margin=me.Margin(top=10),
    border_radius="18px",
)
