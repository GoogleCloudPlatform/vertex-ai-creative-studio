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
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
GEMINI_LOCATION = os.getenv("GEMINI_LOCATION")
IMAGEN_LOCATION = os.getenv("IMAGEN_LOCATION")
VEO_LOCATION = os.getenv("VEO_LOCATION")
INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

MULTIMODAL_MODEL_NAME = "gemini-3.1-pro-preview"
VEO_MODEL_NAME = "veo-3.1-generate-001"
# NOTE: imagen-3.0-capability-001 is on the 2026-06-30 GA sunset list and has NO
# drop-in Imagen 4.0 successor for its mask-based edit/capability calls. The forward
# path is a behavior-changing port to Nano Banana (Gemini prompt-based editing), the
# same decision the core app shipped in PR #1659. That port is tracked separately and
# documented in MIGRATION.md; it is not a mechanical string swap. See #1672.
IMAGEN_MODEL_NAME = "imagen-3.0-capability-001"
