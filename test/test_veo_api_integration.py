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
from models.veo import text_to_video
from config.veo_models import VEO_MODELS

# Parametrize the test to run for each model defined in the configuration.
@pytest.mark.integration
@pytest.mark.parametrize("model_config", VEO_MODELS)
def test_veo_t2v_api_call(gcs_bucket_for_tests, model_config):
    """An integration test that calls the real VEO API for text-to-video.
    
    This test is marked as 'integration' and will be skipped unless explicitly
    run with 'pytest -m integration'. It verifies that the application can
    successfully communicate with the live VEO API and receive a valid response
    for every supported model.
    """
    # --- Arrange ---
    # Use a simple, reliable prompt that is unlikely to trigger content filters.
    prompt = "a happy dog running on a sunny beach"
    output_gcs = f"{gcs_bucket_for_tests}/integration_tests"

    # --- Act ---
    # Call the actual text_to_video function, which will make a real API call.
    # The duration and other parameters are now pulled from the model's config.
    operation_result = text_to_video(
        model=model_config.version_id,
        prompt=prompt,
        seed=42,
        aspect_ratio=model_config.supported_aspect_ratios[0], # Use the first supported aspect ratio
        sample_count=model_config.default_samples,
        output_gcs=output_gcs,
        enable_pr=model_config.supports_prompt_enhancement,
        duration_seconds=model_config.default_duration,
    )

    # --- Assert ---
    # Print the full response object for debugging purposes.
    print(f"\n--- Full API Response for model {model_version} ---")
    print(operation_result)
    print("----------------------------------------------------")

    # Verify that the operation completed successfully and returned a valid response.
    assert operation_result is not None, "The API operation result should not be None."
    assert operation_result.get("done"), f"The 'done' flag in the operation should be True. Full response: {operation_result}"

    # Explicitly check for a top-level error in the operation result.
    if 'error' in operation_result:
        pytest.fail(f"API returned a top-level error: {operation_result['error']}")

    response_data = operation_result.get("response", {})
    assert "videos" in response_data, f"The response should contain a 'videos' key. Full response: {operation_result}"

    videos = response_data["videos"]
    assert len(videos) > 0, "The 'videos' list should not be empty."

    video_uri = videos[0].get("gcsUri")
    assert video_uri is not None, "The video should have a 'gcsUri'."
    assert video_uri.startswith(output_gcs), f"The video URI should be in the specified output bucket. Got {video_uri}"

    print(f"\nIntegration test for model {model_version} PASSED. Video generated successfully at: {video_uri}")

