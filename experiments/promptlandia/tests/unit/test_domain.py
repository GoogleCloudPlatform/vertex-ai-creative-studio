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

import pytest
from pydantic import ValidationError
from models.domain import TrimResult, ImprovementPlan, ImprovementResult

def test_trim_result_validation():
    # Valid case
    result = TrimResult(
        original_prompt="test",
        trimmed_prompt="test",
        analysis_xml="<xml></xml>",
        duration_seconds=1.0
    )
    assert result.original_prompt == "test"

    # Invalid case (missing field)
    with pytest.raises(ValidationError):
        TrimResult(original_prompt="test")

def test_improvement_plan_validation():
    # Valid case
    plan = ImprovementPlan(
        original_prompt="orig",
        instructions="instr",
        generated_plan="plan"
    )
    assert plan.system_prompt == "" # Default value
    assert plan.original_prompt == "orig"

    # Invalid case
    with pytest.raises(ValidationError):
        ImprovementPlan(original_prompt="orig")

def test_improvement_result_validation():
    plan = ImprovementPlan(
        original_prompt="orig",
        instructions="instr",
        generated_plan="plan"
    )
    # Valid case
    result = ImprovementResult(
        plan=plan,
        improved_prompt="improved"
    )
    assert result.plan.original_prompt == "orig"
    assert result.improved_prompt == "improved"

    # Invalid case
    with pytest.raises(ValidationError):
        ImprovementResult(improved_prompt="improved")
