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
import mesop.labs as mel

from common.analytics import log_ui_click, track_click

from components.header import header
from components.library.events import LibrarySelectionChangeEvent
from components.library.library_chooser_button import library_chooser_button
from components.page_scaffold import page_frame, page_scaffold
from state.starter_pack_state import StarterPackState
from state.state import AppState
import common.storage as storage
from components.tab_nav import tab_group, Tab
import models.starter_pack as model
from common.metadata import add_media_item
from config.default import Default

cfg = Default()

from common.utils import create_display_url
from config.default import Default

@me.page(
    path="/starter-pack",
    title="Starter Pack",
)
def page():
    with page_scaffold(page_name="starter-pack"):  # pylint: disable=E1129
        with page_frame():  # pylint: disable=E1129
                header("Starter Pack", "style")  # pylint: disable=E1129
                with me.box(
                    style=me.Style(
                        display="grid",
                        grid_template_columns="1fr 1fr",
                        gap=16,
                        padding=me.Padding.all(16),
                    )
                ):
                    with me.box():
                        #me.text("Inputs", type="headline-5")
                        tabs = [
                            Tab(
                                label="Look to Starter Pack",
                                content=look_to_starter_pack_content,
                                selected=me.state(StarterPackState).selected_tab_index == 0,
                            ),
                            Tab(
                                label="Starter Pack to Look",
                                content=starter_pack_to_look_content,
                                selected=me.state(StarterPackState).selected_tab_index == 1,
                            ),
                        ]
                        tab_group(tabs, on_tab_click=on_tab_click)

                    with me.box(style=me.Style(display="flex", flex_direction="column")):
                        #me.text("Outputs", type="headline-5")
                        if me.state(StarterPackState).selected_tab_index == 0:
                            with me.box(style=me.Style(margin=me.Margin(top=16))):
                                me.text("Generated Starter Pack", type="headline-6")
                                with me.box(
                                    style=me.Style(
                                        border=me.Border.all(
                                            me.BorderSide(width=1, style="solid", color="#ccc")
                                        ),
                                        border_radius=8,
                                        padding=me.Padding.all(16),
                                        margin=me.Margin(top=8),
                                        height=400,
                                        display="flex",
                                        align_items="center",
                                        justify_content="center",
                                    )
                                ):
                                    if me.state(StarterPackState).is_generating_starter_pack:
                                        me.progress_spinner()
                                    elif me.state(StarterPackState).generated_starter_pack_display_url:
                                        me.image(
                                            src=me.state(StarterPackState).generated_starter_pack_display_url,
                                            style=me.Style(width="100%", max_height=400, object_fit="contain", border_radius=8),
                                        )
                                    else:
                                        me.text("Output will appear here")
                                if me.state(StarterPackState).look_image_uri or me.state(StarterPackState).generated_starter_pack_uri:
                                    with me.box(style=me.Style(display="flex", justify_content="center", margin=me.Margin(top=16))):
                                        me.button("Clear", on_click=on_click_clear_starter_pack, type="stroked")

                        if me.state(StarterPackState).selected_tab_index == 1:
                            with me.box(style=me.Style(margin=me.Margin(top=16))):
                                me.text("Generated Look", type="headline-6")
                                with me.box(
                                    style=me.Style(
                                        border=me.Border.all(
                                            me.BorderSide(width=1, style="solid", color="#ccc")
                                        ),
                                        border_radius=8,
                                        padding=me.Padding.all(16),
                                        margin=me.Margin(top=8),
                                        height=400,
                                        display="flex",
                                        align_items="center",
                                        justify_content="center",
                                    )
                                ):
                                    if me.state(StarterPackState).is_generating_look:
                                        me.progress_spinner()
                                    elif me.state(StarterPackState).generated_look_display_url:
                                        me.image(
                                            src=me.state(StarterPackState).generated_look_display_url,
                                            style=me.Style(width="100%", max_height=400, object_fit="contain", border_radius=8),
                                        )
                                    else:
                                        me.text("Output will appear here")
                                if me.state(StarterPackState).starter_pack_image_uri or me.state(StarterPackState).model_image_uri or me.state(StarterPackState).generated_look_uri:
                                    with me.box(style=me.Style(display="flex", justify_content="center", margin=me.Margin(top=16))):
                                        me.button("Clear", on_click=on_click_clear_look, type="stroked")

