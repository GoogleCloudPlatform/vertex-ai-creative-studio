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

import os
import io
from PIL import Image as PIL_Image
import google.genai as genai
from google.genai.types import (
    EditImageConfig,
    Image,
    MaskReferenceImage,
    RawReferenceImage,
    MaskReferenceConfig,
)
import config

# Initialize the Gemini client to use Vertex AI
client = genai.Client(vertexai=True, project=config.PROJECT_ID, location=config.GEMINI_LOCATION)
# NOTE: imagen-3.0-capability-001 is on the 2026-06-30 GA sunset list with no drop-in
# Imagen 4.0 successor for this mask-based outpaint call. Forward path is a Nano Banana
# port (see config.IMAGEN_MODEL_NAME note and MIGRATION.md). Tracked by #1673.
edit_model = "imagen-3.0-capability-001"

# Helper functions adapted from the notebook

def get_bytes_from_pil(image: PIL_Image.Image) -> bytes:
    """Gets the image bytes from a PIL Image object."""
    byte_io_png = io.BytesIO()
    image.save(byte_io_png, "PNG")
    return byte_io_png.getvalue()

def pad_to_target_size(
    source_image,
    target_size,
    mode="RGB",
    vertical_offset_ratio=0,
    horizontal_offset_ratio=0,
    fill_val=255,
):
    """Pads an image to a target size."""
    orig_image_size_w, orig_image_size_h = source_image.size
    target_size_w, target_size_h = target_size

    insert_pt_x = (target_size_w - orig_image_size_w) // 2 + int(
        horizontal_offset_ratio * target_size_w
    )
    insert_pt_y = (target_size_h - orig_image_size_h) // 2 + int(
        vertical_offset_ratio * target_size_h
    )
    insert_pt_x = min(insert_pt_x, target_size_w - orig_image_size_w)
    insert_pt_y = min(insert_pt_y, target_size_h - orig_image_size_h)

    if mode == "RGB":
        source_image_padded = PIL_Image.new(
            mode, target_size, color=(fill_val, fill_val, fill_val)
        )
    elif mode == "L":
        source_image_padded = PIL_Image.new(mode, target_size, color=(fill_val))
    else:
        raise ValueError("source image mode must be RGB or L.")

    source_image_padded.paste(source_image, (insert_pt_x, insert_pt_y))
    return source_image_padded

def pad_image_and_mask(
    image_pil: PIL_Image.Image,
    mask_pil: PIL_Image.Image,
    target_size,
    vertical_offset_ratio,
    horizontal_offset_ratio,
):
    """Pads and resizes an image and its mask to the same target size."""
    image_pil.thumbnail(target_size)
    mask_pil.thumbnail(target_size)

    image_pil_padded = pad_to_target_size(
        image_pil,
        target_size=target_size,
        mode="RGB",
        vertical_offset_ratio=vertical_offset_ratio,
        horizontal_offset_ratio=horizontal_offset_ratio,
        fill_val=0,
    )
    mask_pil_padded = pad_to_target_size(
        mask_pil,
        target_size=target_size,
        mode="L",
        vertical_offset_ratio=vertical_offset_ratio,
        horizontal_offset_ratio=horizontal_offset_ratio,
        fill_val=255, # White for the area to be filled
    )
    return image_pil_padded, mask_pil_padded

def outpaint_image(image_path: str, prompt: str) -> str:
    """
    Performs outpainting on an image to a 16:9 aspect ratio. This function
    takes the best-selected image and expands it to create a wider scene,
    which is more suitable for video generation. This helps to create a more
    dynamic and visually appealing video.
    """
    initial_image = PIL_Image.open(image_path)
    
    # Create a black mask with the same size as the original image
    mask = PIL_Image.new("L", initial_image.size, 0)

    # Define target 16:9 size
    target_height = 1080
    target_width = int(target_height * 16 / 9)
    target_size = (target_width, target_height)

    # Pad the image and mask
    image_pil_outpaint, mask_pil_outpaint = pad_image_and_mask(
        initial_image,
        mask,
        target_size,
        0,
        0,
    )

    # Convert to genai.Image objects
    image_for_api = Image(image_bytes=get_bytes_from_pil(image_pil_outpaint))
    mask_for_api = Image(image_bytes=get_bytes_from_pil(mask_pil_outpaint))

    # Create reference images for the API call
    raw_ref_image = RawReferenceImage(reference_image=image_for_api, reference_id=0)
    mask_ref_image = MaskReferenceImage(
        reference_id=1,
        reference_image=mask_for_api,
        config=MaskReferenceConfig(
            mask_mode="MASK_MODE_USER_PROVIDED",
            mask_dilation=0.03,
        ),
    )

    # Call the edit_image API
    edited_image_response = client.models.edit_image(
        model=edit_model,
        prompt=prompt,
        reference_images=[raw_ref_image, mask_ref_image],
        config=EditImageConfig(
            edit_mode="EDIT_MODE_OUTPAINT",
            number_of_images=1,
            safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
            person_generation="ALLOW_ALL",
        ),
    )
    
    # Save the outpainted image
    outpainted_image = edited_image_response.generated_images[0].image
    outpainted_image_path = os.path.join(os.path.dirname(image_path), "outpainted_image.png")
    
    # To save the PIL image from the response, we need to access the private _pil_image attribute
    # or save its bytes. Let's use the bytes.
    with open(outpainted_image_path, "wb") as f:
        f.write(outpainted_image.image_bytes)

    return outpainted_image_path
