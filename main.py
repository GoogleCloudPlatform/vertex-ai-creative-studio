import os

import mesop as me

from svg_icon.svg_icon_component import (
    svg_icon_component,
)

from prompts.critics import (
    REWRITER_PROMPT,
    MAGAZINE_EDITOR_PROMPT,
)

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, TypedDict, Any, cast

import json
import random

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    Part,
)
from google.cloud.aiplatform import telemetry


title = "CREATIVE STUDIO"

PROJECT_ID = os.environ.get('PROJECT_ID')
LOCATION = "us-central1"
multimodal_model_name = "gemini-1.5-flash"

vertexai.init(project=PROJECT_ID, location=LOCATION)

with telemetry.tool_context_manager('creative-studio'):
    model = GenerativeModel(model_name=multimodal_model_name)

imagen2 = "imagegeneration@006"
imagen_nano = "imagegeneration@004"
imagen3_fast = "imagen-3.0-fast-generate-preview-0611"
imagen3 = "imagen-3.0-generate-preview-0611"
imagen3_model_name = imagen2
imagen3_generation_model = ImageGenerationModel.from_pretrained(imagen3)
image_generation_model = ImageGenerationModel.from_pretrained(imagen2)

# set this if you want to use templates; you must update to publicly accessible image source
template_portrait_base_url = ""
#template_portrait_base_url = "https://storage.googleapis.com/creative-studio-867-static-assets/"
image_creation_bucket = "gs://creative-studio-867-static-assets/temporary-generations/"
#image_creation_bucket = "gs://ghchinoy-genai-sa-assets/creative-studio-temp/"

class ImageModel(TypedDict):
    display: str
    model_name: str

image_models_json = [
    {"display": "Imagen 3 Fast", "model": "imagen-3.0-fast-generate-preview-0611"},
    {"display": "Imagen 3", "model": "imagen-3.0-generate-preview-0611"}
]


@dataclass_json
@me.stateclass
class State:
    is_loading: bool = False
    show_templates: bool = False
    show_advanced: bool = False

    # imagen
    image_models: list[ImageModel] = field(default_factory=lambda:image_models_json)
    image_model_name: str = "imagen-3.0-fast-generate-preview-0611"
    image_prompt_input: str
    image_prompt_placeholder: str
    image_textarea_key: int
    
    image_aspect_ratio: str = "1:1"
    image_negative_prompt_input: str = ""
    image_negative_prompt_placeholder: str = ""
    image_negative_prompt_key: int
    
    image_content_type: str = "Photo"
    image_color_tone: str = "Cool tone"
    image_lighting: str = "Golden hour"
    image_composition: str = "Wide angle"
    
    image_output: list[str] = field(default_factory=lambda:[])
    image_commentary: str


image_modifiers = ["aspect_ratio", "content_type", "color_tone", "lighting", "composition"]


def on_image_input(e: me.InputEvent):
    state = me.state(State)
    state.image_prompt_input = e.value

def on_blur_image_prompt(e: me.InputBlurEvent):
    me.state(State).image_prompt_input = e.value

def on_blur_image_negative_prompt(e: me.InputBlurEvent):
    me.state(State).image_negative_prompt_input = e.value

def on_click_generate_images(e: me.ClickEvent):
    state = me.state(State)
    state.is_loading = True
    state.image_output.clear()
    yield
    generate_images(state.image_prompt_input)
    generateCompliment(state.image_prompt_input)
    state.is_loading = False
    yield
    

