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



import pytest
from models.image_models import generate_images
from config.imagen_models import IMAGEN_MODELS

# Parametrize the test to run for each model defined in the configuration.
@pytest.mark.integration
@pytest.mark.parametrize("model_config", IMAGEN_MODELS)
def test_imagen_api_call(gcs_bucket_for_tests, model_config):
    """An integration test that calls the real Imagen API for text-to-image.
    
    This test is marked as 'integration' and will be skipped unless explicitly
    run with 'pytest -m integration'. It verifies that the application can
    successfully communicate with the live Imagen API and receive a valid response
    for every supported model.
    """
    # --- Arrange ---
    # Use a simple, reliable prompt that is unlikely to trigger content filters.
    prompt = "a happy dog running on a sunny beach"
    output_gcs = f"{gcs_bucket_for_tests}/integration_tests"

    # --- Act ---
    # Call the actual generate_images function, which will make a real API call.
    response = generate_images(
        model=model_config.model_name,
        prompt=prompt,
        number_of_images=model_config.default_samples,
        aspect_ratio=model_config.supported_aspect_ratios[0], # Use the first supported aspect ratio
        negative_prompt="",
    )

    # --- Assert ---
    # Verify that the operation completed successfully and returned a valid response.
    assert response is not None, "The API response should not be None."
    assert hasattr(response, 'generated_images'), "The response should have a 'generated_images' attribute."
    
    generated_images = response.generated_images
    assert len(generated_images) > 0, "The 'generated_images' list should not be empty."
    
    image = generated_images[0].image
    assert image is not None, "The generated image should not be None."
    assert hasattr(image, 'gcs_uri'), "The image should have a 'gcs_uri' attribute."
    assert image.gcs_uri.startswith("gs://"), f"The returned URI should be a GCS URI. Got {image.gcs_uri}"

    print(f"\nIntegration test for model {model_config.model_name} PASSED. Image generated successfully at: {image.gcs_uri}")