@me.component
def look_to_starter_pack_content():
    with me.box(style=me.Style(padding=me.Padding.all(16))):
        me.text(
            "Upload an image of a person wearing an outfit (a 'look') to generate a starter pack collage.",
            style=me.Style(margin=me.Margin(bottom=16)),
        )
        with me.box(style=me.Style(display="flex", align_items="center", justify_content="center", gap=8, margin=me.Margin(top=16))):
            me.uploader(
                label="Upload Look Image",
                on_upload=on_upload_look_image,
                style=me.Style(width="100%"),
                accepted_file_types=["image/jpeg", "image/png", "image/webp"],
            )
            library_chooser_button(
                key="library_look",
                on_library_select=on_library_chooser,
                button_type="icon",
            )
        if me.state(StarterPackState).look_image_display_url:
            me.image(
                src=me.state(StarterPackState).look_image_display_url,
                style=me.Style(
                    width="100%",
                    margin=me.Margin(top=16),
                    border_radius=8,
                ),
            )
        me.button(
            "Generate Starter Pack",
            on_click=on_click_generate_starter_pack,
            type="raised",
            style=me.Style(margin=me.Margin(top=16)),
        )

@me.component
def starter_pack_to_look_content():
    with me.box(style=me.Style(padding=me.Padding.all(16))):
        me.text(
            "Upload a starter pack/mood board and a model image to generate an image of the model wearing the outfit.",
            style=me.Style(margin=me.Margin(bottom=16)),
        )
        with me.box(style=me.Style(display="flex", align_items="center", justify_content="center", gap=8, margin=me.Margin(top=16))):
            me.uploader(
                label="Upload Starter Pack Image",
                on_upload=on_upload_starter_pack_image,
                style=me.Style(width="100%"),
                accepted_file_types=["image/jpeg", "image/png"],
            )
            library_chooser_button(
                key="library_starter_pack",
                on_library_select=on_library_chooser,
                button_type="icon",
            )
        if me.state(StarterPackState).starter_pack_image_display_url:
            me.image(
                src=me.state(StarterPackState).starter_pack_image_display_url,
                style=me.Style(
                    width="100%",
                    margin=me.Margin(top=16),
                    border_radius=8,
                ),
            )
        with me.box(style=me.Style(display="flex", align_items="center",justify_content="center", gap=8, margin=me.Margin(top=16))):
            me.uploader(
                label="Upload Model Image",
                on_upload=on_upload_model_image,
                style=me.Style(width="100%"),
                accepted_file_types=["image/jpeg", "image/png"],
            )
            library_chooser_button(
                key="library_model",
                on_library_select=on_library_chooser,
                button_type="icon",
            )
            me.button("Create Virtual Model", on_click=on_click_generate_virtual_model)

        if me.state(StarterPackState).is_generating_virtual_model:
            with me.box(style=me.Style(display="flex", justify_content="center", margin=me.Margin(top=16))):
                me.progress_spinner()
        elif me.state(StarterPackState).model_image_display_url:
            me.image(
                src=me.state(StarterPackState).model_image_display_url,
                style=me.Style(
                    width="100%",
                    margin=me.Margin(top=16),
                    border_radius=8,
                ),
            )

        me.button(
            "Generate Look",
            on_click=on_click_generate_look,
            type="raised",
            style=me.Style(margin=me.Margin(top=16)),
        )

def on_tab_click(e: me.ClickEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="starter_pack_tab",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"key": e.key},
    )
    state = me.state(StarterPackState)
    _, tab_index = e.key.split("-")
    state.selected_tab_index = int(tab_index)
    yield

def on_upload_look_image(e: me.UploadEvent):
    state = me.state(StarterPackState)
    uploaded_file = e.file
    gcs_uri = storage.store_to_gcs(
        folder="starter_pack_uploads",
        file_name=uploaded_file.name,
        mime_type=uploaded_file.mime_type,
        contents=uploaded_file.getvalue(),
    )
    state.look_image_uri = gcs_uri
    state.look_image_display_url = create_display_url(gcs_uri)
    print(f"Look image URI: {state.look_image_uri}")
    yield


def on_library_chooser(e: LibrarySelectionChangeEvent):
    state = me.state(StarterPackState)
    print(f"EVENT: {e}")

    if e.chooser_id == "library_look":
        state.look_image_uri = e.gcs_uri
        state.look_image_display_url = create_display_url(e.gcs_uri)
    elif e.chooser_id == "library_starter_pack":
        state.starter_pack_image_uri = e.gcs_uri
        state.starter_pack_image_display_url = create_display_url(e.gcs_uri)
    elif e.chooser_id == "library_model":
        state.model_image_uri = e.gcs_uri
        state.model_image_display_url = create_display_url(e.gcs_uri)
    yield


