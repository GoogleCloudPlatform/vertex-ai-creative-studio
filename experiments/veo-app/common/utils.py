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
# limitations under the License


def print_keys(obj, prefix=""):
    """Recursively prints keys of a JSON object."""
    if obj is None:  # Base case: if obj is None, do nothing and return
        return
    if isinstance(obj, dict):
        for key in obj:
            print(prefix + key)
            print_keys(obj[key], prefix + "  ")  # Recurse with increased indentation
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            # For lists, we might want to indicate the index and then recurse on the item
            # If the item itself is a complex object.
            # If you only want to print keys of dicts within a list,
            # you might adjust the print statement here or what you pass to print_keys.
            # Current behavior: treats list items as potentially new objects to explore.
            print_keys(item, prefix + f"  [{i}] ")  # indicate list index in prefix
