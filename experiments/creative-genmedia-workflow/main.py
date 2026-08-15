# Copyright 2025 Google LLC
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

# Changelog
# v1 - version for github

import mesop as me
import os, io
import json 
import time
import pandas as pd
from dataclasses import field
from urllib.parse import quote

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    Part,
    Tool,
)
from google.cloud import storage

# ======== Environment Set up ========

BUCKET = os.environ.get("BUCKET")
BUCKET_URI = f"gs://{BUCKET}/"
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION")

print(f"\nLoading...\nUsing project: {PROJECT_ID}, location: {LOCATION}, bucket: {BUCKET}")

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket = storage_client.get_bucket(BUCKET)

# ======== Application Configuration ========

VERSION = "v1.0"
MAIN_TITLE = "Creative GenMedia Demo"
LOGO_URL = "https://developers.google.com/workspace/images/cymbal/wordmark.png"
SHOWCASE_CSV_URI = "outputs/showcase_outputs.csv"

# Using palette https://coolors.co/palette/03045e-023e8a-0077b6-0096c7-00b4d8-48cae4-90e0ef-ade8f4-caf0f8
BACKGROUND_COLOUR_FRONT = "#ADE8F4"
AGENT_TEXT_BACKGROUND = "#ADE8F4" # Background to "How can I help today" 
BACKGROUND_COLOUR_CONTENT =  "#E8F9FC"
TEXT_COLOUR = "#03045E" 
BUTTON_COLOUR = "#90E0EF" 
BUTTON_TEXT_COLOUR = "#03045E" 

# ======== LLMs ========

# Initialize Generative Models

model_20_flashlite = "gemini-3.1-flash-lite"
model_20_flash = "gemini-3.5-flash"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
print(f"Using GenAI SDK version: {genai.__version__}")

# Model calling functions

def call_gemini_with_retry(func, max_retries=10, retry_delay=2, **kwargs):
    """
    Calls a given function with retry logic.

    Args:
    func: The function to call.
    max_retries: The maximum number of retries.
    retry_delay: The delay between retries in seconds.
    **kwargs: Keyword arguments to pass to the function.

    Returns:
    The result of the function call if successful, otherwise None.
    """
    retries = 0
    success = False
    print("Calling gemini with retry")
    while not success and retries < max_retries:
        try:
            response = func(**kwargs)
            success = True
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
            print(f"Attempt {retries + 1} failed. Retrying...")
        finally:
            retries += 1
            time.sleep(retry_delay)

    if not success and retries == max_retries:
        print("Max retries reached. Returning None.")
        return None

