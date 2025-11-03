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

import json
import random
from dataclasses import field
from pathlib import Path

import mesop as me
import mesop.labs as mel

from common.metadata import add_media_item
from common.utils import gcs_uri_to_https_url
from components.dialog import dialog
from components.header import header
from components.page_scaffold import on_theme_load
from components.theme_manager.theme_manager import theme_manager
from models.image_models import generate_virtual_models
from models.virtual_model_generator import DEFAULT_PROMPT, VirtualModelGenerator
from state.state import AppState


@me.stateclass
class PageState:
    base_prompt: str = DEFAULT_PROMPT
    selected_gender_name: str = "Feminine-presenting"
    selected_silhouette_name: str = "Linear & Balanced"
    selected_mst: str = "MST-5"
    selected_mst_orb_url: str = (
        "https://google-ai-skin-tone-research.imgix.net/orbs/monk-05.png"
    )
    generated_images: list[list[str]] = field(default_factory=list)  # pylint: disable=invalid-field-call
    generated_description: str = ""
    loading: bool = False
    save_to_library: bool = False
    show_info_dialog: bool = False

    # Load options once
    _options: dict = field(default_factory=dict, init=False)  # pylint: disable=invalid-field-call

    def __post_init__(self):
        config_path = Path(__file__).parent.parent / "config/virtual_model_options.json"
        with open(config_path, "r") as f:
            self._options = json.load(f)


