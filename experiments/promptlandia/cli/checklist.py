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

"""CLI script to evaluate prompts against the health checklist."""

import argparse
import sys
import os

# Add the project root to the python path so we can import from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.checklist import PromptChecklist
from models.checklist_models import IssueDetail
from cli.common import setup_logging


def print_results(response):
    """Prints the checklist results to stdout in a human-readable format."""
    categories_with_issues = {}
    categories_without_issues = {}

    for name, data in response.categories.items():
        if any(score for score in data.items.values()):
            categories_with_issues[name] = data
        else:
            categories_without_issues[name] = data

    # Print issues first
    if categories_with_issues:
        print(f"\nFound {len(categories_with_issues)} categories with issues:\n")
        for category_name, category_data in categories_with_issues.items():
            print(f"--- {category_name.replace('_', ' ').title()} ---")
            for item_name, score in category_data.items.items():
                status = "[FAIL]" if score else "[PASS]"
                print(f"{status} {item_name.replace('_', ' ').title()}")

                if score and category_data.details and item_name in category_data.details:
                    detail = category_data.details[item_name]
                    if isinstance(detail, IssueDetail):
                        print(f"    Issue: {detail.issue_name}")
                        print(f"    Location: {detail.location_in_prompt}")
                        print(f"    Rationale: {detail.rationale}")
                    else:
                        print(f"    Details: {detail}")
            
            if category_data.explanation:
                 print(f"\n    Category Explanation: {category_data.explanation}")
            print()

    # Print passes
    if categories_without_issues:
        print("\nThe following checks passed without issues:\n")
        for category_name in categories_without_issues:
             print(f"[PASS] {category_name.replace('_', ' ').title()}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a prompt against a health checklist of best practices."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt to evaluate. If not provided, reads from stdin.",
    )
    parser.add_argument(
        "-f", "--file", help="Read the prompt from a specific file."
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output the raw markdown response from the model.",
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
        if args.verbose:
            sys.stderr.write("Evaluating prompt...\n")

        checklist_service = PromptChecklist()
        structured_response, raw_text = checklist_service.evaluate_prompt(prompt)

        if args.raw:
            print(raw_text)
        elif structured_response:
            print_results(structured_response)
        else:
            sys.stderr.write("Could not parse structured response. Showing raw output:\n")
            print(raw_text)

    except Exception as e:
        sys.stderr.write(f"Error during prompt evaluation: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()