def gemini_grounding_call():
    s=me.state(State)
    print("Calling gemini with grounding")
    generation_config = GenerateContentConfig(
        temperature=0.0,
        tools=([Tool(google_search=GoogleSearch())])
    )
    contents = [s.inspo_prompt]
    print(f"Prompt: {s.inspo_prompt}")

    def gemini_call():
        return client.models.generate_content(
            model=model_20_flashlite,
            contents=contents,
            config=generation_config,
        )
    
    response = call_gemini_with_retry(gemini_call)

    grounding_metadata = response.candidates[0].grounding_metadata
    markdown_parts = []

    # Citation indexes are in bytes
    ENCODING = "utf-8"
    text_bytes = response.text.encode(ENCODING)
    last_byte_index = 0

    for support in grounding_metadata.grounding_supports:
        markdown_parts.append(
            text_bytes[last_byte_index : support.segment.end_index].decode(ENCODING)
        )

        # Generate and append citation footnotes (e.g., "[1][2]")
        footnotes = "".join([f"[{i + 1}]" for i in support.grounding_chunk_indices])
        markdown_parts.append(f" {footnotes}")

        # Update index for the next segment
        last_byte_index = support.segment.end_index

    # Append any remaining text after the last citation
    if last_byte_index < len(text_bytes):
        markdown_parts.append(text_bytes[last_byte_index:].decode(ENCODING))

    markdown_parts.append("\n\n----\n## Grounding Sources\n")

    # Build Grounding Sources Section
    for i, chunk in enumerate(grounding_metadata.grounding_chunks, start=1):
        context = chunk.web or chunk.retrieved_context
        if not context:
            continue

        uri = context.uri
        title = context.title or "Source"

        # Convert GCS URIs to public HTTPS URLs
        if uri and uri.startswith("gs://"):
            uri = uri.replace("gs://", "https://storage.googleapis.com/", 1).replace(
                " ", "%20"
            )
        markdown_parts.append(f"{i}. [{title}]({uri})\n")

    # Add Search/Retrieval Queries
    if grounding_metadata.web_search_queries:
        markdown_parts.append(
            f"\n**Web Search Queries:** {grounding_metadata.web_search_queries}\n"
        )
        if grounding_metadata.search_entry_point:
            markdown_parts.append(
                f"\n**Search Entry Point:** {grounding_metadata.search_entry_point.rendered_content}\n"
            )
    elif grounding_metadata.retrieval_queries:
        markdown_parts.append(
            f"\n**Retrieval Queries:** {grounding_metadata.retrieval_queries}\n"
        )

    output = "".join(markdown_parts)

    if response is not None:
        s.inspo_output_refs = output
    else:
        print("API call failed")
    return

