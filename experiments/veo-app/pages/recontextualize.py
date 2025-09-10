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

from dataclasses import field
import json

import mesop as me

from common.metadata import add_media_item
from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from components.dialog import dialog
from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from components.image_thumbnail import image_thumbnail
from config.default import Default, ABOUT_PAGE_CONTENT
from models.image_models import recontextualize_product_in_scene
from state.state import AppState

config = Default()


with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    RECONTEXT_INFO = next(
        (s for s in about_content["sections"] if s.get("id") == "recontextualize"), None
    )

@me.stateclass
class PageState:
    """Recontext Page State"""

    uploaded_images: list[me.UploadedFile] = field(default_factory=list)  # pylint: disable=invalid-field-call
    uploaded_image_gcs_uris: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    prompt: str = ""
    result_images: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    recontext_sample_count: int = 4
    is_loading: bool = False
    error_message: str = ""
    show_error_dialog: bool = False

    info_dialog_open: bool = False


@me.page(path="/recontextualize")
def recontextualize():
    """Imagen Product Recontext page"""
    with page_scaffold(page_name="recontextualize"):  # pylint: disable=not-context-manager
        state = me.state(PageState)

        if state.info_dialog_open:
            with dialog(is_open=state.info_dialog_open):  # pylint: disable=not-context-manager
                me.text(f'About {RECONTEXT_INFO["title"]}', type="headline-6")
                me.markdown(RECONTEXT_INFO["description"])
                me.divider()
                me.text("Current Settings", type="headline-6")
                me.text(f"Product Images: {state.uploaded_image_gcs_uris}")
                me.text(f"Prompt: {state.prompt}")
                me.text(f"Model: {config.MODEL_IMAGEN_PRODUCT_RECONTEXT}")
                with me.box(style=me.Style(margin=me.Margin(top=16))):
                    me.button("Close", on_click=close_info_dialog, type="stroked")

        with page_frame():  # pylint: disable=not-context-manager
            header("Product in Scene", "scene_based_layout", show_info_button=True, on_info_click=open_info_dialog)

            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=16),
            ):
                me.text("Provide 1-3 images of a product, then recast it in a new scene of your choosing.")
                if len(state.uploaded_image_gcs_uris) < 3:
                    with me.box(
                        style=me.Style(display="flex", flex_direction="row", gap=16, justify_content="center"),
                    ):
                        me.uploader(
                            label="Upload Product Images",
                            on_upload=on_upload,
                            #style=me.Style(width="100%"),
                            key="product_uploader",
                            multiple=True,
                        )
                        library_chooser_button(
                            button_label="Choose Image from Library",
                            on_library_select=on_library_choice,
                            button_type="raised",
                        )
                else:
                    me.text(
                        "Maximum of 3 images uploaded.",
                        style=me.Style(
                            font_style="italic",
                            color=me.theme_var("on-surface-variant"),
                            text_align="center",
                            padding=me.Padding.all(16),
                        ),
                    )

                if state.uploaded_image_gcs_uris:
                    with me.box(
                        style=me.Style(display="flex", flex_wrap="wrap", gap=16)
                    ):
                        for i, uri in enumerate(state.uploaded_image_gcs_uris):
                            image_thumbnail(
                                image_uri=uri, index=i, on_remove=on_remove_image
                            )

                me.input(
                    label="Scene Prompt",
                    on_input=lambda e: on_input_prompt(e.value),
                    style=me.Style(width="100%"),
                )

                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=10,
                        align_items="center",
                        justify_content="center",
                    ),
                ):
                    with me.box(
                        style=me.Style(width="400px", margin=me.Margin(top=16))
                    ):
                        with me.box(
                            style=me.Style(
                                display="flex", justify_content="space-between"
                            )
                        ):
                            me.text(f"Number of images: {state.recontext_sample_count}")
                        me.slider(
                            min=1,
                            max=4,
                            step=1,
                            value=state.recontext_sample_count,
                            on_value_change=on_sample_count_change,
                        )

                    # with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                    me.button("Generate", on_click=on_generate, type="flat")
                    me.button("Clear", on_click=on_clear, type="stroked")

                if state.is_loading:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        )
                    ):
                        me.progress_spinner()

                if state.result_images:
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_wrap="wrap",
                            gap=16,
                            justify_content="center",
                            margin=me.Margin(top=16),
                        )
                    ):
                        for image in state.result_images:
                            me.image(
                                src=image,
                                style=me.Style(width="400px", border_radius=12),
                            )

            with dialog(is_open=state.show_error_dialog):  # pylint: disable=not-context-manager
                me.text("Generation Failed", style=me.Style(font_weight="bold"))
                me.text(state.error_message)
                with me.box(style=me.Style(margin=me.Margin(top=16))):
                    me.button("Close", on_click=on_close_error_dialog, type="stroked")


def on_library_choice(e: LibrarySelectionChangeEvent):
    """Add from library."""
    state = me.state(PageState)
    state.uploaded_image_gcs_uris.append(e.gcs_uri)
    yield


def on_upload(e: me.UploadEvent):
    """Handle uploade event."""
    state = me.state(PageState)
    for file in e.files:
        gcs_url = store_to_gcs(
            "recontext_sources", file.name, file.mime_type, file.getvalue(),
        )
        state.uploaded_image_gcs_uris.append(gcs_url)
    yield


def on_input_prompt(value: str):
    state = me.state(PageState)
    state.prompt = value
    yield


def on_sample_count_change(e: me.SliderValueChangeEvent):
    state = me.state(PageState)
    state.recontext_sample_count = int(e.value)
    yield


def on_remove_image(e: me.ClickEvent):
    state = me.state(PageState)
    del state.uploaded_image_gcs_uris[int(e.key)]
    yield


def on_generate(e: me.ClickEvent):
    app_state = me.state(AppState)
    state = me.state(PageState)
    state.result_images = []
    state.is_loading = True
    yield

    print(f"Generating recontext image with sources: {state.uploaded_image_gcs_uris}")
    try:
        result_gcs_uris = recontextualize_product_in_scene(
            state.uploaded_image_gcs_uris, state.prompt, state.recontext_sample_count
        )
        state.result_images = [
            gcs_uri_to_https_url(uri) for uri in result_gcs_uris
        ]
        add_media_item(
            user_email=app_state.user_email,
            model=config.MODEL_IMAGEN_PRODUCT_RECONTEXT,
            mime_type="image/png",
            prompt=state.prompt,
            gcs_uris=result_gcs_uris,
            source_images_gcs=state.uploaded_image_gcs_uris,
            comment="product recontext",
        )
    except Exception as e:
        state.error_message = str(e)
        state.show_error_dialog = True
    finally:
        state.is_loading = False
        yield


def on_clear(e: me.ClickEvent):
    state = me.state(PageState)
    state.uploaded_image_gcs_uris = []
    state.result_images = []
    yield


def on_close_error_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_error_dialog = False
    yield

def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = True
    yield

def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(PageState)
    state.info_dialog_open = False
    yield