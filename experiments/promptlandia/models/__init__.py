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

"""
The `models` package contains the core business logic for interacting with
Generative AI models. It is designed to be used by both the web application
(Mesop) and command-line tools.
"""

from models.gemini import (
    gemini_generate_content as generate_content,
    gemini_improve_this_prompt as improve_prompt,
    gemini_thinking_thoughts as generate_thoughts,
    gemini_trim_prompt as trim_prompt,
)
from models.checklist import evaluate_prompt

__all__ = [
    "generate_content",
    "improve_prompt",
    "generate_thoughts",
    "trim_prompt",
    "evaluate_prompt",
]