PROMPT_CREATIVE_BASE = """# ROLE AND GOAL
You are a world-class Marketing Strategist and Creative Director based in the UK, with specialist expertise in creating cohesive, multi-format campaigns for consumer brands. Your goal is to analyze the provided inputs and generate a comprehensive set of creative assets, strictly adhering to all brand guidelines.

# INPUTS
You will be provided with the following:
1.  **[USER_BRIEF]**: A one or two-sentence brief from the user.
2.  **[BRAND_GUIDELINES]**:  A brand guidelines document.
3.  **[ITEM_TITLE]**:  The item's title.
4.  **[IMAGE]**: An image that will serve as the primary creative asset.

# THINKING PROCESS (Follow these steps internally before generating the output)
1.  **Deconstruct Inputs**: First, thoroughly analyze all provided inputs. From the [BRAND_GUIDELINES], identify the core brand voice, tone, target audience, key messaging pillars, and any strict "Dos and Don'ts". From the [USER_BRIEF] and [IMAGE], understand the specific goal of this campaign.
2.  **Formulate Strategy**: Based on your analysis, develop a single, powerful creative concept or "big idea". This concept will be the narrative thread that connects all the outputs. Consider: What is the story we are telling? What emotion are we trying to evoke? How does this directly serve the user's brief?
3.  **Generate Assets**: Using your strategy, create the required outputs. Ensure every single output is fully aligned with the creative concept and the [BRAND_GUIDELINES].

# OUTPUT STRUCTURE
Generate a single, valid JSON object. Use only British English spelling and terminology. Do not include any commentary outside of the JSON structure.

# OUTPUT GUIDANCE

## Summary
A concise summary of the task.
*   **User Brief:** Summarize the key takeaways in one or two sentences.
*   **Brand Guidelines:** Summarize the key takeaways in one or two sentences.
*   **Image:** Summarize the key takeaways in one or two sentences.

## Approach
### Creative Concept
A compelling paragraph explaining the core story or 'big idea' for this campaign. This should be the central narrative thread connecting all assets and engaging the target audience.
### Target Emotion
Describe the primary emotion the creative assets should evoke in the customer (e.g., 'Nostalgic warmth', 'Excited anticipation', 'Confident empowerment').
### Guideline Alignment
Briefly explain how the proposed creative concept and assets specifically adhere to the key principles of the provided `[BRAND_GUIDELINES]`.

## Copy Options
### Email Subject Line
Create two compelling subject line options. Max 60 characters each.
### Social Media - Instagram / Facebook
A short, engaging post to accompany the image. Include relevant emojis and suggest 3-5 relevant hashtags. Max 280 characters.
### Website Hero Banner
*   **Headline:** A powerful, punchy headline. Max 8 words.
*   **Sub-headline:** A supporting sentence that adds context or a call-to-action. Max 15 words.

## Video Prompt
### Thinking
Give details of the approach which has been chosen. Consider the background of the image and ensure the video narrative fits with the existing background. If the background is blank or a studio shot then describe the new background which should be used in the video.
### Scene Description
A detailed description of an 8-second video. Simple approaches with one or two main shots are most effective. The image provided must be the first frame, unless as previously described a new background is to be used. Describe the starting item (don't use the product name directly) and any subsequent camera movements (e.g., 'slow zoom out', 'gentle pan right', 'focus pull'). Maintain focus on the primary subject for the majority of the video. The scene must not contain children, additional logos/branding, or text overlays. 
### Audio Description
A description of the audio for the video. Be highly specific and evocative (e.g., 'The sound of gentle waves and a distant seagull', 'The sizzle of a BBQ and light, upbeat acoustic guitar music', 'The pop of a cork and celebratory background chatter'). Don't overcomplicate things, consider if music is needed or just atmospheric audio.
### Final prompt
Combine the scene and audio described into a succinct paragraph prompt to be used to generate the video. Indicate this is code in formatting.
**Important**: ONLY if a new background is to be added (where the image has a blank background), begin the prompt with the exact phrase: "Switch to scene..." followed immediately by the description of the new background. Remember, only use this phrase if the product background is blank or a studio shot.
### Sample prompt outputs
`A close-up shot of two glasses filled with colourful summer drinks sitting on a sun-drenched table. A slow zoom out reveals the setting: a garden or patio bathed in sunlight, with gentle shadows playing across the surface. The camera gently pans right, maintaining focus on the drinks, highlighting the vibrant colours and refreshing ingredients. The audio features the gentle clinking of ice in the glasses, overlaid with the cheerful sound of birdsong and the distant murmur of a tennis match commentary. The soundscape evokes a relaxing summer atmosphere, capturing the essence of a leisurely afternoon.`

`Switch to scene of the garden sofa in a sunlit garden. Soft, natural light highlights the texture of the sofa. The camera slowly zooms out to reveal a patio setting with plants and a small table with a jug. The camera gently pans right, maintaining focus on the sofa, with a gentle defocus to the table. The scene concludes with a slightly wider shot showcasing the sofa and the inviting ambience of the garden. The audio consists of the gentle buzzing of bees, light summery music with acoustic guitar, and the clinking of glasses being placed on the table. The background audio evokes a relaxing summer atmosphere, capturing the essence of a leisurely afternoon.`
"""

def gemini_creative_call():
    s=me.state(State)
    print("Calling gemini with creative inputs")

    response_schema = {
    "type": "object",
    "properties": {
        "response": {
        "type": "object",
        "properties": {
            "summary": {
            "type": "string"
            },
            "approach": {
            "type": "string"
            },
            "copy": {
            "type": "string"
            },
            "video_prompt": {
            "type": "string"
            }
        },
        "required": [
            "summary",
            "approach",
            "copy",
            "video_prompt"
        ]
        }
    },
    "required": [
        "response"
    ]
    }

    generation_config = GenerateContentConfig(
        temperature=1.0,
        response_mime_type="application/json",
        response_schema=response_schema,
    )

    contents = [PROMPT_CREATIVE_BASE]
    # Add brief 
    print(f" **[USER_BRIEF]**: {s.input_creative['brief']}")
    contents.append("**[USER_BRIEF]**")
    contents.append(s.input_creative['brief'])
    # Get image & title
    print(f" **[ITEM_TITLE]**: {s.input_creative['title']}")
    print(f" **[IMAGE]**: {s.input_creative['image_url']}")
    # image_file = Part.from_uri(file_uri=s.input_creative['image_url'], mime_type="image/webp")
    image_file = Part.from_uri(file_uri=s.input_creative['image_url'], mime_type="image/png")
    contents.append("**[ITEM_TITLE]**")
    contents.append(s.input_creative['title'])
    contents.append("**[IMAGE]**")
    contents.append(image_file)
    # Get branding guidelines doc
    print(f" **[BRAND_GUIDELINES]**: {s.input_creative['brand_uri']}")
    brand_file = Part.from_uri(file_uri=s.input_creative['brand_uri'], mime_type="application/pdf") 
    contents.append("**[BRAND_GUIDELINES]**")
    contents.append(brand_file)

    def gemini_call():
        return client.models.generate_content(
            model=model_20_flash,
            contents=contents,
            config=generation_config,
        )
    
    response = call_gemini_with_retry(gemini_call)

    if response is not None:
        s.creative_output = response.text
    else:
        print("API call failed")
    return

