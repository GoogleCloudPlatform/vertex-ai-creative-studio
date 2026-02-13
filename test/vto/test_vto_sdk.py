# VTO Python SDK

import os

from google import genai
from google.genai.types import (
    Image,
    ProductImage,
    RecontextImageConfig,
    RecontextImageSource,
)

PROJECT_ID = str(os.environ.get("GOOGLE_CLOUD_PROJECT"))
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

VTO_MODEL = os.environ.get("VTO_MODEL", "virtual-try-on-preview-08-04")


PERSON_IMAGE_GCS_URI = ""
CLOTHING_IMAGE_GCS_URI = "gs://cloud-samples-data/generative-ai/image/dress.jpg"


client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

virtual_try_on_response = client.models.recontext_image(
    model=VTO_MODEL,
    source=RecontextImageSource(
        person_image=PERSON_IMAGE_GCS_URI,
        product_images=[
            ProductImage(
                product_image=Image(
                    gcs_uri=CLOTHING_IMAGE_GCS_URI,
                )
            )
        ],
    ),
    config=RecontextImageConfig(
        output_mime_type="image/jpeg",
        number_of_images=1,
        safety_filter_level="BLOCK_LOW_AND_ABOVE",
    ),
)

image = virtual_try_on_response.generated_images[0].image



# class RecontextImageSource(_common.BaseModel):
#   """A set of source input(s) for image recontextualization."""

#   prompt: Optional[str] = Field(
#       default=None,
#       description="""A text prompt for guiding the model during image
#       recontextualization. Not supported for Virtual Try-On.""",
#   )
#   person_image: Optional[Image] = Field(
#       default=None,
#       description="""Image of the person or subject who will be wearing the
#       product(s).""",
#   )
#   product_images: Optional[list[ProductImage]] = Field(
#       default=None, description="""A list of product images."""
#   )



# class RecontextImageConfig(_common.BaseModel):
#   """Configuration for recontextualizing an image."""

#   http_options: Optional[HttpOptions] = Field(
#       default=None, description="""Used to override HTTP request options."""
#   )
#   number_of_images: Optional[int] = Field(
#       default=None, description="""Number of images to generate."""
#   )
#   base_steps: Optional[int] = Field(
#       default=None,
#       description="""The number of sampling steps. A higher value has better image
#       quality, while a lower value has better latency.""",
#   )
#   output_gcs_uri: Optional[str] = Field(
#       default=None,
#       description="""Cloud Storage URI used to store the generated images.""",
#   )
#   seed: Optional[int] = Field(
#       default=None, description="""Random seed for image generation."""
#   )
#   safety_filter_level: Optional[SafetyFilterLevel] = Field(
#       default=None, description="""Filter level for safety filtering."""
#   )
#   person_generation: Optional[PersonGeneration] = Field(
#       default=None,
#       description="""Whether allow to generate person images, and restrict to specific
#       ages.""",
#   )
#   add_watermark: Optional[bool] = Field(
#       default=None,
#       description="""Whether to add a SynthID watermark to the generated images.""",
#   )
#   output_mime_type: Optional[str] = Field(
#       default=None, description="""MIME type of the generated image."""
#   )
#   output_compression_quality: Optional[int] = Field(
#       default=None,
#       description="""Compression quality of the generated image (for ``image/jpeg``
#       only).""",
#   )
#   enhance_prompt: Optional[bool] = Field(
#       default=None, description="""Whether to use the prompt rewriting logic."""
#   )
#   labels: Optional[dict[str, str]] = Field(
#       default=None,
#       description="""User specified labels to track billing usage.""",
#   )
