# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import base64
from dataclasses import field
from typing import TYPE_CHECKING, Any

import mesop as me
from absl import logging
from components.header import header
from config.default import Default
from components import constants
from state.state import AppState
from models import image_models
from common import utils as helpers

from common.storage import store_to_gcs
from google.cloud import storage
from components.page_scaffold import page_frame, page_scaffold

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@me.page(path="/edit_images", title="GenMedia Creative Studio - Edit Images")
def edit_images_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold(page_name="edit_images"):  # pylint: disable=not-context-manager
        content(state)


config = Default()

_BOX_STYLE = me.Style(
    flex_basis="max(480px, calc(50% - 48px))",
    background=me.theme_var("background"),
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
    width="100%",
)


@me.stateclass
class EditImagesPageState:
    """Local Page State"""

    is_loading: bool = False

    prompt_input: str = ""
    prompt_placeholder: str = ""
    textarea_key: int = 0

    upload_file: me.UploadedFile = None
    upload_file_key: int = 0
    upload_uri: str = ""
    edit_mode: str = "EDIT_MODE_INPAINT_INSERTION"
    edit_mode_placeholder: str = ""

    mask_mode: str = "MASK_MODE_BACKGROUND"
    mask_mode_placeholder = ""
    mask_mode_disabled: bool = False

    edit_uri: str = ""

    username: str = ""


def content(app_state: me.state):  # pylint: disable=unused-argument
#def content(app_state: AppState) -> None:
    app_state = me.state(AppState)
    page_state = me.state(EditImagesPageState)
    page_state.username = helpers.extract_username(app_state.user_email)
    logging.info("Page loaded with state: %s", page_state)
    logging.info("Username: %s", page_state.username)
    logging.info("User email: %s", app_state.user_email)

    with page_frame():  # pylint: disable=not-context-manager

           
            # Page Header
            header("Edit Images", "edit")

            # Page Contents
            with me.box(
                style=me.Style(
                    margin=me.Margin(left="auto", right="auto"),
                    width="min(1024px, 100%)",
                    gap="24px",
                    display="flex",
                    flex_direction="column",
                ),
            ):
                # Edit input & output
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=35,
                        border_radius=20,
                    ),
                ):
                    with me.box(style=_BOX_STYLE):
                        me.text("Upload Image", style=me.Style(font_weight="bold"))
                        me.box(style=me.Style(height="12px"))
                        if page_state.upload_file:
                            me.image(
                                src=f"data:{page_state.upload_file.mime_type};base64,{base64.b64encode(page_state.upload_file.getvalue()).decode()}",
                                style=me.Style(
                                    width="460px",
                                    border_radius=12,
                                    align_self="end",
                                    justify_content="center",
                                ),
                                key=str(page_state.upload_file_key),
                            )
                        else:
                            me.box(
                                style=me.Style(height="400px", width="460px"),
                            )
                        me.box(style=me.Style(height="12px"))
                        me.uploader(
                            label="Upload Image",
                            accepted_file_types=["image/jpeg", "image/png"],
                            on_upload=on_upload,
                            type="flat",
                            color="primary",
                            style=me.Style(font_weight="bold"),
                        )
                    with me.box(style=_BOX_STYLE):
                        me.text(
                            "Output Image",
                            style=me.Style(font_weight="bold", align_self="top"),
                        )
                        me.box(style=me.Style(height="12px"))
                        if page_state.is_loading:
                            with me.box(
                                style=me.Style(
                                    align_items="center",
                                    display="flex",
                                    justify_content="center",
                                    position="relative",
                                    top="25%",
                                ),
                            ):
                                me.progress_spinner()
                        else:
                            if page_state.edit_uri:
                                for idx, uri in enumerate(
                                    [page_state.edit_uri],
                                ):
                                    me.image(
                                        src=helpers.gcs_uri_to_https_url(uri),
                                        style=me.Style(
                                            align_self="end",
                                            justify_content="center",
                                            width="460px",
                                            border_radius=12,
                                        ),
                                        key=f"edit_{idx}",
                                    )
                            else:
                                me.box(
                                    style=me.Style(
                                        height="400px",
                                        width="460px",
                                    ),
                                )
                            me.box(style=me.Style(height="12px"))
                            me.box(style=me.Style(height="20px"))

                # Edit controls
                with me.box(style=_BOX_STYLE):
                    me.text("What do you want to do with this image?")
                    me.select(
                        label="Edit mode",
                        options=constants.EDIT_MODE_OPTIONS,
                        key="edit_mode",
                        on_selection_change=on_selection_change_edit_mode,
                        value=page_state.edit_mode,
                        placeholder=page_state.edit_mode_placeholder,
                    )
                    me.select(
                        label="Mask Mode",
                        options=constants.MASK_MODE_OPTIONS,
                        key="mask_mode",
                        disabled=page_state.mask_mode_disabled,
                        on_selection_change=on_selection_change_mask_mode,
                        value=page_state.mask_mode,
                        placeholder=page_state.mask_mode_placeholder,
                    )
                    me.textarea(
                        label="Describe what you want to insert in the selected zone.",
                        key="prompt_input",
                        on_blur=on_blur,
                        rows=2,
                        autosize=True,
                        max_rows=5,
                        style=me.Style(width="100%"),
                        value=page_state.prompt_placeholder,
                    )
                    with me.box(
                        style=me.Style(
                            display="flex",
                            justify_content="space-between",
                        ),
                    ):
                        # Clear
                        me.button(
                            "Clear",
                            color="primary",
                            type="stroked",
                            on_click=on_click_clear_images,
                        )
                        # Generate
                        me.button(
                            "Generate",
                            color="primary",
                            type="flat",
                            on_click=on_click_image_edit,
                        )