# ======== General helper functions ========

def convert_gcs_to_url(uri):
    url = uri.replace('gs://', 'https://storage.cloud.google.com/')
    return quote(url, safe=":/?#%")

def load_showcase():
    s = me.state(State)
    print(f"Loading showcase data from {SHOWCASE_CSV_URI}")

    blob = bucket.blob(SHOWCASE_CSV_URI)
    s.showcase_df = pd.read_csv(io.BytesIO(blob.download_as_bytes()))

# ======== Handlers ========

# Navigation

def handle_click_text_box(e: me.ClickEvent):
    print(f"Link for {e.key} is clicked")
    me.navigate(f"/{e.key}")

def handle_button_nav_index(e: me.ClickEvent):
    s = me.state(State)
    me.navigate("/")

def handle_button_nav_showcase(e: me.ClickEvent):
    s = me.state(State)
    me.navigate("/showcase")

# Inspiration page

def handle_textarea_prompt_inspo_onblur(e: me.InputBlurEvent):
    s = me.state(State)
    s.inspo_prompt = e.value
    print(e.value)
    print(f"Inspo prompt updated to {s.inspo_prompt}")

def handle_button_inspo_submit(e: me.ClickEvent):
    s = me.state(State)
    print("Inspo submit button clicked")
    s.inspo_output_refs = ""
    gemini_grounding_call()

# Creative page

def handle_input_image_url_onblur(e: me.InputEvent):
    s = me.state(State)
    s.input_creative["image_url"] = e.value

def handle_input_title_onblur(e: me.InputEvent):
    s = me.state(State)
    s.input_creative["title"] = e.value

def handle_input_brand_uri_onblur(e: me.InputEvent):
    s = me.state(State)
    s.input_creative["brand_uri"] = e.value

def handle_input_brief_onblur(e: me.InputEvent):
    s = me.state(State)
    s.input_creative["brief"] = e.value

def handle_button_creative_submit(e: me.ClickEvent):
    s = me.state(State)
    print("Creative submit button clicked")
    gemini_creative_call()

def handle_button_creative_clear(e: me.ClickEvent):
    s = me.state(State)
    print("Creative inputs clear button clicked")
    s.input_creative = {
        "image_url": "",
        "title": "",
        "brand_uri": "",
        "brief": "",
    }
    s.creative_output = ""

# Use to add buttons on creative page to add details on a click 

# def handle_button_insert_item(e: me.ClickEvent):
#     s = me.state(State)
#     print("Insert taco details button clicked")
#     s.input_creative = {
#         "image_url": "",
#         "title": "",
#         "brand_uri": "",
#         "brief": "",
#     }
#     s.creative_output = ""

def handle_button_insert_basket(e: me.ClickEvent):
    s = me.state(State)
    print("Insert basket details button clicked")
    s.input_creative = {
        "image_url": f"{BUCKET_URI}inputs/basket.png",
        "title": "The Harmony Picnic Basket",
        "brand_uri": f"{BUCKET_URI}inputs/Cymbal Brand Guidelines.pdf",
        "brief": "Picnics on the beach this summer",
    }
    s.creative_output = ""