@me.page(
    path="/test_vto_prompt_generator",
    title="VTO Model Composite Card Generator Test Page",
    security_policy=me.SecurityPolicy(dangerously_disable_trusted_types=True),
)
def page():
    state = me.state(PageState)

    if state.show_info_dialog:
        with dialog(is_open=state.show_info_dialog):  # pylint: disable=not-context-manager
            with me.box(
                style=me.Style(
                    display="flex",
                    justify_content="space-between",
                    align_items="center",
                    margin=me.Margin(bottom=16),
                )
            ):
                me.text("About The Virtual Model Generator", type="headline-6")
                with me.box(
                    on_click=on_close_info_dialog, style=me.Style(cursor="pointer")
                ):
                    me.icon("close")
            me.markdown(
                text="""This tool helps create more inclusive and representative virtual models by incorporating the Monk Skin Tone Scale, a 10-point scale designed to be more representative of a wider range of skin tones. By allowing you to select a specific skin tone, we can generate models that more accurately reflect the diversity of your users. You can learn more about the Monk Skin Tone Scale and its recommended practices [here](https://skintone.google/recommended-practices).

Describing silhouette presets is essential because it transforms abstract shapes into understandable and accessible starting points for creativity. By using neutral, geometric language—such as 'a linear form with a subtle waist'—you educate users and give them the vocabulary to make informed choices. This approach showcases the generator's commitment to diversity from the very beginning, ensuring that every body type is presented as a valid, beautiful foundation for design rather than a 'default' or a 'deviation.' It helps users find what they're looking for quickly and reinforces the positive, inclusive ethos of the tool.

It is crucial to describe gender based on presentation rather than identity because a virtual model has an appearance, not a personal identity. Using terms like 'feminine-presenting,' 'masculine-presenting,' or 'androgynous' is a precise and respectful way to describe the visual characteristics of the model you've generated. This practice avoids making assumptions and is inclusive of transgender and non-binary individuals, who know that external appearance is distinct from one's internal sense of self. This careful choice of words ensures the generator is a safe and welcoming tool for all users, accurately describing what is on the screen without mislabeling or imposing a false identity.""",
            )

    with me.box(style=me.Style(padding=me.Padding.all(20))):
        header(
            title="Virtual Model Composite Card Generator Matrix",
            icon="style",
            show_info_button=True,
            on_info_click=lambda e: on_show_info_dialog(e),
        )

        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=20,
                margin=me.Margin(bottom=20),
                align_items="flex-start",
            )
        ):
             me.markdown(
                text="""This tool helps create more inclusive and representative virtual models by incorporating the Monk Skin Tone Scale, a 10-point scale designed to be more representative of a wider range of skin tones. By allowing you to select a specific skin tone, we can generate models that more accurately reflect the diversity of your users. You can learn more about the Monk Skin Tone Scale and its recommended practices [here](https://skintone.google/recommended-practices).""")

        # --- CONTROLS ---
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=20,
                margin=me.Margin(bottom=20),
                align_items="flex-start",
            )
        ):
            with me.box(style=me.Style(flex_grow=1)):
                me.textarea(
                    label="Base Prompt",
                    value=state.base_prompt,
                    on_input=on_base_prompt_input,
                    rows=5,
                    style=me.Style(width="100%"),
                )
            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=10)
            ):
                me.select(
                    label="Gender Presentation",
                    options=[
                        me.SelectOption(label=g["name"], value=g["name"])
                        for g in state._options.get("genders", [])
                    ],
                    value=state.selected_gender_name,
                    on_selection_change=on_gender_select,
                )
            with me.box(
                style=me.Style(display="flex", flex_direction="column", gap=10)
            ):
                me.select(
                    label="Monk Skin Tone",
                    options=[
                        me.SelectOption(
                            label=f"{mst['name']} ({mst['hex']})", value=mst["name"]
                        )
                        for mst in state._options.get("MST", [])
                    ],
                    value=state.selected_mst,
                    on_selection_change=on_mst_select,
                )
                if state.selected_mst_orb_url:
                    with me.box(
                        style=me.Style(display="flex", justify_content="center")
                    ):
                        me.image(
                            src=state.selected_mst_orb_url,
                            style=me.Style(width=50, height=50),
                        )

        # --- SILHOUETTE PRESETS ---
        me.text(
            "Select a Silhouette Preset",
            type="headline-6",
            style=me.Style(margin=me.Margin(bottom=10)),
        )
        with me.box(
            style=me.Style(
                display="grid",
                grid_template_columns="repeat(auto-fill, minmax(250px, 1fr))",
                gap=15,
            )
        ):
            for preset in state._options.get("silhouette_presets", []):
                with me.box(
                    key=preset["name"],
                    on_click=on_select_silhouette,
                    style=me.Style(
                        border=me.Border.all(
                            me.BorderSide(
                                width=2,
                                style="solid",
                                color=me.theme_var("primary")
                                if state.selected_silhouette_name == preset["name"]
                                else me.theme_var("outline"),
                            )
                        ),
                        background=me.theme_var("primary-container")
                        if state.selected_silhouette_name == preset["name"]
                        else "transparent",
                        padding=me.Padding.all(15),
                        border_radius=12,
                        cursor="pointer",
                    ),
                ):
                    me.text(preset["name"], type="subtitle-1")
                    me.text(preset["description"], type="body-2")

        with me.box(
            style=me.Style(
                display="flex", gap=10, margin=me.Margin(top=20), align_items="center"
            )
        ):
            me.button(
                "Generate Matrix", on_click=on_click_generate_matrix, type="raised"
            )
            me.button("I'm Feeling Lucky", on_click=on_click_randomize, type="flat")
            me.button(
                "Generate Description",
                on_click=on_click_generate_description,
                type="flat",
                disabled=not state.generated_images,
            )
            me.checkbox(
                label="Save to Library",
                on_change=on_save_to_library_change,
                checked=state.save_to_library,
            )

        # --- GENERATED DESCRIPTION ---
        if state.generated_description:
            with me.box(
                style=me.Style(
                    margin=me.Margin(top=20),
                    background=me.theme_var("surface-container-lowest"),
                    padding=me.Padding.all(15),
                    border_radius=8,
                )
            ):
                me.text("Generated Description", type="subtitle-2")
                me.text(state.generated_description)

        # --- IMAGE MATRIX ---
        if state.loading:
            me.progress_spinner()
        elif state.generated_images:
            me.text(
                "Generated Models",
                type="headline-6",
                style=me.Style(margin=me.Margin(top=20, bottom=10)),
            )
            with me.box(
                style=me.Style(
                    display="grid", grid_template_columns="repeat(3, 1fr)", gap=10
                )
            ):
                for image_row in state.generated_images:
                    for image_url in image_row:
                        me.image(
                            src=gcs_uri_to_https_url(image_url),
                            style=me.Style(width="100%"),
                        )


