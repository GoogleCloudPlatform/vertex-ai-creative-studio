## Lessons Learned & Revised Approach

The initial refactoring steps introduced several bugs (`SyntaxError`, `NameError`) due to faulty `replace` operations. The following lessons have been learned and will be applied to the remainder of this task:

1.  **Verify Before Acting:** Always use `read_file` to get the definitive current state of a file before attempting to modify it. Do not rely on memory or previous context.
2.  **Prefer `write_file` for Complex Changes:** For anything more than a single-line substitution, it is safer to construct the entire corrected file content and use `write_file` to overwrite the file. This avoids complex `old_string` matching and reduces the risk of syntax errors.
3.  **One File at a Time:** The refactoring will proceed strictly one file at a time. A file will be read, modified, and written back before moving to the next file on the checklist.
4.  **Pause for Verification:** As originally planned, I will pause after completing each major section of the checklist (e.g., after all `components` are done) for you to perform manual testing. This is a critical step to catch any errors early.

# Refactoring Plan: Centralize GCS URI to Public URL Conversion

## 1. Analysis

The application currently converts GCS URIs (`gs://...`) to public HTTPS URLs by manually replacing the prefix with a hardcoded string (`https://storage.mtls.cloud.google.com/`) in over 30 different files. This approach is repetitive, error-prone, and difficult to maintain.

A search of the codebase revealed that a central utility function, `gcs_uri_to_https_url`, already exists in `common/utils.py`. However, it was not being used consistently.

This refactoring effort will address these issues by improving the central utility, making it more robust, and replacing all manual string replacements with a call to this single, reliable function.

### Benefits:
- **Centralization:** Logic for GCS URI conversion will exist in a single place.
- **Maintainability:** To change the URL format in the future (e.g., to support different authentication methods), only one function will need to be updated.
- **Robustness:** The new function will gracefully handle `None` values, empty strings, and URLs that are already in HTTPS format.

## 2. Approach

The refactoring will be done in two phases:

**Phase 1: Fix and Improve the Central Utility (Completed)**
1.  The central utility `gcs_uri_to_https_url` in `experiments/veo-app/common/utils.py` has been improved.
2.  A new `https_url_to_gcs_uri` function has been added to handle reverse conversions.

**Phase 2: Refactor All Occurrences**
1.  Go through the checklist below, file by file.
2.  Import the appropriate utility function from `common.utils`.
3.  Replace every manual `.replace("gs://", ...)` call with the utility function.
4.  After each file is refactored, perform the specified validation check.

## 3. Refactoring Checklist

### Models (Completed)

- [x] **File:** `experiments/veo-app/models/veo.py`
- [x] **File:** `experiments/veo-app/models/vto.py`

### Components (Completed)

- [x] **File:** `experiments/veo-app/components/image_thumbnail.py`
- [x] **File:** `experiments/veo-app/components/imagen/image_output.py`
- [x] **File:** `experiments/veo-app/components/library/audio_details.py`
- [x] **File:** `experiments/veo-app/components/library/character_consistency_details.py`
- [x] **File:** `experiments/veo-app/components/library/grid_parts.py`
- [x] **File:** `experiments/veo-app/components/library/image_details.py`
- [x] **File:** `experiments/veo-app/components/library/infinite_scroll_library.js`
- [x] **File:** `experiments/veo-app/components/library/library_image_selector.py`
- [x] **File:** `experiments/veo-app/components/library/video_details.py`
- [x] **File:** `experiments/veo-app/components/library/video_grid_item.py`
- [x] **File:** `experiments/veo-app/components/library/video_infinite_scroll_library.js`
- [x] **File:** `experiments/veo-app/components/veo/video_display.py`

### Pages (Completed)

- [x] **File:** `experiments/veo-app/pages/character_consistency.py`
- [x] **File:** `experiments/veo-app/pages/gemini_image_generation.py`
- [x] **File:** `experiments/veo-app/pages/library.py`
- [x] **File:** `experiments/veo-app/pages/lyria.py`
- [x] **File:** `experiments/veo-app/pages/portraits.py`
- [x] **File:** `experiments/veo-app/pages/recontextualize.py`
- [x] **File:** `experiments/veo-app/pages/veo.py`
- [x] **File:** `experiments/veo-app/pages/vto.py`

### Documentation (Completed)
- [x] **File:** `experiments/veo-app/GEMINI.md`
- [x] **File:** `experiments/veo-app/developers_guide.md`

## 4. Overall Test Plan

After all files in the checklist have been refactored, perform a final end-to-end test pass covering all user journeys that involve displaying media from GCS.

- **Veo Page:** Full image upload -> video generation -> playback loop.
- **Imagen Page:** Full prompt -> image generation -> display loop.
- **Gemini Image Gen Page:** Full image/prompt -> generation -> display loop.
- **VTO Page:** Full person/garment upload -> generation -> display loop.
- **Library:** Open the library, scroll through all media, open the details page for each media type (image, video, audio), and ensure everything loads and plays correctly.