def handle_button_insert_mug(e: me.ClickEvent):
    s = me.state(State)
    print("Insert mug details button clicked")
    s.input_creative = {
        "image_url": f"{BUCKET_URI}inputs/mug.png",
        "title": "The Stillness Stoneware Mug",
        "brand_uri": f"{BUCKET_URI}inputs/Cymbal Brand Guidelines.pdf",
        "brief": "Comforting warm drinks on rainy days",
    }
    s.creative_output = ""

# Not currently used
def handle_button_insert_rug(e: me.ClickEvent):
    s = me.state(State)
    print("Insert rug details button clicked")
    s.input_creative = {
        "image_url": f"{BUCKET_URI}inputs/rug.png",
        "title": "The Horizon Wool Throw",
        "brand_uri": f"{BUCKET_URI}inputs/Cymbal Brand Guidelines.pdf",
        "brief": "Chilled days at home",
    }
    s.creative_output = ""

def handle_button_insert_balm(e: me.ClickEvent):
    s = me.state(State)
    print("Insert balm details button clicked")
    s.input_creative = {
        "image_url": f"{BUCKET_URI}inputs/balm.png",
        "title": "Harmonious Hydration Balm",
        "brand_uri": f"{BUCKET_URI}inputs/Cymbal Brand Guidelines.pdf",
        "brief": "Pamper yourself",
    }
    s.creative_output = ""

# ======== UI Components ========

def page_header(page_title="In progress"):
    with me.box(style=STYLE_TITLE):
        me.image(src=LOGO_URL, style=me.Style(width=200, margin=me.Margin(right=20, bottom=20)))
        me.button(label="Back to Main Page", on_click=handle_button_nav_index, style=BUTTON_STYLE)
    me.text(page_title, type="headline-4", style=me.Style(color=TEXT_COLOUR))

def make_clickable_text_box(text, page):
    with me.box(
        key=page,
        on_click=handle_click_text_box,
        style=TEXT_HOLDING_USER
    ):
        me.text(text, type="body-2")

# ======== State ========

@me.stateclass
class State:
    # Loaded from files
    showcase_df: pd.DataFrame | None = None # showcase video locations and details
    # Inspiration related
    inspo_prompt: str = "How might I tailor a marketing campaign for homewares in a department store to young professionals for this summer? Suggest and outline 3 campaign ideas."
    inspo_output_refs: str
    # Creative related
    input_creative: dict = field(default_factory=lambda:{
        "image_url": "",
        "title": "",
        "brand_uri": "",
        "brief": "",
    })
    creative_input_filled: bool = True
    creative_output: str

# ======== Main application  ========

@me.page(title=MAIN_TITLE, path="/")
def page_index():
    s=me.state(State)
    with me.box(style=WELCOME_BACK_BOX):
        me.image(src=LOGO_URL, style=me.Style(width=250, padding=me.Padding.all(20), margin=me.Margin(top=50, left=50, bottom=-50)))
        with me.box(style=WELCOME_HOLDING):
            me.text(text="How can I help today?", type="headline-5", style=TEXT_STYLE_AGENT)
            make_clickable_text_box(text="I need inspiration related to trends", page="inspo")
            make_clickable_text_box(text="I want to create media from existing content", page="create")
            make_clickable_text_box(text="Show me some outputs", page="showcase")
    with me.box(style=me.Style(display="flex", flex_direction="row", justify_content="end", background="white", height="3%")):
        me.text(VERSION, style=me.Style(color="gray"))

