# Analytics Implementation Plan

This document outlines the two-stage plan to introduce robust, configurable analytics and observability into the Genmedia Creative Studio application.

## Guiding Principles

- **Phased Approach:** Manage complexity by delivering value incrementally.
- **Configurability:** All new features (analytics, tracing) must be optional and configurable via environment variables, ensuring no negative impact on local development.
- **Pythonic & Maintainable:** Use standard Python patterns and libraries to ensure the code is clean, robust, and easy to maintain.

---

## Stage 1: Foundational Structured Logging

**Goal:** Implement immediate, valuable analytics using Python's standard `logging` module with structured (JSON) output. This provides a solid foundation and can be ingested by Google Cloud Logging.

**Key Steps:**

- [x] **Create Central Analytics Module:** Create `common/analytics.py` with a JSON-formatted logger.
- [x] **Implement Page View Tracking:** Modify `components/page_scaffold.py` to log page views.
- [x] **Implement UI Click Tracking (via Decorator):** Create and apply the `@track_click` decorator to the Imagen "Generate" button.
- [x] **Implement Model Call Tracking (via Context Manager):** Create and apply the `track_model_call` context manager to external API calls.

---

## Stage 2: Full OpenTelemetry (OTel) Integration

**Goal:** Upgrade the observability stack to a full distributed tracing solution using the OpenTelemetry standard. This will provide deep performance insights and debugging capabilities.

**Prerequisites:** Stage 1 is complete.

**Key Steps:**

- [ ] **Add Dependencies:** Add OTel packages to `requirements.txt`.
- [ ] **Create Tracing Module & Configuration:** Create `common/tracing.py` to handle OTel initialization, controlled by environment variables.
- [ ] **Instrument FastAPI:** Use `opentelemetry-instrumentation-fastapi` to automatically trace all incoming web requests.
- [ ] **Upgrade Analytics Instrumentation:** Modify the decorator and context manager from Stage 1 to create OTel spans instead of just logging.

---

## Verification Milestones

### Milestone 1: Page View & Click Tracking (Ready for Verification)

**Goal:** Verify that the initial analytics instrumentation is working correctly.

**Steps:**

1.  Run the application (e.g., `sh devserver.sh`).
2.  Navigate to the **Imagen** page in your browser.
3.  In the terminal where the app is running, check the console output.
4.  **Expected Log 1 (Page View):** A JSON log should appear containing `"event_type": "page_view"` and `"page_name": "imagen"`.
5.  Click the **"Generate"** button on the Imagen page.
6.  Check the console output again.
7.  **Expected Log 2 (UI Click):** A JSON log should appear containing `"event_type": "ui_click"` and `"element_id": "imagen_generate_button"`.

### Milestone 2: Model Call Tracking

**Goal:** Verify that model calls are logged after the context manager is implemented.

**Steps:**

1.  Run the app and navigate to the Imagen page.
2.  Enter a prompt and click "Generate".
3.  Check the console output.
4.  **Expected Result:** A new JSON log should appear containing `"event_type": "model_call"`.

### Milestone 3: OpenTelemetry Integration

**Goal:** Verify that the full distributed tracing is working after Stage 2 is complete.

**Steps:**

1.  Run the app with OTel enabled via environment variables.
2.  Perform actions on the site to generate traces.
3.  Check the configured OTel backend (e.g., Google Cloud Trace).
4.  **Expected Result:** Full traces are visible, showing connected spans from the initial web request down to the generative model calls.
