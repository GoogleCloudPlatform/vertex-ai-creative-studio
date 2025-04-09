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

from dataclasses import field
import random
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import mesop as me

from common.metadata import update_elo_ratings
from config.default import Default
from prompts.utils import PromptManager
from state.state import AppState
from components.header import header

from models.set_up import ModelSetup, load_default_models

from models.gemini_model import (
    generate_content,
    generate_images,
)
from models.generate import images_from_flux, images_from_imagen, images_from_stable_diffusion, study_fetch


# Initialize configuration
client, model_id = ModelSetup.init()
MODEL_ID = model_id
config = Default()
prompt_manager = PromptManager()
logging.basicConfig(level=logging.DEBUG)


IMAGEN_MODELS = [config.MODEL_IMAGEN2, config.MODEL_IMAGEN3_FAST, config.MODEL_IMAGEN3, config.MODEL_IMAGEN32,]
GEMINI_MODELS = [config.MODEL_GEMINI2]


@me.stateclass
class PageState:
    """Local Page State"""

    temp_name: str = ""
    is_loading: bool = False

    # pylint: disable=invalid-field-call
    arena_prompt: str = ""
    image_negative_prompt_input: str = ""
    image_aspect_ratio: str = "1:1"
    arena_textarea_key: int = 0
    arena_model1: str = ""
    arena_model2: str = ""
    arena_output: list[str] = field(default_factory=lambda: [])
    chosen_model: str = ""
    study: str = "live"
    study_models: list[str] = field(default_factory=list)
    # pylint: disable=invalid-field-call


def arena_images(input: str, study: str):
    """Create images for arena comparison"""
    state = me.state(PageState)
    if input == "":  # handle condition where someone hits "random" but doesn't modify
        if state.arena_prompt != "":
            input = state.arena_prompt
    state.arena_output.clear()

    logging.info("BATTLE: %s vs. %s", state.arena_model1, state.arena_model2)

    prompt = input
    logging.info("prompt: %s", prompt)
    if state.image_negative_prompt_input:
        logging.info("negative prompt: %s", state.image_negative_prompt_input)
    
    with ThreadPoolExecutor() as executor:  # Create a thread pool
        futures = []
        if study == "live":
            # model 1
            if state.arena_model1 in IMAGEN_MODELS:
                logging.info("model 1: %s", state.arena_model1)
                futures.append(
                    executor.submit(
                        images_from_imagen,
                        state.arena_model1,
                        prompt,
                        state.image_aspect_ratio,
                    )
                )
            elif state.arena_model1.startswith(config.MODEL_GEMINI2):
                logging.info("model 1: %s", state.arena_model1)
                futures.append(
                    executor.submit(
                        generate_images,
                        prompt,
                    )
                )
            elif state.arena_model1.startswith(config.MODEL_FLUX1):
                if config.MODEL_FLUX1_ENDPOINT_ID:
                    logging.info("model 1: %s", state.arena_model1)
                    futures.append(
                        executor.submit(
                            images_from_flux,
                            state.arena_model1,
                            prompt,
                            state.image_aspect_ratio,
                        )
                    )
                else:
                    logging.error("no endpoint defined for %s", state.arena_model1)
            elif state.arena_model1.startswith(config.MODEL_STABLE_DIFFUSION):
                if config.MODEL_STABLE_DIFFUSION_ENDPOINT_ID:
                    logging.info("model 1: %s", state.arena_model1)
                    futures.append(
                        executor.submit(
                            images_from_stable_diffusion,
                            state.arena_model1,
                            prompt,
                            state.image_aspect_ratio,
                        )
                    )
                else:
                    logging.error("no endpoint defined for %s", state.arena_model1)

            # model 2
            if state.arena_model2 in IMAGEN_MODELS:
                logging.info("model 2: %s", state.arena_model2)
                futures.append(
                    executor.submit(
                        images_from_imagen,
                        state.arena_model2,
                        prompt,
                        state.image_aspect_ratio,
                    )
                )
            elif state.arena_model2.startswith(config.MODEL_GEMINI2):
                logging.info("model 2: %s", state.arena_model2)
                futures.append(
                    executor.submit(
                        generate_images,
                        prompt,
                    )
                )
            elif state.arena_model2.startswith(config.MODEL_FLUX1):
                if config.MODEL_FLUX1_ENDPOINT_ID:
                    logging.info("model 2: %s", state.arena_model2)
                    futures.append(
                        executor.submit(
                            images_from_flux,
                            state.arena_model2,
                            prompt,
                            state.image_aspect_ratio,
                        )
                    )
                else:
                    logging.error("no endpoint defined for %s", state.arena_model2)
            elif state.arena_model2.startswith(config.MODEL_STABLE_DIFFUSION):
                if config.MODEL_STABLE_DIFFUSION_ENDPOINT_ID:
                    logging.info("model 2: %s", state.arena_model2)
                    futures.append(
                        executor.submit(
                            images_from_stable_diffusion,
                            state.arena_model2,
                            prompt,
                            state.image_aspect_ratio,
                        )
                    )
                else:
                    logging.error("no endpoint defined for %s", state.arena_model2)
        # Fetch images from study
        else:
            futures.extend([
                executor.submit(
                    study_fetch,
                    state.arena_model1,
                    prompt
                ),
                executor.submit(
                    study_fetch,
                    state.arena_model2,
                    prompt
                )
            ])
        
        for future in as_completed(futures):  # Wait for tasks to complete
            try:
                result = future.result()  # Get the result of each task
                state.arena_output.extend(
                    result
                )  # Assuming images_from_imagen returns a list
            except Exception as e:
                logging.error(f"Error during image generation: {e}")