def on_blur(event: me.InputBlurEvent) -> None:
    state = me.state(EditImagesPageState)
    setattr(state, event.key, event.value)


# Event Handlers
def on_click_clear_images(event: me.ClickEvent) -> None:
    """Click Event to clear images."""
    del event
    state = me.state(EditImagesPageState)
    state.prompt_input = ""
    state.prompt_placeholder = ""
    state.upload_file = None
    state.upload_file_key += 1
    state.upload_uri = ""
    state.textarea_key += 1
    state.edit_uri = ""


async def on_upload(e: me.UploadEvent):
    """Upload image to GCS"""
    state = me.state(EditImagesPageState)
    contents = e.file.getvalue()
    destination_blob_name = store_to_gcs(
        "uploads", e.file.name, e.file.mime_type, contents
    )
    state.upload_uri = f"gs://{destination_blob_name}"
    state.upload_file_key += 1


def on_selection_change_edit_mode(
    event: me.SelectSelectionChangeEvent,
) -> Generator[Any, Any, Any]:
    """Change Event For Selecting an Image Model."""
    state = me.state(EditImagesPageState)
    setattr(state, event.key, event.value)
    yield


def on_selection_change_mask_mode(
    event: me.SelectSelectionChangeEvent,
) -> Generator[Any, Any, Any]:
    state = me.state(EditImagesPageState)
    state.mask_mode = event.value
    yield


async def on_click_image_edit(event: me.ClickEvent) -> AsyncGenerator[Any, Any, Any]:
    """Creates images from Imagen and returns a list of gcs uris."""
    del event  # Unused.
    state = me.state(EditImagesPageState)
    state.is_loading = True
    state.edit_uri = ""
    yield

    storage_client = storage.Client(project=config.PROJECT_ID)
    bucket = storage_client.bucket(config.GENMEDIA_BUCKET)
    blob = bucket.blob(state.upload_uri.replace(f"gs://{config.GENMEDIA_BUCKET}/", ""))
    image_bytes = blob.download_as_bytes()

    edit_uris = await image_models.edit_image(
        model=config.MODEL_IMAGEN_EDITING,
        prompt=state.prompt_input,
        edit_mode=state.edit_mode,
        mask_mode=state.mask_mode,
        reference_image_bytes=image_bytes,
        number_of_images=1,
    )
    if edit_uris:
        state.edit_uri = edit_uris[0]
    state.is_loading = False
    yield
