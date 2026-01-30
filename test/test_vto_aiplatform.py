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
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.vto import generate_vto_image

def test_generate_vto_image_aiplatform(gcs_bucket_for_tests):
    """Tests the generate_vto_image function using the aiplatform client."""
    person_image = f"{gcs_bucket_for_tests}/vto_person_images/vto_model_001.png"
    product_image = f"{gcs_bucket_for_tests}/vto_product_images/product_boho_blouse.png"
    # The original function expects base_steps as an argument.
    # We will use a default value of 50 for this test.
    gcs_uris = generate_vto_image(person_image, product_image, 1, 50)
    assert len(gcs_uris) == 1
    for uri in gcs_uris:
        assert uri.startswith("gs://")

    print(f"Generated {len(gcs_uris)} images:")
    for uri in gcs_uris:
        print(uri)
