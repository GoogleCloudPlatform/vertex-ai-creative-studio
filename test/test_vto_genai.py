import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from google.cloud import storage
from models.vto import generate_vto_image_genai

# This is a sample test file, you will need to adapt it to your needs.
# You will need to have a person and product image in GCS to run this test.

def test_generate_vto_image_genai(gcs_bucket_for_tests):
    """Tests the generate_vto_image_genai function."""
    person_image = f"{gcs_bucket_for_tests}/vto_person_images/vto_model_001.png"
    product_image = f"{gcs_bucket_for_tests}/vto_product_images/product_boho_blouse.png"
    gcs_uris = generate_vto_image_genai(person_image, product_image, 1)
    assert len(gcs_uris) == 1
    for uri in gcs_uris:
        assert uri.startswith("gs://")

    print(f"Generated {len(gcs_uris)} images:")
    for uri in gcs_uris:
        print(uri)
