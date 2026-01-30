# Copyright 2026 Google LLC
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
import pytest
import concurrent.futures
from google import genai
from google.genai import types
from PIL import Image
from config.default import Default

# Initialize configuration
cfg = Default()

def create_dummy_image_bytes():
    """Creates a simple dummy image and returns its bytes."""
    # Create a slightly more complex image (gradient) to ensure it's not just flat color issues
    img = Image.new('RGB', (1024, 1024), color='blue')
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    return byte_io.getvalue()

def call_edit_image(client, model_name, prompt, reference_images, negative_prompt):
    """Wrapper to call edit_image, to be used in ThreadPoolExecutor."""
    print(f"Thread calling edit_image with model {model_name}...")
    return client.models.edit_image(
        model=model_name,
        prompt=prompt,
        reference_images=reference_images,
        config=types.EditImageConfig(
            edit_mode="EDIT_MODE_DEFAULT",
            number_of_images=1,
            aspect_ratio="1:1",
            person_generation="allow_all",
            safety_filter_level="block_only_high", # Fixed from block_few
            negative_prompt=negative_prompt,
        ),
    )

@pytest.mark.integration
def test_imagen_capability_subject_reference_threaded():
    """
    Test specifically targeting imagen-3.0-capability-001 with SubjectReferenceImage,
    replicating the ThreadPoolExecutor pattern from models/character_consistency.py.
    """
    print(f"\n--- Starting Test: imagen-3.0-capability-001 Subject Reference (Threaded) ---")
    
    # 1. Setup Client
    client = genai.Client(vertexai=True, project=cfg.PROJECT_ID, location=cfg.LOCATION)
    model_name = "imagen-3.0-capability-001"
    
    # 2. Prepare Input Data
    reference_image_bytes = create_dummy_image_bytes()
    # Use a longer, more realistic description
    subject_description = "A young woman with shoulder-length brown hair, wearing a red leather jacket and a white t-shirt. She has green eyes and a neutral expression."
    prompt = "A cinematic shot of the woman standing on a rooftop overlooking a cyberpunk city at night. Neon lights reflect off her jacket."
    negative_prompt = "blurry, distorted, low quality, ugly, deformed hands"

    # 3. Construct Reference Object
    image = types.Image(image_bytes=reference_image_bytes)
    
    reference_images_for_generation = [
        types.SubjectReferenceImage(
            reference_id=0,
            reference_image=image,
            config=types.SubjectReferenceConfig(
                subject_type="SUBJECT_TYPE_PERSON",
                subject_description=subject_description,
            ),
        ),
    ]

    # 4. Make API Call within ThreadPoolExecutor
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                call_edit_image, 
                client, 
                model_name, 
                prompt, 
                reference_images_for_generation, 
                negative_prompt
            )
            response = future.result() # This will raise if the thread raised
        
        print("Request completed.")

        # 5. Verify Response
        assert response is not None
        assert response.generated_images is not None
        assert len(response.generated_images) > 0
        print(f"Success! Generated {len(response.generated_images)} images.")

    except Exception as e:
        print(f"\n!!! API Call Failed !!!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        raise

if __name__ == "__main__":
    test_imagen_capability_subject_reference_threaded()
