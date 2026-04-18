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
from unittest.mock import MagicMock
from services.trimmer import PromptTrimmer
from services.improver import PromptImprover
from services.checklist import PromptChecklist
from models.domain import TrimResult, ImprovementResult
from google.genai.types import GenerateContentResponse, Candidate, Content, Part

@pytest.fixture
def mock_client():
    client = MagicMock()
    return client

def test_trimmer_service(mock_client):
    # Mock responses for deconstruct and rewrite
    mock_response_1 = MagicMock(spec=GenerateContentResponse)
    mock_response_1.text = "<PromptStructureAnalysis><TaskSpecificRequirements>reqs</TaskSpecificRequirements><GeneralRulesAndBestPractices>rules</GeneralRulesAndBestPractices></PromptStructureAnalysis>"
    
    mock_response_2 = MagicMock(spec=GenerateContentResponse)
    mock_response_2.text = "Trimmed prompt"

    mock_client.generate_content.side_effect = [mock_response_1, mock_response_2]

    trimmer = PromptTrimmer(client=mock_client)
    result = trimmer.trim_prompt("original prompt")

    assert isinstance(result, TrimResult)
    assert result.original_prompt == "original prompt"
    assert result.trimmed_prompt == "Trimmed prompt"
    assert result.analysis_xml == mock_response_1.text
    assert mock_client.generate_content.call_count == 2

def test_improver_service_run(mock_client):
    # Mock responses for plan and improve
    mock_response_plan = MagicMock(spec=GenerateContentResponse)
    mock_candidate = MagicMock(spec=Candidate)
    mock_content = MagicMock(spec=Content)
    mock_part = MagicMock(spec=Part)
    mock_part.text = "The Plan"
    mock_content.parts = [mock_part]
    mock_candidate.content = mock_content
    mock_response_plan.candidates = [mock_candidate]

    mock_response_improve = MagicMock(spec=GenerateContentResponse)
    mock_response_improve.text = "Improved Prompt"

    mock_client.generate_content.side_effect = [mock_response_plan, mock_response_improve]

    improver = PromptImprover(client=mock_client)
    result = improver.run(system_prompt="sys", prompt="orig", instructions="instr")

    assert isinstance(result, ImprovementResult)
    assert result.plan.generated_plan == "The Plan"
    assert result.improved_prompt == "Improved Prompt"
    assert mock_client.generate_content.call_count == 2

def test_checklist_service(mock_client):
    # Mock response for checklist
    mock_response = MagicMock(spec=GenerateContentResponse)
    # Minimal valid markdown for parsing logic (assuming parsers.py logic)
    # We just want to ensure the service calls the client and returns something.
    mock_response.text = "# Prompt Health Checklist\n\n## Clarity\n**Score:** 5/5\n**Explanation:** Good."
    mock_client.generate_content.return_value = mock_response

    checklist = PromptChecklist(client=mock_client)
    structured, raw = checklist.evaluate_prompt("prompt")

    assert raw == mock_response.text
    assert mock_client.generate_content.call_count == 1
