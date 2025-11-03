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

import models.shop_the_look_workflow as shop_the_look_workflow
from common.storage import store_to_gcs
from common.utils import gcs_uri_to_https_url
from config.default import Default
from state.shop_the_look_state import PageState

config = Default()

@me.component
def look_selection():
    """Renders the UI for selecting or uploading clothing items (looks).

    This component provides uploaders for different categories of apparel
    (tops, bottoms, dresses, shoes) and displays a gallery of available
    items. Users can select a combination of items to create a look.
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
            text="Choose a Look",
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
                        cursor="pointer",
                    ),
                    key="apparel",
                ):
                    me.uploader(
                        label="",
                        accepted_file_types=["image/jpeg", "image/png"],
                        on_upload=on_upload_article_image,
                        type="flat",
                        color="primary",
                        style=me.Style(
                            position="relative",
                            cursor="pointer",
                            width="150px",
                            height="150px",
                            object_fit="cover",
                            border_radius="5px",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                            background="#FFFFFF",
                            margin=me.Margin(left=10, top=10),
                        ),
                        key="top",
                        multiple=True,
                    )
                    me.icon(
                        "add",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="20px",
                            left="30px",
                            width="30px",
                            height="30px",
                            font_size="30px",
                        ),
                    )
                    me.icon(
                        "apparel",
                        style=me.Style(
                            color="black",
                            position="absolute",
                            top="45px",
                            left="55px",
                            width="50px",
                            height="50px",
                            font_size="50px",
                        ),
                    )
                    me.text(
                        text="Add Top",
                        style=me.Style(
                            position="absolute",
                            text_align="center",
                            bottom="35px",
                            left="45px",
                            font_size="20px",
                        ),
                    )
            with me.box(
                style=me.Style(
                    position="relative",
                    height="100%",
                    cursor="pointer",
                ),
                key="apparel",
            ):
                me.uploader(
                    label="",
                    accepted_file_types=["image/jpeg", "image/png"],
                    on_upload=on_upload_article_image,
                    type="flat",
                    color="primary",
                    style=me.Style(
                        position="relative",
                        cursor="pointer",
                        width="150px",
                        height="150px",
                        object_fit="cover",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                        background="#FFFFFF",
                        margin=me.Margin(left=10, top=10),
                    ),
                    key="bottom",
                    multiple=True,
                )
                me.icon(
                    "add",
                    style=me.Style(
                        color="black",
                        position="absolute",
                        top="20px",
                        left="30px",
                        width="30px",
                        height="30px",
                        font_size="30px",
                    ),
                )
                me.icon(
                    "styler",
                    style=me.Style(
                        color="black",
                        position="absolute",
                        top="45px",
                        left="55px",
                        width="50px",
                        height="50px",
                        font_size="50px",
                    ),
                )
                me.text(
                    text="Add Bottom",
                    style=me.Style(
                        position="absolute",
                        text_align="center",
                        bottom="35px",
                        left="30px",
                        font_size="20px",
                    ),
                )

            with me.box(
                style=me.Style(
                    position="relative",
                    height="100%",
                    cursor="pointer",
                ),
                key="apparel",
            ):
                me.uploader(
                    label="",
                    accepted_file_types=["image/jpeg", "image/png"],
                    on_upload=on_upload_article_image,
                    type="flat",
                    color="primary",
                    style=me.Style(
                        position="relative",
                        cursor="pointer",
                        width="150px",
                        height="150px",
                        object_fit="cover",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                        background="#FFFFFF",
                        margin=me.Margin(left=10, top=10),
                    ),
                    key="dress",
                    multiple=True,
                )
                me.icon(
                    "add",
                    style=me.Style(
                        color="black",
                        position="absolute",
                        top="20px",
                        left="30px",
                        width="30px",
                        height="30px",
                        font_size="30px",
                    ),
                )
                me.icon(
                    "girl",
                    style=me.Style(
                        color="black",
                        position="absolute",
                        top="35px",
                        left="45px",
                        width="70px",
                        height="70px",
                        font_size="70px",
                    ),
                )
                me.text(
                    text="Add Dress",
                    style=me.Style(
                        position="absolute",
                        text_align="center",
                        bottom="35px",
                        left="35px",
                        font_size="20px",
                    ),
                )

            with me.box(
                style=me.Style(
                    position="relative",
                    height="100%",
                    cursor="pointer",
                ),
                key="apparel",
            ):
                me.uploader(
                    label="",
                    accepted_file_types=["image/jpeg", "image/png"],
                    on_upload=on_upload_article_image,
                    type="flat",
                    color="primary",
                    style=me.Style(
                        position="relative",
                        cursor="pointer",
                        width="150px",
                        height="150px",
                        object_fit="cover",
                        border_radius="5px",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
                        background="#FFFFFF",
                        margin=me.Margin(left=10, top=10),
                    ),
                    key="shoe",
                    multiple=True,
                )
                me.icon(
                    "add",
                    style=me.Style(
                        color="black",
                        position="absolute",
                        top="20px",
                        left="30px",
                        width="30px",
                        height="30px",
                        font_size="30px",
                    ),
                )
                me.icon(
                    "steps",
                    style=me.Style(
                        color="black",
                        position="absolute",
                        top="45px",
                        left="55px",
                        width="50px",
                        height="50px",
                        font_size="50px",
                    ),
                )
                me.text(
                    text="Add Shoe",
                    style=me.Style(
                        position="absolute",
                        text_align="center",
                        bottom="35px",
                        left="35px",
                        font_size="20px",
                    ),
                )

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
                        key=f"{item.item_id}_{item.article_type}",
                        style=me.Style(
                            position="relative",
                            height="100%",
                            margin=me.Margin(left=10, top=10),
                            cursor="pointer",
                        ),
                        on_click=article_on_click,
                    ):
                        me.icon(
                            "check_circle",
                            style=me.Style(
                                color=("green" if item.selected else "#666"),
                                position="absolute",
                                top="1px",
                                left="5px",
                                opacity=("1" if item.selected else ".1"),
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
                                opacity=(
                                    "1"
                                    if (item.available_to_select or item.selected)
                                    else ".3"
                                ),
                            ),
                        )
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="row",
            gap=5,
            align_items="right",
        ),
    ):
        me.button(
            "Continue",
            type="flat",
            style=me.Style(
                width=75,
                height=40,
                border_radius=5,
                cursor="pointer",
                margin=me.Margin(left=5, top=10),
            ),
            on_click=on_continue_click,
        )


def on_upload_article_image(e: me.UploadEvent):
    """Handles the upload of one or more article (clothing) images.

    For each uploaded file, it generates a unique name, stores it in Google
    Cloud Storage under a path determined by the article type (e.g., 'top'),
    and creates a corresponding metadata entry in Firestore. Finally, it
    reloads the article data to update the UI.

    This is a generator function that yields to update the UI with the
    upload progress.

    Args:
        e: The Mesop upload event. `e.key` contains the article type, and
           `e.files` contains the file(s).
    """
    state = me.state(PageState)

    for i, file in enumerate(e.files):
        state.current_status = f"Uploading {i + 1} of {len(e.files)}"
        yield
        filename_uuid = str(uuid.uuid4())
        file_ext = file.name.split(".")[-1]
        filename = f"{filename_uuid}.{file_ext}"

        file_path = f"gs://{config.GENMEDIA_BUCKET}/uploads/apparel/{e.key}/{filename}"
        gcs_url = store_to_gcs(
            f"uploads/apparel/{e.key}",
            filename.lower(),
            file.mime_type,
            file.getvalue(),
        )
        state.reference_image_gcs_clothing.append(f"{gcs_url}")
        state.reference_image_uri_clothing.append(gcs_uri_to_https_url(gcs_url))
        article_type = gcs_url.split("/")[-2]
        shop_the_look_workflow.store_article_data(file_path, article_type)

        state.current_status = ""
        yield

    shop_the_look_workflow.load_article_data()
    yield


def article_on_click(e: me.ClickEvent):
    """Handles the click event on a clothing item.

    This function toggles the 'selected' state of the clicked item. It also
    manages the 'available_to_select' state of other items based on clothing
    compatibility rules (e.g., selecting a dress disables tops and bottoms).

    Args:
        e: The Mesop click event. `e.key` is a string combining the item_id
           and article_type, e.g., "some_uuid_top".
    """
    state = me.state(PageState)
    selected_type = e.key.split("_")[-1]
    selected_id = e.key.split("_")[-2]

    selected = False
    for item in state.articles:
        if item.item_id == selected_id:
            item.selected = not item.selected
            selected = item.selected

    for item in state.articles:
        if item.item_id != selected_id:
            if selected_type == "shoe" and item.article_type == "shoe":
                item.available_to_select = not selected
                item.selected = False
            elif selected_type == "dress" and item.article_type in [
                "dress",
                "top",
                "bottom",
            ]:
                item.available_to_select = not selected
                item.selected = False
            elif selected_type == "top" and item.article_type in ["dress", "top"]:
                item.available_to_select = not selected
                item.selected = False
            elif selected_type == "bottom" and item.article_type in ["dress", "bottom"]:
                item.available_to_select = not selected
                item.selected = False
    yield


def on_continue_click(e: me.ClickEvent):
    """Handles the click event for the 'Continue' button.

    Advances the user to the next step in the workflow.

    Args:
        e: The Mesop click event.
    """
    state = me.state(PageState)
    state.look = 2
    yield