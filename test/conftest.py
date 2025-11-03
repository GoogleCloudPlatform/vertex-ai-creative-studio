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

import pytest


def pytest_addoption(parser):
    """Adds a custom command-line option to pytest for specifying the GCS bucket."""
    parser.addoption(
        "--gcs-bucket",
        action="store",
        default="gs://genai-blackbelt-fishfooding-assets",
        help="The GCS bucket to use for tests that require GCS resources.",
    )


@pytest.fixture
def gcs_bucket_for_tests(request):
    """A pytest fixture that provides the GCS bucket from the command-line option."""
    return request.config.getoption("--gcs-bucket")
