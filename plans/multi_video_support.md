# Plan: Implementing Multi-Video Support for Veo

## Overview

This document outlines a phased approach to implement support for generating and displaying multiple video outputs from the Veo model. The goal is to enhance the Veo page to handle multiple video results and update the Library to correctly display these multi-video items, creating a consistent user experience.

---

## Phase 1: Backend and Veo Page Core Logic [COMPLETED]

**Objective:** Update the backend to return all generated videos and modify the Veo page's state and event handlers to process this data correctly.

### Task 1.1: Update Backend Function to Return All Videos [COMPLETED]

*   **File Modified:** `experiments/veo-app/models/veo.py`
*   **Implementation Details:** The function's return logic was updated to use a list comprehension to gather all video URIs.

### Task 1.2: Update Veo Page State [COMPLETED]

*   **File Modified:** `experiments/veo-app/state/veo_state.py`
*   **Implementation Note:** The `result_video: str` field was replaced with `result_videos: list[str]` and `selected_video_url: str`.

### Task 1.3: Update Veo Page Event Handlers [COMPLETED]

*   **File Modified:** `experiments/veo-app/pages/veo.py`
*   **Implementation Details:** Event handlers were updated to process a list of URIs and log them correctly to Firestore.

---

## Phase 2: Veo Page UI Implementation [COMPLETED]

**Objective:** Implement the front-end components to display the gallery of generated videos on the Veo page.

### Task 2.1: Implement Gallery UI in `video_display` [COMPLETED]

*   **Files Modified:** `experiments/veo-app/components/veo/video_display.py`, `experiments/veo-app/pages/veo.py`
*   **Implementation Note:** A gallery view with a main player and clickable thumbnails was created.

---

## Phase 3: Library Component Updates [COMPLETED]

**Objective:** Update the Library grid and details view to correctly represent and display multi-video items.

### Task 3.1: Add Multi-Video Badge to Grid Item [COMPLETED]

*   **File Modified:** `experiments/veo-app/components/library/grid_parts.py`
*   **Implementation Details:** A conditional `pill` component was added to show the video count.

### Task 3.2: Implement Gallery in Details View [COMPLETED]

*   **Files Modified:** `experiments/veo-app/pages/library.py`, `experiments/veo-app/components/library/video_details.py`
*   **Implementation Details:** The same gallery view from the Veo page was implemented in the library details dialog.

---

## Phase 4: Component-Based Refactoring & UI Polish [COMPLETED]

**Objective:** Refactor the thumbnail implementation into a dedicated web component to fix layout issues and improve user experience.

### Task 4.1: Create `video_thumbnail` Web Component [COMPLETED]

*   **Files Created:** `experiments/veo-app/components/video_thumbnail/video_thumbnail.py`, `experiments/veo-app/components/video_thumbnail/video_thumbnail.js`
*   **Implementation Details:** A new, reusable web component was built to provide a stable thumbnail with mouse-over autoplay and a selection state.

### Task 4.2: Integrate New Component [COMPLETED]

*   **Files Modified:** `video_display.py`, `video_details.py`, `grid_parts.py`
*   **Implementation Details:** The old thumbnail logic was replaced with the new `video_thumbnail` component.

### Task 4.3: Final Aspect Ratio Polish [COMPLETED]

*   **File Modified:** `experiments/veo-app/components/video_thumbnail/video_thumbnail.js`
*   **Implementation Details:** The component's CSS was changed from `object-fit: contain` to `object-fit: cover` to ensure all thumbnails fill their landscape container, providing a uniform look and feel for the grid and gallery strips.
