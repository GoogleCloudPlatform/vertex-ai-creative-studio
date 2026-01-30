from pydantic import BaseModel, Field, Enum
import uuid


class CriterionRubric(BaseModel, frozen=True):
    """A record for storing a question, its ground truth answer, and justification."""

    guideline_id: str
    criterion_id: str
    question: str
    gt_answer: str
    gt_justification: str


class CriterionVerdict(CriterionRubric, frozen=True):
    """A guideline rubric extended with the model's verdict."""

    verdict: str
    justification: str


class GuidelineVerdict(BaseModel):
    """The verdict for a specific guideline."""

    guideline_id: str
    mean_score: float
    verdicts: list[CriterionVerdict]


class EvaluationResponse(BaseModel, frozen=True):
    asset_path: str = Field(..., description="The GCS path of the evaluated asset")
    asset_url: str = Field(..., description="The URL of the evaluated asset")
    rating: float = Field(..., description="The rating of the asset")
    rationale: str = Field(..., description="The rationale for the rating")
    verdicts: list[GuidelineVerdict] = Field(
        ..., description="The verdicts for all guidelines"
    )

    from pydantic import BaseModel, Field


class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"


class Criterion(BaseModel):
    criterion_id: str = Field(
        default_factory=lambda: f"criterion_{uuid.uuid4().hex[:10]}",
        description="Unique identifier for the criterion",
    )
    name: str
    criterion_value: str
    severity: Severity


class Guideline(BaseModel):
    guideline_id: str = Field(
        default_factory=lambda: f"guideline_{uuid.uuid4().hex[:10]}",
        description="Unique identifier for the guideline",
    )
    name: str
    description: str
    criteria: list[Criterion]


RUBRIC_VALIDATOR_PROMPT = """
# Instructions
Analyze the **Source Images** and the **Generated Asset** below carefully. Your goal is to evaluate the **Generated Asset** against each rubric question. The asset may be an image or a video.
If the asset is an image, **Source Images** is going to be empty and you should apply your evaluation entirely on the **Generated Asset**.
If the asset is a video, know that **Source Images** are what was provided as input to generate the video, so the rubric questions might be assessing elements of the source images, generated video, or both.

For each question, provide a verdict of "Yes", "No", or "N/A" (Not Applicable) and a brief justification for your choice, based on comparing the **Generated Asset** and **Source Images** as described above to the rubrics.

- "Yes" means the **Generated Asset** complies with the question's statement.
- "No" means the **Generated Asset** does not comply.
- "N/A" means the question is not applicable to the asset.
- "Justification" should be a concise explanation (1-2 sentences) of why you chose the verdict.

{rubrics}

# Source Images
{source_images}

# Visual Asset to Evaluate
{response}

# Output Format
Provide your answer for each question in the following format.
<question>
Question: [Question Text]
Verdict: [Yes|No|N/A]
Justification: [Brief explanation for the verdict]
</question>
"""

BAS_RUBRIC_GENERATION_PROMPT = """
Given a brand guideline with multiple criteria and additional free-text guidance, your task is to create a set of precise Yes/No questions to check for compliance. This is for a Brand Alignment Scorecard (BAS).

Generate a list of Yes/No questions based on both the brand criteria and the additional guidance provided.
Crucially, all questions must be phrased so that a "Yes" answer indicates compliance. For example, for a negative rule like "Avoid beaches", the question should be "Is the setting something other than a beach?".
The "answer" for each question must be "yes", as it represents the ground truth for compliance.

Your output must be a JSON object in the exact format shown in the example.

===
**EXAMPLE:**

**Brand Guideline Criteria to Enforce:**
- When a logo is present, it must be clearly visible and unobscured.
- The background should be simple and not distracting.
**Additional Guidance:**
Avoid showing any text other than the brand logo. Do not show the product in a beach setting.

**Answer:**
{{
  "qas": [
    {{
      "criterion_id": "cr-logo-visible",
      "question": "If a logo is present in the image, is it clearly visible and unobscured?",
      "justification": "This is a requirement from the brand guidelines. An image without a logo is not in violation, but if a logo exists, it must be visible.",
      "answer": "yes"
    }},
    {{
      "criterion_id": "cr-background-style",
      "question": "Is the background simple and not distracting?",
      "justification": "This is a requirement from the brand guidelines.",
      "answer": "yes"
    }},
    {{
      "criterion_id": "additional-guidance-text",
      "question": "Is the image free of any text other than the official brand logo?",
      "justification": "This is a requirement from the additional guidance. 'Yes' indicates compliance.",
      "answer": "yes"
    }},
    {{
      "criterion_id": "additional-guidance-setting",
      "question": "Is the product shown in a setting other than a beach?",
      "justification": "This is a requirement from the additional guidance. 'Yes' indicates compliance.",
      "answer": "yes"
    }}
  ]
}}
===

**BRAND GUIDELINE CRITERIA TO ENFORCE:**
{criteria}

**ADDITIONAL GUIDANCE (e.g., negative prompts):**
{additional_guidance}

**Answer:**
"""


