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
import logging
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
load_dotenv()

# --- Output Directories ---
# Base directory for downloaded video segments
VIDEO_OUTPUT_DIR: str = "video"
# Directory for video chunks after splitting
CHUNKS_OUTPUT_DIR: str = "chunks"
# Directory for AI-generated style analysis prompts
ENGINEERED_PROMPTS_OUTPUT_DIR: str = "engineered_prompts"
# Base directory for all generated company-specific video assets
GENERATED_VIDEO_BASE_OUTPUT_DIR: str = "generated_company_video"

# --- AI Model Configuration ---
# Google Cloud Project ID for Vertex AI
GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required.")

# Google Cloud location for Vertex AI services
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Specific model IDs for various AI tasks
IMAGE_GENERATION_MODEL: str = "imagen-4.0-generate-preview-06-06"
# VIDEO_GENERATION_MODEL: str = "veo-3.0-generate-preview"
VIDEO_GENERATION_MODEL: str = "veo-3.0-fast-generate-preview"
SELECTOR_MODEL: str = "gemini-2.5-pro"
SCRIPT_GENERATION_MODEL: str = "gemini-2.5-pro"
REVERSE_ENGINEERING_MODEL: str = "gemini-2.5-pro"

# --- Logging Configuration ---
LOG_LEVEL: int = logging.INFO
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE: str = "app.log"

# --- Skip rev eng config ---
SKIP_REVERSE_ENGINEERING=True

def setup_logging() -> None:
    """Configures the basic logging for the application."""
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ])