def generate_images(input: str):
    state = me.state(State)
    if input == "": # handle condition where someone hits "random" but doens't modify
        if state.image_prompt_placeholder != "":
            input = state.image_prompt_placeholder
    state.image_output.clear()
    modifiers = []
    for mod in image_modifiers:
        if mod != "aspect_ratio":
            if getattr(state, f"image_{mod}") != "None":
                modifiers.append(getattr(state, f"image_{mod}"))
    prompt_modifiers = ", ".join(modifiers)
    prompt = f"{input} {prompt_modifiers}"
    print(f"prompt: {prompt}")
    if state.image_negative_prompt_input:
        print(f"negative prompt: {state.image_negative_prompt_input}")
    print(f"model: {state.image_model_name}")
    imagen3_generation_model = ImageGenerationModel.from_pretrained(state.image_model_name)
    response = imagen3_generation_model.generate_images(
        prompt=prompt,
        add_watermark=True,
        aspect_ratio=getattr(state, "image_aspect_ratio"),
        number_of_images=3,
        output_gcs_uri=image_creation_bucket,
        language="auto",
        negative_prompt=state.image_negative_prompt_input
    )
    for idx, img in enumerate(response.images):
        print(f"generated image: {idx} len {len(img._as_base64_string())} at {img._gcs_uri}")
        #output = img._as_base64_string()
        #state.image_output.append(output)
        state.image_output.append(img._gcs_uri)
        

def random_prompt(e: me.ClickEvent):
    state = me.state(State)
    with open('imagen_prompts.json', 'r') as file:
        data = file.read()
    prompts = json.loads(data)
    random_prompt = random.choice(prompts["imagen"])
    state.image_prompt_placeholder = random_prompt
    on_image_input(me.InputEvent(key=str(state.image_textarea_key), value=random_prompt))
    print(f"preset chosen: {random_prompt}")
    yield


# advanced controls
def on_click_advanced_controls(e: me.ClickEvent):
    me.state(State).show_advanced = not me.state(State).show_advanced


# fun templates
all_templates = []
templates = []

if template_portrait_base_url:
    with open('./templates/templates.json', 'r') as file:
        data = file.read()
        tmpls = json.loads(data)
        for tmpl in tmpls["templates"]:
            all_templates.append(tmpl)
        templates = random.sample(all_templates,5) 

def on_click_show_templates(e: me.ClickEvent):
    state = me.state(State)
    shuffle_templates()
    state.show_templates = not state.show_templates
    
def on_click_choose_template(e: me.ClickEvent):
    state = me.state(State)
    tmpl = next(item for item in all_templates if item["name"] == e.key)
    template = tmpl.get('template')    
    state.image_prompt_placeholder = template
    on_image_input(me.InputEvent(key=str(state.image_textarea_key), value=template))
    state.show_templates = not state.show_templates
    yield

def on_click_shuffle_templates(e: me.ClickEvent):
    shuffle_templates()

def shuffle_templates():
    print(templates)
    templates = random.sample(all_templates,5)
    for t in templates:
        print(t["name"])
    yield


def on_click_clear_images(e: me.ClickEvent):
    state = me.state(State)
    state.image_prompt_input = ""
    state.image_prompt_placeholder = ""
    state.image_output.clear()
    state.image_negative_prompt_input = ""
    state.image_textarea_key += 1
    state.image_negative_prompt_key += 1
    

def on_selection_change_image(e: me.SelectSelectionChangeEvent):
    state = me.state(State)
    print(f"changed: {e.key}={e.value}")
    setattr(state, f"image_{e.key}", e.value)


def on_click_rewrite_prompt(e: me.ClickEvent):
    state = me.state(State)
    rewritten = rewrite_prompt(state.image_prompt_input)
    state.image_prompt_input = rewritten
    state.image_prompt_placeholder = rewritten
    #state.image_textarea_key += 1


def rewrite_prompt(original_prompt: str):
    """
    Outputs a rewritten prompt

    Args:
        original_prompt (str): artists's original prompt
    """
    #state = me.state(State)
    with telemetry.tool_context_manager('creative-studio'):
        model = GenerativeModel(multimodal_model_name)
    config = GenerationConfig(temperature=0.8, max_output_tokens=2048)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    response = model.generate_content(
        REWRITER_PROMPT.format(original_prompt), 
        generation_config=config,
        safety_settings=safety_settings,
        )
    print(f"asked to rewrite: '{original_prompt}")
    print(f"rewritten as: {response.text}")
    return response.text
    