DSG_RUBRIC_GENERATION_PROMPT = """
You are an expert quality assurance tester for AI-generated media.
Given a source prompt, your task is to create a set of precise Yes/No questions to check for two things:
1.  **Prompt Fidelity (DSG):** Is each key component of the source prompt present in the asset? This is for a Davidsonian Scene Graph (DSG) analysis.
2.  **General Quality (GQM):** Is the asset technically and aesthetically well-made, and free of common AI mistakes? This is for a General Quality & Mistakes (GQM) evaluation.

**Instructions:**

**Part 1: Prompt Fidelity Questions (DSG)**
- Analyze the source prompt and break it down into its key components.
- In the JSON output, create a "keywords" string where each component is enclosed in numbered brackets, like `{{1}}[component]`.
- Generate multiple Yes/No questions for each identified component.

**Part 2: General Quality Questions (GQM)**
- Generate additional Yes/No questions that address the following general quality dimensions:
  - **Object Permanence & Consistency:** Do objects or characters maintain a consistent appearance?
  - **Plausibility & Realism:** Do interactions like lighting and shadows appear natural?
  - **Aesthetic Quality:** Is the asset free of obvious visual glitches, artifacts, or excessive blur?
  - **Natural Movement (for video):** Is movement fluid and not distorted?

**Formatting Rules:**
- All questions must be phrased so that a "Yes" answer indicates compliance or high quality.
- The "answer" for all questions must be "yes" as this reflects the ground truth of what was requested in the prompt and the expected level of quality.
- Your output must be a single JSON object in the exact format shown in the example.

===
**EXAMPLE:**

**Source Prompt:** A close-up of a luxurious gold watch with a leather strap on a man's wrist.

**Answer:**
{{
  "keywords": "A {{1}}[close-up] of a {{2}}[luxurious] {{3}}[gold] watch with a {{4}}[leather strap] on a {{5}}[man's wrist].",
  "qas": [
    {{
      "criterion_id": "prompt-component-1",
      "question": "Is the image a close-up shot?",
      "justification": "DSG: The source prompt explicitly states a 'close-up' ({{1}}).",
      "answer": "yes"
    }},
    {{
      "criterion_id": "prompt-component-3",
      "question": "Is the watch case made of gold?",
      "justification": "DSG: The source prompt explicitly states the watch is 'gold' ({{3}}).",
      "answer": "yes"
    }},
    {{
      "criterion_id": "prompt-component-5",
      "question": "Is the watch displayed on a man's wrist?",
      "justification": "DSG: The source prompt specifies a 'man's wrist' ({{5}}).",
      "answer": "yes"
    }},
    {{
      "criterion_id": "gqm-artifacts",
      "question": "Is the image free of noticeable visual artifacts, distortions, or glitches?",
      "justification": "GQM: Checks for general aesthetic quality and common AI generation errors.",
      "answer": "yes"
    }},
    {{
      "criterion_id": "gqm-lighting",
      "question": "Are the lighting and shadows on the watch and wrist plausible and consistent?",
      "justification": "GQM: Checks for physical realism and plausibility.",
      "answer": "yes"
    }}
  ]
}}
===

**Source Prompt:**
{source_prompt}

**Answer:**
"""