def on_upload_starter_pack_image(e: me.UploadEvent):

    state = me.state(StarterPackState)
    uploaded_file = e.file
    gcs_uri = storage.store_to_gcs(
        folder="starter_pack_uploads",
        file_name=uploaded_file.name,
        mime_type=uploaded_file.mime_type,
        contents=uploaded_file.getvalue(),
    )

    state.starter_pack_image_uri = gcs_uri
    state.starter_pack_image_display_url = create_display_url(gcs_uri)
    yield





def on_upload_model_image(e: me.UploadEvent):
    state = me.state(StarterPackState)
    uploaded_file = e.file
    gcs_uri = storage.store_to_gcs(
        folder="starter_pack_uploads",
        file_name=uploaded_file.name,
        mime_type=uploaded_file.mime_type,
        contents=uploaded_file.getvalue(),
    )

    state.model_image_uri = gcs_uri
    state.model_image_display_url = create_display_url(gcs_uri)

    yield





def on_click_generate_virtual_model(e: me.ClickEvent):
    state = me.state(StarterPackState)
    app_state = me.state(AppState)
    state.is_generating_virtual_model = True
    yield

    gcs_uri = model.generate_virtual_model()
    state.model_image_uri = gcs_uri
    state.model_image_display_url = create_display_url(gcs_uri)
    #add_media_item(
    #    user_email=app_state.user_email,
    #    model=cfg.MODEL_IMAGEN4_FAST,
    #    mime_type="image/png",
    #    gcs_uris=[gcs_uri],
    #    comment="virtual model",
    #    source_images_gcs=[]
    #)
    state.is_generating_virtual_model = False
    yield





@track_click(element_id="starter_pack_generate_starter_pack_button")
def on_click_generate_starter_pack(e: me.ClickEvent):
    state = me.state(StarterPackState)
    app_state = me.state(AppState)
    state.is_generating_starter_pack = True
    yield

    gcs_uri = model.generate_starter_pack_from_look(
        look_image_uri=state.look_image_uri
    )

    state.generated_starter_pack_uri = gcs_uri
    state.generated_starter_pack_display_url = create_display_url(gcs_uri)

    add_media_item(
        user_email=app_state.user_email,
        model=cfg.GEMINI_IMAGE_GEN_MODEL,
        mime_type="image/png",
        gcs_uris=[gcs_uri],
        comment="look to starter pack",
        source_images_gcs=[state.look_image_uri]
    )

    state.is_generating_starter_pack = False

    yield





@track_click(element_id="starter_pack_generate_look_button")

def on_click_generate_look(e: me.ClickEvent):

    state = me.state(StarterPackState)

    app_state = me.state(AppState)

    state.is_generating_look = True

    yield



    gcs_uri = model.generate_look_from_starter_pack(

        starter_pack_uri=state.starter_pack_image_uri,

        model_image_uri=state.model_image_uri,

    )

    state.generated_look_uri = gcs_uri

    state.generated_look_display_url = create_display_url(gcs_uri)
    add_media_item(
        user_email=app_state.user_email,
        model=cfg.GEMINI_IMAGE_GEN_MODEL,
        mime_type="image/png",
        gcs_uris=[gcs_uri],
        comment="starter pack to look",
        source_images_gcs=[state.starter_pack_image_uri, state.model_image_uri]
    )
    state.is_generating_look = False
    yield

@track_click(element_id="starter_pack_clear_starter_pack_button")
def on_click_clear_starter_pack(e: me.ClickEvent):
    state = me.state(StarterPackState)
    state.look_image_uri = ""
    state.look_image_display_url = ""
    state.generated_starter_pack_uri = ""
    state.generated_starter_pack_display_url = ""
    yield

@track_click(element_id="starter_pack_clear_look_button")
def on_click_clear_look(e: me.ClickEvent):
    state = me.state(StarterPackState)
    state.starter_pack_image_uri = ""
    state.starter_pack_image_display_url = ""
    state.model_image_uri = ""
    state.model_image_display_url = ""
    state.generated_look_uri = ""
    state.generated_look_display_url = ""
    yield
