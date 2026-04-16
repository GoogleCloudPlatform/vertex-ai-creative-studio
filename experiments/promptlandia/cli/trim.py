#!/usr/bin/env python3
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

"""CLI script to trim prompts using the Promptlandia logic."""

import argparse
import sys
import os

# Add the project root to the python path so we can import from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.trimmer import PromptTrimmer
from cli.common import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Trim a prompt by removing general best practices while keeping task-specific requirements."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt to trim. If not provided, reads from stdin.",
    )
    parser.add_argument(
        "-f", "--file", help="Read the prompt from a specific file."
    )
    parser.add_argument(
        "--show-analysis",
        action="store_true",
        help="Output the analysis XML to stderr.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging."
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Determine input source
    prompt = ""
    if args.prompt:
        prompt = args.prompt
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                prompt = f.read()
        except Exception as e:
            sys.stderr.write(f"Error reading file {args.file}: {e}\n")
            sys.exit(1)
    elif not sys.stdin.isatty():
        # Read from piped stdin
        prompt = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    if not prompt.strip():
        sys.stderr.write("Error: Empty prompt provided.\n")
        sys.exit(1)

    try:
        trimmer = PromptTrimmer()
        result = trimmer.trim_prompt(prompt)

        if args.show_analysis:
            sys.stderr.write("--- Analysis ---\\n")
            sys.stderr.write(result.analysis_xml)
            sys.stderr.write("\n----------------\n")

        # Print the final trimmed prompt to stdout
        print(result.trimmed_prompt)

    except Exception as e:
        sys.stderr.write(f"Error during trimming: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
