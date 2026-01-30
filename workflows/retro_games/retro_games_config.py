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

import json
import os
import random
from typing import Any, Optional

from config.default import get_config_path

class RetroGameConfig:
    _instance = None
    _config_data = None
    _prompts_data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RetroGameConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Loads the configuration from the JSON file."""
        # Load Config
        config_path = get_config_path('workflows/retro_games/config.json')
        try:
            with open(config_path, 'r') as f:
                self._config_data = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config_data = {"themes": {}, "bumper_videos": []}

        # Load Prompts
        prompts_path = get_config_path('workflows/retro_games/prompts.json')
        try:
            with open(prompts_path, 'r') as f:
                self._prompts_data = json.load(f)
        except Exception as e:
            print(f"Error loading prompts: {e}")
            self._prompts_data = {}

    def get_prompt(self, key: str) -> str:
        """Returns a prompt template by key."""
        return self._prompts_data.get(key, "")

    def get_theme_names(self) -> list[str]:
        """Returns a list of available theme names."""
        return list(self._config_data.get("themes", {}).keys())

    def get_theme_config(self, theme_name: str) -> Optional[dict[str, str]]:
        """Returns the configuration for a specific theme."""
        return self._config_data.get("themes", {}).get(theme_name)

    def get_theme_prompt(self, theme_name: str) -> Optional[str]:
        """Returns the prompt for a specific theme."""
        theme = self.get_theme_config(theme_name)
        return theme.get("prompt") if theme else None

    def get_theme_logo(self, theme_name: str) -> Optional[str]:
        """Returns the logo URI for a specific theme."""
        theme = self.get_theme_config(theme_name)
        return theme.get("logo_uri") if theme else None

    def get_theme_8bit_logo(self, theme_name: str) -> Optional[str]:
        """Returns the 8-bit logo URI for a specific theme."""
        theme = self.get_theme_config(theme_name)
        return theme.get("logo_8bit_uri") if theme else None

    def get_random_bumper(self) -> Optional[str]:
        """Returns a random bumper video URI."""
        bumpers = self._config_data.get("bumper_videos", [])
        return random.choice(bumpers) if bumpers else None
