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
from models.vto import generate_vto_image

@pytest.mark.integration
def test_vto_api_call(gcs_bucket_for_tests):
    """An integration test that calls the real VTO API.
    
    This test is marked as 'integration' and will be skipped unless explicitly
    run with 'pytest -m integration'. It verifies that the application can
    successfully communicate with the live VTO API and receive a valid response.
    """
    # --- Arrange ---
    # Use the standard test assets for the person and product images.
    person_image = f"{gcs_bucket_for_tests}/vto_person_images/vto_model_001.png"
    product_image = f"{gcs_bucket_for_tests}/vto_product_images/product_boho_blouse.png"

    # --- Act ---
    # Call the actual generate_vto_image function, which will make a real API call.
    # This will take some time.
    gcs_uris = generate_vto_image(person_image, product_image, 1, 50)

    # --- Assert ---
    # Verify that the operation completed successfully and returned a valid response.
    assert gcs_uris is not None, "The API call should return a list of GCS URIs."
    assert isinstance(gcs_uris, list), "The result should be a list."
    assert len(gcs_uris) > 0, "The list of GCS URIs should not be empty."
    
    result_uri = gcs_uris[0]
    assert result_uri.startswith("gs://"), f"The returned URI should be a GCS URI. Got {result_uri}"

    print(f"\nIntegration test PASSED. VTO image generated successfully at: {result_uri}")

