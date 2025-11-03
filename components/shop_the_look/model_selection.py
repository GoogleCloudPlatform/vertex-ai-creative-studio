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

import uuid

import mesop as me

from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from config.default import Default
from models import shop_the_look_workflow
from state.shop_the_look_state import PageState

config = Default()


@me.component
def model_selection():
    """Renders the UI for selecting or uploading a model image.

    This component displays an uploader to add new models and a gallery of
    existing models that can be selected.
    """
    state = me.state(PageState)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=10,
            align_items="center",
            width="100%",
        )
    ):
        me.text(
            text="Choose a Model",
            type="headline-2",
        )
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
                    align_items="left",
                )
            ):
                with me.box(
                    style=me.Style(
                        position="relative",
                        height="100%",
                        margin=me.Margin(left=7, top=7),
                        cursor="pointer",
                    ),
                    key="model",
                ):
                    me.uploader(
                        label="",
                        accepted_file_types=["image/jpeg", "image/png"],
                        on_upload=on_upload_model_image,
                        type="flat",
                        color="primary",
                        style=me.Style(
                            position="relative",
                            cursor="pointer",
                            width="200px",
                            height="200px",
                            object_fit="cover",
                            border_radius="5px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                            background="#FFFFFF",
                        ),
                        key="model",
                        multiple=True,
                    )
                    me.icon(
                        "add",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="35px",
                            left="35px",
                            width="35px",
                            height="35px",
                            font_size="35px",
                        ),
                    )
                    me.icon(
                        "person_outline",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="50px",
                            left="55px",
                            width="100px",
                            height="100px",
                            font_size="100px",
                        ),
                    )
                    me.text(
                        text="Add Model",
                        style=me.Style(
                            position="absolute",
                            text_align="center",
                            bottom="45px",
                            left="55px",
                            font_size="20px",
                        ),
                    )

            for model in state.models:
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        gap=5,
                        align_items="left",
                    )
                ):
                    with me.box(
                        key=f"{model.model_image}",
                        style=me.Style(
                            position="relative",
                            height="100%",
                            margin=me.Margin(left=7, top=7),
                            cursor="pointer",
                        ),
                        on_click=on_model_click,
                    ):
                        me.image(
                            src=gcs_uri_to_https_url(model.model_image),
                            style=me.Style(
                                object_fit="cover",
                                border_radius="5px",
                                box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                                max_height="200px",
                                height="auto",
                            ),
                        )


def on_model_click(e: me.ClickEvent):
    """Handles the click event on a model's image.

    Sets the selected model in the page state for VTO generation.

    Args:
        e: The Mesop click event, where e.key is the GCS URI of the image.
    """
    state = me.state(PageState)
    state.reference_image_gcs_model = e.key
    state.before_image_uri = e.key
    for m in state.models:
        if m.model_image in e.key:
            state.selected_model = m
    yield


def on_upload_model_image(e: me.UploadEvent):
    """Handles the upload of one or more model images.

    For each uploaded file, it generates a unique name, stores it in Google
    Cloud Storage, and creates a corresponding metadata entry in Firestore.
    Finally, it reloads the model data to update the UI.

    This is a generator function that yields to update the UI with the
    upload progress.

    Args:
        e: The Mesop upload event containing the file(s).
    """
    state = me.state(PageState)

    for i, file in enumerate(e.files):
        state.current_status = f"Uploading {i + 1} of {len(e.files)}"
        yield
        filename_uuid = str(uuid.uuid4())
        file_ext = file.name.split(".")[-1]
        filename = f"{filename_uuid}.{file_ext}"

        file_path = f"gs://{config.GENMEDIA_BUCKET}/uploads/models/{filename}"
        store_to_gcs(
            "uploads/models",
            filename.lower(),
            file.mime_type,
            file.getvalue(),
        )
        shop_the_look_workflow.store_model_data(file_path)

        state.current_status = ""
        yield

    state.models = shop_the_look_workflow.load_model_data()
    yield