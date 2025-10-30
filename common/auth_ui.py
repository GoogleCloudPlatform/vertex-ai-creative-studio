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

"""Helper functions for authentication UI components."""

from config.default import Default

def should_show_logout_button() -> bool:
    """Check if logout button should be shown based on configuration."""
    cfg = Default()
    return cfg.SIMPLE_AUTH_ENABLED

def get_auth_header_props() -> dict:
    """Get header properties with authentication context."""
    return {
        "show_logout_button": should_show_logout_button()
    }