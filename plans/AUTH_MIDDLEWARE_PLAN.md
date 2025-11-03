# Plan: Implement Authentication via FastAPI Redirect and Firestore-Backed Sessions

### **Objective**

To resolve a critical data integrity issue where a user's identity can be missed if they navigate directly to a deep-linked page (e.g., `/veo`, `/library`). This plan outlines the implementation of a centralized authentication and session management system using a FastAPI redirect handler. This approach correctly bridges the context gap between FastAPI and Mesop, ensuring every request is authenticated and associated with a persistent session stored in Firestore.

This enhanced approach replaces the previous, brittle method of performing authentication on a single page, making the application secure, robust, and stateful.

---

### **Implementation Details**

The final implementation uses a redirect-based pattern to handle authentication and session creation within the FastAPI context before handing off to the Mesop application.

**1. Centralized Auth Endpoint (`/__/auth/`)**

*   **Action:** A FastAPI route at `/__/auth/` was created in `main.py` to act as the central authentication processor.
*   **Implementation:**
    *   The root path `/` redirects all incoming traffic to `/__/auth/`.
    *   This endpoint reads the `X-Goog-Authenticated-User-Email` header to identify the user.
    *   It inspects the request's cookies for an existing `session_id`. If one is not found, it generates a new UUID.
    *   It calls the `get_or_create_session` function to ensure the session is persisted in Firestore.
    *   It populates the global `app.state` object with the `user_email` and `session_id`. This object acts as the bridge to the Mesop context.
    *   Finally, it creates a `RedirectResponse` to `/home` and sets the `session_id` cookie on the response to ensure it persists for subsequent requests.

**2. Firestore Session State Persistence**

*   **Action:** The `common/storage.py` module was enhanced to manage session objects.
*   **Implementation:**
    *   A `Session` dataclass was created to define the session schema.
    *   A `get_or_create_session` function was added to handle the logic of retrieving an existing session document from Firestore or creating a new one.
    *   The name of the Firestore collection is sourced from the new `SESSIONS_COLLECTION_NAME` variable in `config/default.py`.

**3. Mesop State Hydration (`on_load`)**

*   **Action:** The `on_load` function in `main.py` was updated to receive the user and session data.
*   **Implementation:**
    *   The function now reads the `user_email` and `session_id` from the global `app.state` object (which was populated by the `/__/auth/` endpoint).
    *   It then uses these values to populate the Mesop-specific `me.state(AppState)`. This correctly "hydrates" the UI state with the authenticated user and session info.

**4. State Class Update**

*   **Action:** The `state/state.py` file was updated.
*   **Implementation:** The `session_id: str` field was added to the `AppState` dataclass to hold the unique session identifier.

---

### **Verification Plan**

The implementation was validated against the following test cases.

*   **Test Case 1: The Deep Link Test (Primary Validation)** - **PASSED**
    *   Navigating directly to a sub-page correctly created a new session and attributed generated media to the user.

*   **Test Case 2: Session Persistence and Restoration** - **PASSED**
    *   The session ID correctly persisted across navigations within the same browser session.

*   **Test Case 3: The Standard Flow Regression Test** - **PASSED**
    *   Navigating to the root of the application correctly established and maintained a session.

*   **Test Case 4 (Optional): Unauthenticated Access**
    *   This test can be performed with `curl` to ensure the system defaults to an "anonymous" user when the authentication header is not present.

