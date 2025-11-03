# Plan: Move Presets to Firestore with Local Fallback and Override

**Author:** Gemini
**Date:** 2025-09-15
**Status:** Tabled

## 1. Overview

This plan details the process for refactoring the application's preset management system. The goal is to move the presets from a static Python file (`config/banana_presets.py`) to a dynamic Firestore collection, enabling easier updates and future user contributions.

The core strategy is a hybrid approach where presets fetched from Firestore override the local, default presets defined in the code.

## 2. Implementation Stages

### Stage 1: Define Schema & Seed Data

- **New Firestore Collection:** Create a new collection named `genmedia-presets`.
- **Document Schema:** Each document will represent one preset with the following fields:
  - `key` (string, e.g., "labubu")
  - `label` (string, e.g., "1/7th figurine")
  - `prompt` (string)
  - `references` (array of strings, GCS URIs)
  - `category` (string, e.g., "creative")
  - `application` (string, e.g., "gemini_image_generation")
- **Seeding Script:** Create a one-time seeding script (`scripts/seed_presets.py`) to read the existing presets from `config/banana_presets.py` and populate the `genmedia-presets` collection in Firestore.

### Stage 2: Create Reusable Preset Loading Module

- **New File:** Create a new module at `experiments/veo-app/common/presets.py`.
- **New Function:** Implement a function `load_and_merge_presets(application: str)` within this module.
- **Function Logic:**
  1.  **Load Local:** Start by loading the default presets from `config/banana_presets.py`.
  2.  **Fetch Firestore:** In a `try...except` block, query the `genmedia-presets` collection for all documents where `application` matches the input parameter. If this fails, log an error and return only the local presets.
  3.  **Merge with Override:** If Firestore data is retrieved, merge it with the local data. If a preset `key` exists in both sources, the version from Firestore will take precedence.
  4.  **Restructure Data:** Transform the final list of presets into the nested dictionary format (grouped by `category`) that the UI expects.
  5.  **Return:** Return the final, merged data structure.

### Stage 3: Integrate into Application Pages

- **Target File:** Initially, `experiments/veo-app/pages/gemini_image_generation.py`.
- **Modification:**
  - Replace the static import: `from config.banana_presets import IMAGE_ACTION_PRESETS`.
  - Add a new call to the preset loading function:
    ```python
    from common.presets import load_and_merge_presets
    IMAGE_ACTION_PRESETS = load_and_merge_presets("gemini_image_generation")
    ```
- **Result:** The rest of the page will function as before, as it receives data in the expected format. This pattern can be reused for any other page that needs presets.

## 3. Future Considerations

- This new `common/presets.py` module provides a centralized place to manage preset logic, which will be useful for reconciling other preset-like collections (`genmedia-vto-catalog`, etc.) in the future.
