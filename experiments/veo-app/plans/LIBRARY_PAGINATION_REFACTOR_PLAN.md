# Library Pagination Refactor Plan

This document outlines the long-term architectural changes required to fix pagination issues in the Library page.

## Problem Summary

The current library implementation suffers from two major issues:
1.  **`list index out of range` errors:** The application crashes when trying to access pages of data that don't exist in its in-memory list.
2.  **Inaccurate Pagination:** The total number of pages is calculated incorrectly, and users can get "stuck" on a page with no way to proceed.

The root cause is that the application performs **client-side pagination** on a limited subset of data (the last 1000 items) fetched from Firestore, rather than performing true **server-side pagination**.

## Proposed Solution: Server-Side Pagination

To solve this robustly, the pagination logic must be moved from the Python client code to the Firestore query itself. This involves two major changes.

### 1. Implement Cursor-Based Pagination

The `get_media_for_page` function in `common/metadata.py` must be refactored.

-   **Current State:** It fetches a large, fixed number of items and then slices the list in Python.
-   **Future State:** It should accept a Firestore `DocumentSnapshot` as a "cursor" (or page token). The Firestore query will use this cursor with the `start_after()` method to fetch the next batch of documents directly from the server. This is the standard and scalable way to implement pagination in Firestore.

This change will require modifications to the `PageState` in `pages/library.py` to store the cursor for the next and previous pages.

### 2. Solve the "Total Page Count" Issue

True server-side pagination makes it difficult to get the total count of items that match a filter without reading all the documents, which is slow and expensive. There are two viable options:

#### Option A: Remove the Total Count (Simpler)

-   **Implementation:** Remove the "Page X of Y" text from the UI. The "Next" button's state would be determined by the number of results in the current fetch. If the query for 9 items returns less than 9, we are on the last page, and the "Next" button is disabled.
-   **Pros:** Easier to implement, avoids costly count operations.
-   **Cons:** Degrades user experience slightly as the user doesn't know how many total pages exist.

#### Option B: Implement Distributed Counters (More Complex)

-   **Implementation:** Create a separate document in Firestore (e.g., in a `stats` collection) to hold the total count of media items. This counter would be updated using a Cloud Function that triggers whenever a new media item is created or deleted. For filtered counts, a more complex system of counters would be needed.
-   **Pros:** Provides an accurate total count, offering the best user experience.
-   **Cons:** Significantly more complex to implement and maintain. It requires setting up Cloud Functions and ensuring the counters are always in sync with the data.

## Implementation Steps

1.  **Refactor `get_media_for_page`:**
    -   Modify its signature to accept an optional page cursor.
    -   Change the query logic to use `start_after(cursor)`.
    -   Remove the client-side list slicing.
2.  **Update `pages/library.py` State:**
    -   Modify `PageState` to store the cursor for the last document of the currently displayed page.
3.  **Update Library UI Logic:**
    -   The "Next" and "Previous" buttons in `handle_page_change` will now pass the stored cursor to the data fetching function.
    -   Implement either Option A or B for handling the total page count and "Next" button state.
4.  **Test Thoroughly:** Since `common/metadata.py` is a shared module, all other pages that use `get_media_for_page` must be tested to ensure they are not broken by this change.

This refactor is a significant but necessary step to create a scalable and bug-free library experience.

## Specific Test Cases for Verification

After implementing the refactor, the following specific scenario, which previously caused bugs, must be tested to verify the fix:

1.  **"Stuck on Backwards Pagination" Test:**
    -   Navigate several pages forward into the library results (e.g., to page 5).
    -   From that page, open the details dialog for an item, then close it.
    -   Navigate backwards page by page.
    -   **Expected Result:** The user should be able to paginate all the way back to page 1 without getting stuck. The "Previous" button should function correctly on every page.