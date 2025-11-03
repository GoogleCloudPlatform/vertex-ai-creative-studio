# Plan: Refactoring Temperature Settings for Character Consistency

This document provides an analysis of the hardcoded `temperature` parameters within the Character Consistency workflow and outlines a plan to refactor them for better maintainability and tunability.

### 1. Analysis of Temperature Parameters

The `temperature` parameter controls the randomness of a generative model's output. A low temperature is deterministic and focused, while a high temperature is more creative.

There are three instances of this parameter in `models/gemini.py` that directly impact the Character Consistency workflow:

1.  **`get_facial_composite_profile` -> `temperature=0.1`**
    *   **Purpose:** Performs a "forensic analysis" of a face and must output a perfectly structured JSON object.
    *   **Impact:** The low temperature is **critical**. It forces the model to be highly factual and stick rigidly to the required JSON schema. A higher value would risk malformed JSON, breaking the workflow.

2.  **`get_natural_language_description` -> `temperature=0.1`**
    *   **Purpose:** Translates the factual JSON profile into a concise, natural-language paragraph.
    *   **Impact:** The low temperature is **highly appropriate**. The goal is a direct, faithful translation of the data, not a creative interpretation.

3.  **`generate_final_scene_prompt` -> `temperature=0.3`**
    *   **Purpose:** Creatively elaborates on the character description and user's scene to produce a rich, cinematic prompt for Imagen.
    *   **Impact:** The slightly higher temperature is **intentional and desirable**. It encourages the model to add creative details like camera angles and lighting without straying too far from the core request.

4.  **`select_best_image` -> `temperature=0.2`**
    *   **Purpose:** Acts as a judge, comparing generated images to the originals and returning a structured JSON object with its choice.
    *   **Impact:** The low temperature is **very important**. It ensures the model performs a focused, analytical comparison and guarantees the JSON output is valid.

### 2. Recommended Changes: A Hybrid Approach

Hardcoding these values is not ideal. The recommended solution is to move them to the configuration file with highly descriptive names and comments. This provides tunability for advanced users while documenting the purpose of each setting for future developers.

### 3. Detailed Plan & Task List

**A. The Plan**

1.  **Centralize Parameters:** Move the three temperature values to the `Default` dataclass in `config/default.py`.
2.  **Use Descriptive Naming:** Name the new variables to clearly reflect their purpose (e.g., `TEMP_FORENSIC_ANALYSIS`).
3.  **Add Explanatory Comments:** Add comments in the config file explaining what each temperature controls.
4.  **Refactor Model:** Update the functions in `models/gemini.py` to read these values from the configuration object.

**B. Detailed Task List**

1.  **Modify `config/default.py`:**
    *   Add the following new fields to the `Default` dataclass:
        ```python
        # Temperatures for Character Consistency Workflow
        # Low temp for factual, structured output. Increasing may break JSON parsing.
        TEMP_FORENSIC_ANALYSIS: float = 0.1
        # Low temp for direct, non-creative translation of data to text.
        TEMP_DESCRIPTION_TRANSLATION: float = 0.1
        # Mid-range temp for creative but controlled prompt engineering.
        TEMP_SCENE_GENERATION: float = 0.3
        # Low temp for analytical comparison and structured JSON output.
        TEMP_BEST_IMAGE_SELECTION: float = 0.2
        ```

2.  **Modify `models/gemini.py`:**
    *   In `get_facial_composite_profile`, change `temperature=0.1` to `temperature=cfg.TEMP_FORENSIC_ANALYSIS`.
    *   In `get_natural_language_description`, change `temperature=0.1` to `temperature=cfg.TEMP_DESCRIPTION_TRANSLATION`.
    *   In `generate_final_scene_prompt`, change `temperature=0.3` to `temperature=cfg.TEMP_SCENE_GENERATION`.
    *   In `select_best_image`, change `temperature=0.2` to `temperature=cfg.TEMP_BEST_IMAGE_SELECTION`.

### 4. Validation and Testing Plan

**A. Functional Test**

1.  **Test:** After the changes are made, perform one full, end-to-end run of the Character Consistency workflow.
2.  **Expected Outcome:** The output quality should be identical to the previous successful run, confirming the refactoring was successful.

**B. Regression Risk Analysis**

*   **Risk Level:** **Very Low.**
*   **Justification:** This refactoring only changes the *location* from which the temperature values are read. It does not alter the values themselves or the workflow logic. The most likely failure mode is an immediate `AttributeError` if a variable is misspelled, which is easy to detect and fix. There is no expected impact on other application pages.
