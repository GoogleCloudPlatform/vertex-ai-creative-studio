# Plan: Infinite Scroll Library Chooser via Lit Web Component

This document outlines the plan to create a new library chooser component that uses an infinite scroll mechanism. This will be implemented as a Lit-based Web Component in parallel with the existing chooser to de-risk development.

**Status: Completed**

## 1. High-Level Analysis and Strategy

The goal is to build a component that can detect when a user scrolls to the bottom of the image list and then request more data from the backend. This provides a seamless browsing experience for large libraries.

-   **Why a Web Component?** Mesop's standard components do not expose low-level browser scroll events. A Web Component is the standard and recommended pattern for bridging this gap, allowing us to write custom JavaScript for the scroll detection while keeping the data logic in Python.

-   **Technology:** We will use **Lit** to build the Web Component, as it is lightweight and integrates well with Mesop.

-   **Parallel Implementation:** To avoid regressions, we will create a completely new set of components and a dedicated test page. The existing components will not be modified.
    -   **New Chooser Button:** `components/library/infinite_scroll_chooser_button.py`
    -   **New Mesop Wrapper:** `components/library/infinite_scroll_library.py`
    -   **New Lit Component:** `components/library/infinite_scroll_library.js`
    -   **New Test Page:** `pages/test_infinite_scroll.py`

## 2. Detailed Component Design

### A. The Lit Component: `components/library/infinite_scroll_library.js`

This is the frontend component that handles the UI and user interaction.

-   **Responsibilities:**
    1.  Accept a list of image items (`items`) and a boolean flag (`hasMoreItems`) as properties from the Mesop backend.
    2.  Render the items in a scrollable grid.
    3.  Attach a `scroll` event listener to the grid container.
    4.  When the user scrolls near the bottom, dispatch a `CustomEvent` named **`load-more`** to notify the Python backend to fetch more data.
    5.  When a user clicks an image, dispatch a `CustomEvent` named **`image-selected`** containing the image's GCS URI.

### B. The Mesop Wrapper: `components/library/infinite_scroll_library.py`

This Python file acts as the bridge between the Lit component and the Mesop application.

-   **Responsibilities:**
    1.  Define a `WebComponent` class that maps to our new `<infinite-scroll-library>` HTML tag.
    2.  Specify the component's properties (`items`, `has_more_items`).
    3.  Define the custom events it will listen for (`on_load_more`, `on_image_selected`).

### C. The New Chooser Button: `components/library/infinite_scroll_chooser_button.py`

This is the main, user-facing Python component that orchestrates the feature.

-   **Responsibilities:**
    1.  Manage the state for the dialog, including `media_items`, `current_page`, and `has_more_items`.
    2.  When the dialog is opened, fetch the initial (first) page of data.
    3.  Define an event handler for the `on_load_more` event. This handler will increment the page counter, fetch the next page of data, and append the new items to the `media_items` list.
    4.  Define an event handler for the `on_image_selected` event to pass the selection up to the parent page.
    5.  Render the `InfiniteScrollLibrary` Web Component inside a dialog, passing the current state down as properties.

## 3. Data Fetching Modifications

The existing `get_media_for_page` function in `common/metadata.py` is already suitable for this task as it supports pagination via a `page` number. No modifications to this function are required for the initial implementation.

## 4. Testing Plan

1.  **Create New Test Page:** Copy `pages/test_uploader.py` to a new file, `pages/test_infinite_scroll.py`.
2.  **Modify Test Page:** Update the new test page to import and render the new `infinite_scroll_chooser_button`.
3.  **Manual Test Cases:**
    -   Navigate to the new `/test_infinite_scroll` page.
    -   Click the new chooser button.
    -   **Verify:** The first page of images loads and is displayed.
    -   Scroll to the bottom of the list.
    -   **Verify:** A loading indicator appears, and the next page of images is appended to the list.
    -   Repeat scrolling until all images are loaded.
    -   **Verify:** The loading indicator no longer appears once the end of the library is reached.
    -   Click on an image from any page in the list.
    -   **Verify:** The dialog closes, and the correct image URI is successfully received by the test page.
