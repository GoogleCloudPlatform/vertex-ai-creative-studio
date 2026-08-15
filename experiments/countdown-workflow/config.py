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

# Google Cloud location for Vertex AI services. Used for the regional Veo
# (video generation) endpoint.
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Location for the Gemini text models and the Nano Banana (Gemini) image model.
# The Gemini 3.x family (gemini-3.7-flash, gemini-3.1-flash-image) is served only
# from the "global" endpoint and returns 404 in regional locations such as
# us-central1, so these calls use a dedicated location. This mirrors the core
# app's split between LOCATION (regional) and GEMINI_IMAGE_GEN_LOCATION=global.
GEMINI_LOCATION: str = os.getenv("GEMINI_LOCATION", "global")

# Specific model IDs for various AI tasks
# Nano Banana (Gemini image) — text-to-image via generate_content. Served from
# GEMINI_LOCATION (global).
IMAGE_GENERATION_MODEL: str = "gemini-3.1-flash-image"
# VIDEO_GENERATION_MODEL: str = "veo-3.1-generate-001"
VIDEO_GENERATION_MODEL: str = "veo-3.1-fast-generate-001"
SELECTOR_MODEL: str = "gemini-3.7-flash"
SCRIPT_GENERATION_MODEL: str = "gemini-3.7-flash"
REVERSE_ENGINEERING_MODEL: str = "gemini-3.7-flash"

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