def generateCompliment(generation_instruction: str):
    """
    Outputs a Gemini generated comment about images
    """
    state = me.state(State)
    with telemetry.tool_context_manager('creative-studio'):
        model = GenerativeModel(multimodal_model_name)
    config = GenerationConfig(temperature=0.8, max_output_tokens=2048)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    prompt_parts = []
    for idx, img in enumerate(state.image_output):
        # not bytes
        #prompt_parts.append(Part.from_data(data=img, mime_type="image/png"))
        # now gcs uri
        prompt_parts.append(f"""image {idx}
""")
        prompt_parts.append(Part.from_uri(uri=img,mime_type="image/png"))
    prompt_parts.append(MAGAZINE_EDITOR_PROMPT.format(generation_instruction))
    
    response = model.generate_content(
        prompt_parts, 
        generation_config=config,
        safety_settings=safety_settings,
        )
    state.image_commentary = response.text



@me.page(
    path="/",
    security_policy=me.SecurityPolicy(
        allowed_script_srcs	    = ["https://cdn.jsdelivr.net"],
        allowed_connect_srcs	= ["https://cdn.jsdelivr.net"],
        dangerously_disable_trusted_types=True),
    title="Creative Studio | Vertex AI Gemini",
)
def app():
    state = me.state(State)
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
        ),
    ):
        with me.box(
            style=me.Style(
                background="#f0f4f8",
                height="100%",
                overflow_y="scroll",
                margin=me.Margin(bottom=20),
            )
        ):
            with me.box(
                style=me.Style(
                    background="#f0f4f8",
                    padding=me.Padding(top=24, left=24, right=24, bottom=24),
                    display="flex",
                    flex_direction="column",
                )
            ):
                with me.box(
                    style=me.Style(
                        display="flex", 
                        justify_content="space-between",
                    )
                ):
                    with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
                        me.icon(icon="auto_fix_high")
                        me.text(title, type="headline-5", style=me.Style(font_family="Google Sans"))
                    image_model_options = []
                    for c in state.image_models:
                        image_model_options.append(me.SelectOption(label=c.get("display"), value=c.get("model")))
                    me.select(
                        label="Imagen version",
                        options=image_model_options,
                        key="model_name",
                        on_selection_change=on_selection_change_image,
                        value=state.image_model_name,
                    )
                    
                # Prompt
                with me.box(
                    style=me.Style(
                        margin=me.Margin(left="auto", right="auto"),
                        width="min(1024px, 100%)",
                        gap="24px",
                        flex_grow=1,
                        display="flex",
                        flex_wrap="wrap",
                        flex_direction="column",
                    )
                ):
                    with me.box(style=_BOX_STYLE):
                        me.text("Prompt for image generation", style=me.Style(font_weight=500))
                        me.box(style=me.Style(height=16))
                        me.textarea(
                            key=str(state.image_textarea_key),
                            #on_input=on_image_input,
                            on_blur=on_blur_image_prompt,
                            rows=3,
                            autosize=True,
                            max_rows=10,
                            style=me.Style(width="100%"),
                            value=state.image_prompt_placeholder
                        )
                        # Prompt buttons
                        me.box(style=me.Style(height=12))
                        with me.box(
                            style=me.Style(display="flex", justify_content="space-between")
                        ):
                            me.button(
                                "Clear",
                                color="primary",
                                type="stroked",
                                on_click=on_click_clear_images,
                            )
                            if templates:
                                me.button(
                                    "Templates",
                                    color="primary",
                                    type="stroked",
                                    on_click=on_click_show_templates,
                                    style=me.Style(color="#1A73E8")
                                )
                            me.button(
                                "Random",
                                color="primary",
                                type="stroked",
                                on_click=random_prompt,
                                style=me.Style(color="#1A73E8"),
                            )
                            # prompt rewriter
                            #disabled = not state.image_prompt_input if not state.image_prompt_input else False
                            with me.content_button(
                                on_click=on_click_rewrite_prompt, 
                                type="stroked",
                                #disabled=disabled,
                            ):
                                with me.tooltip(message="rewrite prompt with Gemini"):
                                    with me.box(
                                        style=me.Style(
                                            display="flex", 
                                            gap=2, 
                                            align_items="center",
                                        )
                                    ):
                                        me.icon("auto_awesome")
                                        me.text("Rewriter")
                            # generate
                            me.button(
                                "Generate",
                                color="primary",
                                type="flat",
                                on_click=on_click_generate_images,
                            )

                    # Modifiers or Templates
                    if state.show_templates == True:
                        # Templates
                        with me.box(style=_BOX_STYLE_ROW):
                            with me.box(
                                style=me.Style(
                                    flex_direction="row", 
                                    display="flex",
                                )
                            ):
                                with me.box(
                                    style=me.Style(
                                        flex_direction="column", 
                                        display="flex", 
                                        padding=me.Padding(top=-5),
                                    )
                                ):
                                    # clickable cancel icon button
                                    with me.content_button(on_click=on_click_show_templates):
                                        with me.tooltip(message="hide templates"):
                                            with me.box(style=me.Style(display="flex")):
                                                me.icon("cancel")
                                    with me.content_button(on_click=on_click_shuffle_templates):
                                        with me.tooltip(message="random"):
                                            with me.box(style=me.Style(display="flex")):
                                                me.icon("shuffle")      
                            with me.box(style=me.Style(
                                display="flex", 
                                flex_wrap="wrap", gap=2, 
                                width="100%",height="80px")):
                                    for tmpl in templates:
                                        tmpl_name = tmpl.get('name')
                                        url = f"{template_portrait_base_url}{tmpl.get('preview')}"
                                        with me.content_button(on_click=on_click_choose_template, key=f"{tmpl_name}"):
                                            with me.tooltip(message=f"{tmpl_name}"):
                                                with me.box(style=_BOX_STYLE_TEMPLATE):
                                                    me.image(
                                                        alt=f"{tmpl_name}",
                                                        src=f"{url}", 
                                                        style=me.Style(width="50px")
                                                    )
                                                    me.text(tmpl_name)
                    
                    else:
                        # Modifiers
                        with me.box(style=_BOX_STYLE):            
                            with me.box(
                                style=me.Style(
                                    display="flex", 
                                    justify_content="space-between", 
                                    gap=2, 
                                    width="100%",
                                )
                            ):
                                if state.show_advanced:
                                    with me.content_button(on_click=on_click_advanced_controls):
                                        with me.tooltip(message="hide advanced controls"):
                                            with me.box(style=me.Style(display="flex")):
                                                me.icon("expand_less")
                                else:
                                    with me.content_button(on_click=on_click_advanced_controls):
                                        with me.tooltip(message="show advanced controls"):
                                            with me.box(style=me.Style(display="flex")):
                                                me.icon("expand_more")
                                            
                                # Default Modifiers
                                me.select(
                                    label="Aspect Ratio",
                                    options=[
                                        me.SelectOption(label="1:1", value="1:1"),
                                        me.SelectOption(label="3:4", value="3:4"),
                                        me.SelectOption(label="4:3", value="4:3"),
                                        me.SelectOption(label="16:9", value="16:9"),
                                        me.SelectOption(label="9:16", value="9:16"),
                                    ],
                                    key="aspect_ratio",
                                    on_selection_change=on_selection_change_image,
                                    style=me.Style(width="160px"),
                                    value=state.image_aspect_ratio,
                                )
                                me.select(
                                    label="Content Type",
                                    options=[
                                        me.SelectOption(label="None", value="None"),
                                        me.SelectOption(label="Photo", value="Photo"),
                                        me.SelectOption(label="Art", value="Art"), 
                                    ],
                                    key="content_type",
                                    on_selection_change=on_selection_change_image,
                                    style=me.Style(width="160px"),
                                    value=state.image_content_type
                                )
                                
                                color_and_tone_options = []
                                for c in ["None", "Black and white", "Cool tone", "Golden", "Monochromatic", "Muted color", "Pastel color", "Toned image"]:
                                        color_and_tone_options.append(me.SelectOption(label=c, value=c))
                                me.select(
                                    label="Color & Tone",
                                    options=color_and_tone_options,
                                    key="color_tone",
                                    on_selection_change=on_selection_change_image,
                                    style=me.Style(width="160px"),
                                    value=state.image_color_tone
                                )
                                
                                lighting_options = []
                                for l in ["None", "Backlighting", "Dramatic light", "Golden hour", "Long-time exposure", "Low lighting", "Multiexposure", "Studio light", "Surreal lighting"]:
                                    lighting_options.append(me.SelectOption(label=l, value=l))
                                me.select(
                                    label="Lighting",
                                    options=lighting_options,
                                    key="lighting",
                                    on_selection_change=on_selection_change_image,
                                    value=state.image_lighting
                                )
                                
                                composition_options = []
                                for c in ["None", "Closeup", "Knolling", "Landscape photography", "Photographed through window", "Shallow depth of field", "Shot from above", "Shot from below", "Surface detail", "Wide angle"]:
                                    composition_options.append(me.SelectOption(label=c, value=c))
                                me.select(
                                    label="Composition",
                                    options=composition_options,
                                    key="composition",
                                    on_selection_change=on_selection_change_image,
                                    value=state.image_composition
                                )

                            # Advanced controls
                            # negative prompt
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_direction="row",
                                )
                            ):
                                if state.show_advanced:
                                    me.box(style=me.Style(width=67))
                                    me.input(
                                        label="negative phrases",
                                        on_blur=on_blur_image_negative_prompt,
                                        value=state.image_negative_prompt_placeholder,
                                        key=str(state.image_negative_prompt_key),
                                        style=me.Style(
                                            width="350px",
                                        )
                                    )


                    # Image output
                    with me.box(style=_BOX_STYLE):
                        me.text("Output", style=me.Style(font_weight=500))
                        if state.is_loading:
                            with me.box(
                                style=me.Style(
                                    display="grid",
                                    justify_content="center",
                                    justify_items="center",
                                )):
                                me.progress_spinner()
                        if len(state.image_output) != 0:
                            with me.box(
                                style=me.Style(
                                    display="grid",
                                    justify_content="center",
                                    justify_items="center",
                                )
                            ):
                                # Generated images row
                                with me.box(style=me.Style(flex_wrap="wrap", display="flex", gap="15px")):
                                    for idx, img in enumerate(state.image_output):
                                        #print(f"{idx}: {len(img)}")
                                        img_url = img.replace("gs://","https://storage.mtls.cloud.google.com/")
                                        me.image(
                                            #src=f"data:image/png;base64,{img}",
                                            src=f"{img_url}",
                                            style=me.Style(
                                                width="300px", margin=me.Margin(top=10),
                                                border_radius="35px",
                                            ),
                                        )
                                
                                # Image commentary
                                #with me.box(style=me.Style(flex_wrap="wrap", display="flex", #flex_direction="row", width="85%", padding=me.Padding.all(10))):
                                #    me.icon("assistant")
                                #    me.text("magazine editor")                                    
                                #    me.text(state.image_commentary)
                                
                                # SynthID notice
                                with me.box(style=me.Style(display="flex", flex_direction="row", align_items="center")):
                                    svg_icon_component(svg="""<svg data-icon-name="digitalWatermarkIcon" viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true" sandboxuid="2"><path fill="#3367D6" d="M12 22c-.117 0-.233-.008-.35-.025-.1-.033-.2-.075-.3-.125-2.467-1.267-4.308-2.833-5.525-4.7C4.608 15.267 4 12.983 4 10.3V6.2c0-.433.117-.825.35-1.175.25-.35.575-.592.975-.725l6-2.15a7.7 7.7 0 00.325-.1c.117-.033.233-.05.35-.05.15 0 .375.05.675.15l6 2.15c.4.133.717.375.95.725.25.333.375.717.375 1.15V10.3c0 2.683-.625 4.967-1.875 6.85-1.233 1.883-3.067 3.45-5.5 4.7-.1.05-.2.092-.3.125-.1.017-.208.025-.325.025zm0-2.075c2.017-1.1 3.517-2.417 4.5-3.95 1-1.55 1.5-3.442 1.5-5.675V6.175l-6-2.15-6 2.15V10.3c0 2.233.492 4.125 1.475 5.675 1 1.55 2.508 2.867 4.525 3.95z" sandboxuid="2"></path><path fill="#3367D6" d="M12 16.275c0-.68-.127-1.314-.383-1.901a4.815 4.815 0 00-1.059-1.557 4.813 4.813 0 00-1.557-1.06 4.716 4.716 0 00-1.9-.382c.68 0 1.313-.128 1.9-.383a4.916 4.916 0 002.616-2.616A4.776 4.776 0 0012 6.475c0 .672.128 1.306.383 1.901a5.07 5.07 0 001.046 1.57 5.07 5.07 0 001.57 1.046 4.776 4.776 0 001.901.383c-.672 0-1.306.128-1.901.383a4.916 4.916 0 00-2.616 2.616A4.716 4.716 0 0012 16.275z" sandboxuid="2"></path></svg>""")

                                    me.text(text="images watermarked by SynthID",
                                        style=me.Style(
                                            padding=me.Padding.all(10),
                                            font_size="0.95em"
                                        ))
                        else:
                            if state.is_loading:
                                me.text(text="generating images!",
                                    style=me.Style(display="grid",justify_content="center", padding=me.Padding.all(20)))
                            else:
                                me.text(text="generate some images!", 
                                    style=me.Style(display="grid",justify_content="center", padding=me.Padding.all(20)))

                    # Image commentary
                    if len(state.image_output) != 0:
                        with me.box(style=_BOX_STYLE):                        
                            with me.box(style=me.Style(display="flex", justify_content="space-between", gap=2, width="100%")):
                                with me.box(style=me.Style(flex_wrap="wrap", display="flex", flex_direction="row", 
                                #width="85%", 
                                padding=me.Padding.all(10))):
                                    me.icon("assistant")
                                    me.text("magazine editor", style=me.Style(font_weight=500))                                    
                                    me.text(state.image_commentary, style=me.Style(padding=me.Padding.all(15)))
            
        footer()                             

