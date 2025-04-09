# Copyright 2024 Google LLC
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
""" Utility functions for prompts """
from __future__ import annotations
import json
import random

from google.api_core import exceptions as gapic_exceptions

from common.storage import download_gcs_blob
from config.default import Default

config = Default()

class PromptManager:
    """Singleton class to manage and provide image generation prompts"""
    _instance = None

    _prompts_location: str = config.DEFAULT_PROMPTS
    
    @property
    def prompts_location(self) -> str:
        return self._prompts_location

    @prompts_location.setter
    def prompts_location(self, new_location: str):
        if self._prompts_location == new_location:
            return
        self._prompts_location = new_location
        self._instance._load_prompts()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._load_prompts()
        return cls._instance

    def _load_prompts(self):
        """Loads prompts from the GCS blob into memory. Falls back to default prompt list."""
        self.prompts = {"prompts": []} #initialize to empty list to avoid errors.
        try:
            if self.prompts_location.startswith("gs://"):
                prompt_file = download_gcs_blob(gs_uri=self.prompts_location)
                prompt_file = prompt_file.decode("utf-8")
                self.prompts = json.loads(prompt_file)
            else:
                with open(config.DEFAULT_PROMPTS, "r") as f:
                    self.prompts = json.load(f)

        except gapic_exceptions.NotFound:
            print("Error: Requested blob not found, loading the default prompt list.")
            self.prompts_location = config.DEFAULT_PROMPTS

        except gapic_exceptions.Unauthorized:
            print("Error: Unauthorized to access requested blob.")

        except json.JSONDecodeError as e:
            print("Error: Requested blob is not a valid JSON. ", e)
        
        except UnicodeDecodeError as e:
            print("Error: Failed to decode requested blob. ", e)
        
        except FileNotFoundError:
            print("Error: imagen_prompts.json not found.")

    def random_prompt(self) -> str:
        """Returns a random image generation prompt."""
        if self.prompts and self.prompts["prompts"]:
            return random.choice(self.prompts["prompts"])
        else:
            return "Default prompt: No prompts available."  # Handle empty prompt list

if __name__ == "__main__":
    prompt_manager = PromptManager()
    random_prompt1 = prompt_manager.random_prompt()
    random_prompt2 = prompt_manager.random_prompt()

    print(random_prompt1)
    print(random_prompt2)

    # Verify singleton behavior:
    another_manager = PromptManager()
    print(prompt_manager is another_manager)  # Should print True