def on_show_info_dialog(e: me.ClickEvent):
    me.state(PageState).show_info_dialog = True
    yield


def on_close_info_dialog(e: me.ClickEvent):
    me.state(PageState).show_info_dialog = False
    yield


def on_base_prompt_input(e: me.InputEvent):
    me.state(PageState).base_prompt = e.value


def on_gender_select(e: me.SelectSelectionChangeEvent):
    me.state(PageState).selected_gender_name = e.value


def on_select_silhouette(e: me.ClickEvent):
    me.state(PageState).selected_silhouette_name = e.key


def on_mst_select(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.selected_mst = e.value
    # MST-1 -> 01, MST-10 -> 10
    mst_number = e.value.split("-")[-1].zfill(2)
    state.selected_mst_orb_url = (
        f"https://google-ai-skin-tone-research.imgix.net/orbs/monk-{mst_number}.png"
    )


def on_click_randomize(e: me.ClickEvent):
    state = me.state(PageState)
    state.selected_gender_name = random.choice(state._options.get("genders", []))[
        "name"
    ]
    state.selected_silhouette_name = random.choice(
        state._options.get("silhouette_presets", [])
    )["name"]
    selected_mst_obj = random.choice(state._options.get("MST", []))
    state.selected_mst = selected_mst_obj["name"]
    mst_number = selected_mst_obj["name"].split("-")[-1].zfill(2)
    state.selected_mst_orb_url = (
        f"https://google-ai-skin-tone-research.imgix.net/orbs/monk-{mst_number}.png"
    )
    yield


def on_click_generate_matrix(e: me.ClickEvent):
    state = me.state(PageState)
    state.loading = True
    state.generated_images = []
    state.generated_description = ""
    yield

    # Find the selected gender and silhouette objects to get their prompt_fragments
    selected_gender_obj = next(
        (
            g
            for g in state._options["genders"]
            if g["name"] == state.selected_gender_name
        ),
        None,
    )
    selected_silhouette_obj = next(
        (
            s
            for s in state._options["silhouette_presets"]
            if s["name"] == state.selected_silhouette_name
        ),
        None,
    )
    selected_mst_obj = next(
        (m for m in state._options["MST"] if m["name"] == state.selected_mst), None
    )

    if not selected_gender_obj or not selected_silhouette_obj or not selected_mst_obj:
        print("Error: Could not find selected gender or silhouette.")
        state.loading = False
        yield
        return

    matrix = []
    for variant in state._options.get("variants", []):
        generator = VirtualModelGenerator(state.base_prompt)
        generator.set_value("gender", selected_gender_obj["prompt_fragment"])
        generator.set_value("silhouette", selected_silhouette_obj["prompt_fragment"])
        generator.set_value("MST", selected_mst_obj["prompt_fragment"])
        generator.set_value("variant", variant["prompt_fragment"])

        prompt = generator.build_prompt()
        print(f"Generating images for prompt: {prompt}")
        image_urls = generate_virtual_models(prompt=prompt, num_images=3)
        matrix.append(image_urls)

        if state.save_to_library:
            add_media_item(
                user_email=me.state(AppState).user_email,
                model="imagen-4.0-generate-preview-06-06",
                mime_type="image/png",
                gcs_uris=image_urls,
                prompt=prompt,
            )

    state.generated_images = matrix
    state.loading = False
    yield


def on_click_generate_description(e: me.ClickEvent):
    state = me.state(PageState)

    selected_gender_obj = next(
        (
            g
            for g in state._options["genders"]
            if g["name"] == state.selected_gender_name
        ),
        {},
    )
    selected_silhouette_obj = next(
        (
            s
            for s in state._options["silhouette_presets"]
            if s["name"] == state.selected_silhouette_name
        ),
        {},
    )

    description = (
        f"A {selected_gender_obj.get('name', 'person')} with an {state.selected_mst} complexion. "
        f"The model has a {selected_silhouette_obj.get('name', 'defined')} silhouette: {selected_silhouette_obj.get('description', '')}"
    )
    state.generated_description = description
    yield


def on_save_to_library_change(e: me.CheckboxChangeEvent):
    me.state(PageState).save_to_library = e.checked
    yield