def footer():
    with me.box(
        style=me.Style(
            #height="18px",
            padding=me.Padding(left=20, right=20, top=10, bottom=14),
            border=me.Border(
                top=me.BorderSide(width=1, style="solid", color="$ececf1")
            ),
            display="flex", 
            justify_content="space-between",
            flex_direction="row",
            color="rgb(68, 71, 70)",
            letter_spacing="0.1px",
            line_height="14px",
            font_size=14,
            font_family="Google Sans",
        )
    ):
        me.html(
            "<a href='https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview' target='_blank'>Imagen</a>",
        )
        me.html(
            "<a href='https://cloud.google.com/vertex-ai/generative-ai/docs/image/img-gen-prompt-guide' target='_blank'>Imagen Prompting Guide</a>"
        )
        me.html(
            "<a href='https://cloud.google.com/vertex-ai/generative-ai/docs/image/responsible-ai-imagen' target='_blank'>Imagen Responsible AI</a>"
        )


_BOX_STYLE = me.Style(
    flex_basis="max(480px, calc(50% - 48px))",
    background="#fff",
    border_radius=12,
    box_shadow=(
        "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
    ),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
)

_BOX_STYLE_ROW = me.Style(
    flex_basis="max(480px, calc(50% - 48px))",
    background="#fff",
    border_radius=12,
    box_shadow=(
        "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
    ),
    padding=me.Padding(top=12, left=12, right=12, bottom=12),
    display="flex",
    flex_direction="row",
)

_BOX_STYLE_TEMPLATE = me.Style(
    flex_basis="max(480px, calc(50% - 48px))",
    background="#fff",
    border_radius=12,
    box_shadow=(
        "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
    ),
    padding=me.Padding(top=10, left=10, right=10, bottom=10),
    display="flex",
    flex_direction="column",
)