def on_click_reload_arena(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Reload arena handler"""
    state = me.state(PageState)
    if state.study == "live":
        state.study_models = load_default_models()

    state.arena_prompt = prompt_manager.random_prompt()

    state.arena_output.clear()

    state.is_loading = True
    yield
    print(f"Use {state.study_models}")

    # get random images
    state.arena_model1, state.arena_model2 = random.sample(state.study_models, 2)
    logging.info("%s vs. %s", state.arena_model1, state.arena_model2)
    arena_images(state.arena_prompt, state.study)

    state.is_loading = False
    yield


def on_click_arena_vote(e: me.ClickEvent):
    """Arena vote handler"""
    state = me.state(PageState)
    model_name = getattr(state, e.key)
    logging.info("user preferred %s: %s", e.key, model_name)
    state.chosen_model = model_name
    yield
    # update the elo ratings
    update_elo_ratings(state.arena_model1, state.arena_model2, model_name, state.arena_output, state.arena_prompt, state.study)
    yield
    time.sleep(int(Default.SHOW_RESULTS_PAUSE_TIME))
    yield
    # clear the output and reload
    state.arena_output.clear()
    state.chosen_model = ""
    state.arena_prompt = prompt_manager.random_prompt()
    state.arena_model1, state.arena_model2 = random.sample(state.study_models, 2)
    yield
    arena_images(state.arena_prompt, state.study)
    yield


WELCOME_PROMPT = """
Welcome the user to the battle of the generative media images, and encourage participation by asserting their voting on the images presented. 
This should be one or two sentences.
"""


def reload_welcome(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Handle regeneration of welcome message event"""
    app_state = me.state(AppState)
    app_state.welcome_message = generate_welcome()
    yield


def generate_welcome() -> str:
    """Generate a nice welcome message with Gemini 2.0"""
    return generate_content(WELCOME_PROMPT)


def arena_page_content(app_state: me.state):
    """Arena Mesop Page"""

    page_state = me.state(PageState)
    prompt_manager.prompts_location = app_state.study_prompts_location
    page_state.study = app_state.study
    if page_state.study == "live":
        app_state.study_models = load_default_models()
    page_state.study_models = app_state.study_models
    print(f"======> Starting Page state study models: {page_state.study_models}")

    # TODO this is an initialization function that should be extracted
    if not app_state.welcome_message:
        app_state.welcome_message = generate_welcome()
    if not page_state.arena_prompt:
        page_state.arena_prompt = prompt_manager.random_prompt()
        page_state.arena_model1, page_state.arena_model2 = random.sample(app_state.study_models, 2)
        arena_images(page_state.arena_prompt, app_state.study)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
        ),
    ):
        with me.box(
            style=me.Style(
                background=me.theme_var("background"),
                height="100%",
                overflow_y="scroll",
                margin=me.Margin(bottom=20),
            )
        ):
            with me.box(
                style=me.Style(
                    background=me.theme_var("background"),
                    padding=me.Padding(top=24, left=24, right=24, bottom=24),
                    display="flex",
                    flex_direction="column",
                )
            ):
                header("Arena" + (f" [Active Study: {app_state.study}]" if app_state.study != "live" else ""), "stadium")

                # welcome message
                with me.box(
                    style=me.Style(
                        flex_grow=1,
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    on_click=reload_welcome,
                ):
                    me.text(
                        app_state.welcome_message,
                        style=me.Style(
                            width="80vw",
                            font_size="12pt",
                            font_style="italic",
                            color="gray",
                        ),
                    )

                me.box(style=me.Style(height="16px"))

                with me.box(
                    style=me.Style(
                        margin=me.Margin(left="auto", right="auto"),
                        width="min(1024px, 100%)",
                        gap="24px",
                        flex_grow=1,
                        display="flex",
                        flex_wrap="wrap",
                        flex_direction="column",
                        align_items="center",
                    )
                ):
                    # Prompt
                    with me.box(
                        style=me.Style(
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                            width="85%",
                        )
                    ):
                        me.text(
                            "Select the output you prefer for the given prompt",
                            style=me.Style(font_weight=500, font_size="20px", text_transform="uppercase"),
                        )
                        me.box(style=me.Style(height=16))
                        me.text(page_state.arena_prompt, style=me.Style(font_size="20pt"))

                    # Image outputs
                    with me.box(style=_BOX_STYLE):
                        if page_state.is_loading:
                            with me.box(
                                style=me.Style(
                                    display="grid",
                                    justify_content="center",
                                    justify_items="center",
                                )
                            ):
                                me.progress_spinner()
                        if len(page_state.arena_output) != 0:
                            with me.box(
                                style=me.Style(
                                    display="grid",
                                    justify_content="center",
                                    justify_items="center",
                                )
                            ):
                                # Generated images row
                                with me.box(
                                    style=me.Style(
                                        flex_wrap="wrap", display="flex", gap="15px"
                                    )
                                ):
                                    for idx, img in enumerate(page_state.arena_output, start=1):
                                        print(f"===> idx: {idx}, img: {img}")
                                        model_name = f"arena_model{idx}"
                                        model_value = getattr(page_state, model_name)

                                        replace_url = "https://storage.mtls.cloud.google.com/"
                                        if Default.PUBLIC_BUCKET:
                                            replace_url = "https://storage.googleapis.com/"
                                        img_url = img.replace(
                                            "gs://",
                                            replace_url
                                        )
                                        with me.box(
                                            style=me.Style(align_items="center", justify_content="center", display="flex", flex_direction="column"),
                                        ):
                                            image_border_style = me.Style(
                                                width="450px",
                                                margin=me.Margin(top=10),
                                                border_radius="35px",
                                            )
                                            if page_state.chosen_model:
                                                if page_state.chosen_model == model_value:
                                                    # green border
                                                    image_border_style = me.Style(
                                                        width="450px",
                                                        margin=me.Margin(top=10),
                                                        border_radius="35px",
                                                        border=me.Border().all(me.BorderSide(color="green", style="inset", width="5px"))
                                                    )
                                                else:
                                                    # opaque
                                                    image_border_style = me.Style(
                                                        width="450px",
                                                        margin=me.Margin(top=10),
                                                        border_radius="35px",
                                                        opacity=0.5,
                                                    )
                                            me.image(
                                                src=f"{img_url}",
                                                style=image_border_style,
                                            )
                                            
                                            if page_state.chosen_model:
                                                text_style = me.Style()
                                                if page_state.chosen_model == model_value:
                                                    text_style = me.Style(font_weight="bold")
                                                me.text(model_value, style=text_style)
                                            else:
                                                me.box(style=me.Style(height=18))

                                me.box(style=me.Style(height=15))

                                if len(page_state.arena_output) != 2:
                                    disabled_choice = True
                                else:
                                    disabled_choice = False

                                with me.box(
                                    style=me.Style(
                                        flex_direction="row",
                                        display="flex",
                                        gap=50,
                                    )
                                ):
                                    # left choice button
                                    with me.content_button(
                                        type="flat",
                                        key="arena_model1",
                                        on_click=on_click_arena_vote,
                                        disabled=disabled_choice,
                                    ):
                                        with me.box(
                                            style=me.Style(
                                                display="flex", align_items="center"
                                            )
                                        ):
                                            me.icon("arrow_left")
                                            me.text("left")
                                    # skip button
                                    me.button(
                                        label="skip",
                                        type="stroked",
                                        on_click=on_click_reload_arena,
                                    )
                                    # right choice button
                                    with me.content_button(
                                        type="flat",
                                        key="arena_model2",
                                        on_click=on_click_arena_vote,
                                        disabled=disabled_choice,
                                    ):
                                        with me.box(
                                            style=me.Style(
                                                display="flex", align_items="center"
                                            )
                                        ):
                                            me.text("right")
                                            me.icon("arrow_right")
                        else:
                            # skip button
                            me.button(
                                label="skip",
                                type="stroked",
                                on_click=on_click_reload_arena,
                            )
                    # show user choice
                    if page_state.chosen_model:
                        me.text(f"You voted {page_state.chosen_model}")


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
