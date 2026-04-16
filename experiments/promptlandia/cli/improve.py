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

"""CLI script to improve prompts using the Promptlandia logic."""

import argparse
import sys
import os

# Add the project root to the python path so we can import from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.improver import PromptImprover
from cli.common import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Improve a prompt based on specific instructions."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt to improve. If not provided, reads from stdin.",
    )
    parser.add_argument(
        "-f", "--file", help="Read the prompt from a specific file."
    )
    parser.add_argument(
        "-i",
        "--instructions",
        required=True,
        help="Instructions on how to improve the prompt.",
    )
    parser.add_argument(
        "-s", "--system-prompt", default="", help="Optional system prompt."
    )
    parser.add_argument(
        "--show-plan",
        action="store_true",
        help="Output the improvement plan to stderr.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging."
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Determine input source for the main prompt
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
        improver = PromptImprover()

        # Step 1: Generate Plan
        if args.verbose:
            sys.stderr.write("Generating improvement plan...\n")
        
        plan_object = improver.generate_plan(
            system_prompt=args.system_prompt,
            prompt=prompt,
            instructions=args.instructions,
        )

        if args.show_plan:
            sys.stderr.write("--- Improvement Plan ---\n")
            sys.stderr.write(plan_object.generated_plan)
            sys.stderr.write("\n------------------------\n")

        # Step 2: Improve Prompt
        if args.verbose:
            sys.stderr.write("Improving prompt based on plan...\n")

        result = improver.improve_prompt(plan=plan_object)

        # Print the final improved prompt to stdout
        print(result.improved_prompt)

    except Exception as e:
        sys.stderr.write(f"Error during prompt improvement: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