@me.page(title=MAIN_TITLE, path="/inspo")
def page_inspo():
    s=me.state(State)
    with me.box(style=STYLE_BACK):
        with me.box(style=STYLE_BOX_HOLDING):
            page_header(page_title="Get inspiration")
            me.textarea(label="Ask your question here using Gemini with Google Search", value=s.inspo_prompt, on_blur=handle_textarea_prompt_inspo_onblur, appearance="outline", style=me.Style(width="100%"), rows=2,)
            me.button("Ask Gemini", on_click=handle_button_inspo_submit, style=BUTTON_STYLE)
            if len(s.inspo_output_refs) > 0:
                me.markdown(s.inspo_output_refs, style=me.Style(line_height=1.5))

@me.page(title=MAIN_TITLE, path="/create")
def page_create():
    s=me.state(State)
    with me.box(style=STYLE_BACK):
        with me.box(style=STYLE_BOX_HOLDING):
            page_header(page_title="Let's get creative!")
            with me.box(style=me.Style(display="flex", flex_direction="row", justify_content="space-evenly")):
                with me.box(style=me.Style(display="flex", flex_direction="column", flex_grow=1)):
                    me.input(label="Item title", on_blur=handle_input_title_onblur, value=s.input_creative['title'], appearance="outline", style=me.Style(width="90%"))
                    me.input(label="Image (URL or GCS URI, expects png)", on_blur=handle_input_image_url_onblur, value=s.input_creative['image_url'], appearance="outline", style=me.Style(width="90%"))
                    me.input(label="Brand guidelines (GCS URI, expects PDF)", on_blur=handle_input_brand_uri_onblur, value=s.input_creative['brand_uri'], appearance="outline", style=me.Style(width="90%"))
                    me.input(label="Brief", appearance="outline", on_blur=handle_input_brief_onblur, value=s.input_creative['brief'], style=me.Style(width="90%"))
                if s.input_creative['image_url'][:2] == "gs":
                    me.image(src=convert_gcs_to_url(s.input_creative['image_url']), style=me.Style(width="500px", border_radius=10))
                elif s.input_creative['image_url'][:4] == "http":
                    me.image(src=s.input_creative['image_url'], style=me.Style(width="500px", border_radius=10))
            with me.expansion_panel(title="Brand guidelines and base prompt", style=me.Style(background=BACKGROUND_COLOUR_CONTENT, margin=me.Margin(bottom=20))):
                if len(s.input_creative['brand_uri']) > 0:
                    me.markdown(f"[Brand guidelines document]({convert_gcs_to_url(s.input_creative['brand_uri'])}) (right click to open in new tab)", style=me.Style(font_size=14))
                    me.divider()
                me.markdown("**Base prompt used:**", style=me.Style(font_size=14))
                me.markdown(PROMPT_CREATIVE_BASE, style=me.Style(font_size=11))
            with me.box(style=me.Style(display="flex", flex_direction="row", justify_content="space-between")):
                with me.box(style=me.Style(display="flex", flex_direction="column", )):
                    me.button("Create my outputs", on_click=handle_button_creative_submit, style=BUTTON_STYLE)
                    me.button("Clear inputs", on_click=handle_button_creative_clear, type="stroked", style=BUTTON_STYLE_BACK)
                with me.box(style=me.Style(display="flex", flex_direction="column", align_items="flex-end")):
                #     me.button("Insert item", on_click=handle_button_insert_item, type="stroked", style=BUTTON_STYLE_BACK)
                    me.button("Picnic Basket", on_click=handle_button_insert_basket, type="stroked", style=BUTTON_STYLE_BACK)
                    me.button("Stoneware Mug", on_click=handle_button_insert_mug, type="stroked", style=BUTTON_STYLE_BACK)
                    me.button("Balm", on_click=handle_button_insert_balm, type="stroked", style=BUTTON_STYLE_BACK)
            if len(s.creative_output) > 0:
                # me.markdown(s.creative_output) # for debug
                markdown_output = []
                for key, value in json.loads(s.creative_output)['response'].items():
                    heading = key.replace("_", " ").title()
                    markdown_output.append(f"## {heading}\n")
                    markdown_output.append(f"{value}\n\n")
                me.markdown("".join(markdown_output), style=me.Style(line_height=1.5))
            me.box(style=me.Style(margin=me.Margin(top=10, bottom=10)))
            me.button("Let's see some generated videos", on_click=handle_button_nav_showcase, style=BUTTON_STYLE)

