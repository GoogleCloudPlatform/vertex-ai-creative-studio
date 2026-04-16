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

"""This module provides functions for interacting with the Gemini model.

It includes functions for generating content, improving prompts, and generating
thoughts for prompt improvement. It also uses the `tenacity` library to
provide automatic retries with exponential backoff for the Gemini API calls,
which makes the application more resilient to transient errors.
"""

import base64
import logging
import re
import time
from typing import Any
from google.genai.types import (
    GenerateContentConfig,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from models.model_setup import ModelSetup
from models.domain import TrimResult, ImprovementPlan, ImprovementResult

from models.prompts import (
    PROMPT_IMPROVEMENT_INSTRUCTIONS,
    PROMPT_IMPROVEMENT_PLANNING_INSTRUCTIONS,
    TRIMMER_DECONSTRUCTOR,
    TRIMMER_REWRITER,
)

logger = logging.getLogger(__name__)

client, model_id, planning_model_id = ModelSetup.init()
MODEL_ID = model_id
PLANNING_MODEL_ID = planning_model_id


def _log_non_text_parts(response):
    """Logs any non-text parts (like thoughts) found in the Gemini response."""
    try:
        if not response.candidates:
            return
        for i, candidate in enumerate(response.candidates):
            if not candidate.content or not candidate.content.parts:
                continue
            for j, part in enumerate(candidate.content.parts):
                # Check for known non-text attributes that might be interesting
                if hasattr(part, "thought") and part.thought:
                    logger.info(
                        f"Response Candidate {i}, Part {j} [THOUGHT]: {part.thought}"
                    )
                elif hasattr(part, "thought_signature") and part.thought_signature:
                    signature = part.thought_signature
                    if isinstance(signature, bytes):
                        signature = base64.b64encode(signature).decode("utf-8")
                    logger.info(
                        f"Response Candidate {i}, Part {j} [THOUGHT_SIGNATURE]: {signature[:100]}..."
                    )
                elif not part.text:
                    # Fallback for other non-text parts (function calls, etc.)
                    logger.info(f"Response Candidate {i}, Part {j} [NON-TEXT]: {part}")
    except Exception as e:
        logger.warning(f"Error logging non-text parts: {e}")


@retry(
    wait=wait_exponential(
        multiplier=1, min=1, max=10
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions
    reraise=True,  # re-raise the last exception if all retries fail
)
def _call_gemini_with_retry(
    model: str, contents: str, config: GenerateContentConfig, log_success_msg: str
) -> Any:
    """
    Helper function to call Gemini with retry logic and standard logging.
    """
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        _log_non_text_parts(response)
        logger.info(f"{log_success_msg}: {response.text[:100]}...")
        return response
    except Exception as e:
        logger.error(f"Error during Gemini call ({log_success_msg}): {e}")
        raise


def gemini_generate_content(system_prompt: str = "", prompt: str = "") -> str:
    """Invokes the Gemini model to generate content.

    This function sends a prompt to the Gemini model and returns the generated
    content. It can also accept an optional system prompt to guide the model's
    behavior.

    Args:
        system_prompt: An optional system prompt to guide the model.
        prompt: The main prompt to send to the model.

    Returns:
        The generated content as a string.
    """
    response = _call_gemini_with_retry(
        model=MODEL_ID,
        contents=prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_modalities=["TEXT"],
        ),
        log_success_msg="Gemini content generation successful",
    )
    return response.text


def gemini_improve_this_prompt(plan: ImprovementPlan) -> ImprovementResult:
    """Improves a prompt using the Gemini model based on a generated plan.

    Args:
        plan: The ImprovementPlan object containing the original prompt, instructions, and the generated plan.

    Returns:
        An ImprovementResult object containing the plan and the improved prompt.
    """

    improvement_prompt = PROMPT_IMPROVEMENT_INSTRUCTIONS.format(
        plan.generated_plan,
        f"{plan.system_prompt} {plan.original_prompt}",
        plan.instructions,
    )

    response = _call_gemini_with_retry(
        model=MODEL_ID,
        contents=improvement_prompt,
        config=GenerateContentConfig(
            response_modalities=["TEXT"],
        ),
        log_success_msg="Gemini prompt improvement successful",
    )
    
    return ImprovementResult(
        plan=plan,
        improved_prompt=response.text
    )


def gemini_thinking_thoughts(
    system_prompt: str = "", prompt: str = "", prompt_improvement_instructions: str = ""
) -> ImprovementPlan:
    """Generates a plan for improving a prompt using the Gemini model.

    Args:
        system_prompt: An optional system_prompt to guide the model.
        prompt: The prompt to improve.
        prompt_improvement_instructions: Instructions for the improvement.

    Returns:
        An ImprovementPlan object containing the inputs and the generated plan.
    """

    planning_prompt = PROMPT_IMPROVEMENT_PLANNING_INSTRUCTIONS.format(
        f"{system_prompt} {prompt}",
        prompt_improvement_instructions,
    )

    response = _call_gemini_with_retry(
        model=PLANNING_MODEL_ID,
        contents=planning_prompt,
        config=GenerateContentConfig(
            response_modalities=["TEXT"],
        ),
        log_success_msg="Gemini thinking thoughts successful",
    )
    
    generated_plan_text = response.candidates[0].content.parts[0].text
    
    return ImprovementPlan(
        original_prompt=prompt,
        system_prompt=system_prompt,
        instructions=prompt_improvement_instructions,
        generated_plan=generated_plan_text
    )


def gemini_trim_prompt(prompt: str) -> TrimResult:
    """Trims a prompt by removing general best practices while keeping task-specific requirements.

    This is a two-step process:
    1. Deconstruct the prompt to identify what is essential vs general.
    2. Rewrite the prompt using only the essential parts.

    Args:
        prompt: The user's original prompt.

    Returns:
        A TrimResult object containing the analysis, trimmed prompt, and duration.
    """
    logger.info(f"Trimming prompt using model: {MODEL_ID}")
    start_time = time.perf_counter()

    # Step 1: Deconstruct
    deconstructor_prompt = TRIMMER_DECONSTRUCTOR.format(prompt)
    response_1 = _call_gemini_with_retry(
        model=MODEL_ID,
        contents=deconstructor_prompt,
        config=GenerateContentConfig(
            response_modalities=["TEXT"],
        ),
        log_success_msg="Step 1 (Deconstruction) complete",
    )
    analysis_xml = response_1.text

    # Parse XML to extract requirements and general rules
    tsr_match = re.search(
        r"<TaskSpecificRequirements>(.*?)</TaskSpecificRequirements>",
        analysis_xml,
        re.DOTALL,
    )
    grbp_match = re.search(
        r"<GeneralRulesAndBestPractices>(.*?)</GeneralRulesAndBestPractices>",
        analysis_xml,
        re.DOTALL,
    )

    tsr = tsr_match.group(1).strip() if tsr_match else ""
    grbp = grbp_match.group(1).strip() if grbp_match else ""

    # Step 2: Rewrite
    rewriter_prompt = TRIMMER_REWRITER.format(prompt, tsr, grbp)
    response_2 = _call_gemini_with_retry(
        model=MODEL_ID,
        contents=rewriter_prompt,
        config=GenerateContentConfig(
            response_modalities=["TEXT"],
        ),
        log_success_msg="Step 2 (Rewriting) complete",
    )
    final_trimmed_prompt = response_2.text
    
    end_time = time.perf_counter()

    return TrimResult(
        original_prompt=prompt,
        trimmed_prompt=final_trimmed_prompt,
        analysis_xml=analysis_xml,
        duration_seconds=end_time - start_time
    )