@me.page(title=MAIN_TITLE, path="/showcase")
def page_showcase():
    s=me.state(State)
    if s.showcase_df is None:
        load_showcase()
    with me.box(style=STYLE_BACK):
        with me.box(style=STYLE_BOX_HOLDING):
            page_header(page_title="Showcase")
            for row in s.showcase_df.itertuples():
                with me.box(style=me.Style(display="flex", flex_direction="row", justify_content="space-evenly", margin=me.Margin(top=20, bottom=20))):
                    with me.box(style=me.Style(display="flex", flex_direction="column", flex_grow=1, margin=me.Margin(right=20))):
                        me.markdown(f"**[{row.title}]({row.item_url})**")
                        me.markdown(f"Brief: {row.brief}")
                        me.text(f"{row.prompt}", style=me.Style(font_size=13))
                    me.video(src=convert_gcs_to_url(BUCKET_URI+row.video_uri), style=me.Style(width="600px", border_radius=10))
                me.divider()
            

# Mesop UI Style Constants

WELCOME_BACK_BOX = me.Style(
    background=BACKGROUND_COLOUR_FRONT,
    height="97%",
    display="flex",
    flex_direction="column", 
)

WELCOME_HOLDING = me.Style(
    display="flex", 
    flex_direction="column", 
    width="min(800px, 100%)", 
    background="white",
    border_radius=15,
    box_shadow=(
    "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
    ),
    padding=me.Padding.all(30),
    margin=me.Margin.all("auto"), # pushes this box into the middle
    # align_items="center", # pushes items inside into middle and squeezes size down of all items... 
)

TEXT_STYLE_AGENT = me.Style(
    background=AGENT_TEXT_BACKGROUND,
    width="75%",
    border_radius=15,
    box_shadow=(
    "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
    ),
    padding=me.Padding.all(20),
)

TEXT_HOLDING_USER = me.Style(
    cursor="pointer", # only needed when box becomes the "button"
    display="flex",
    flex_direction="row",
    background=BACKGROUND_COLOUR_CONTENT,
    border_radius=15,
    box_shadow=(
    "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
    ),
    # width="75%",
    padding=me.Padding.all(15),
    margin=me.Margin.all(5),
    align_self="end", # override the default alignment for this box
    justify_content="end" # where the items in this box are aligned
)

BUTTON_STYLE = me.Style(
    background=BUTTON_COLOUR, 
    color=BUTTON_TEXT_COLOUR,
    margin=me.Margin.all(5),
)

BUTTON_STYLE_BACK = me.Style(
    background=BACKGROUND_COLOUR_CONTENT, 
    color=BUTTON_TEXT_COLOUR,
    margin=me.Margin.all(5),
)

TEXT_STYLE_USER = me.Style(
    padding=me.Padding.all(10),
)

STYLE_BACK = me.Style(
    background=BACKGROUND_COLOUR_CONTENT,
    height="100%",
    overflow_y="scroll",
    # margin=me.Margin(bottom=20),
)

STYLE_BOX_HOLDING = me.Style(
    # background=BACKGROUND_COLOUR,
    margin=me.Margin(left="auto", right="auto"),
    padding=me.Padding(top=24, left=24, right=24, bottom=24),
    width="min(1024px, 100%)",
    display="flex",
    flex_direction="column",
)

STYLE_BOX_WHITE = me.Style(
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

STYLE_TITLE = me.Style(
    display="flex", 
    flex_direction="row", 
    justify_content="space-between", 
    margin=me.Margin(top="20px", bottom="0px")
    # padding=me.Padding.all(12)
)

