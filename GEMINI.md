# Genmedia Creative Studio - Technical Guide & Coding Conventions

This document serves as the primary technical reference for the Genmedia Creative Studio application. It outlines the architectural standards, coding conventions, and framework-specific patterns required to maintain and extend the codebase.

**Frameworks:** Python 3.10+, Mesop (UI), FastAPI (Backend), Google Cloud (Vertex AI, Firestore, GCS).

---

## 1. Coding Standards & Best Practices

### Python Modern Type Hinting (PEP 585)
Use built-in collection types (`list`, `dict`, `tuple`, `set`) for type hinting instead of the deprecated `typing.List`, `typing.Dict`, etc.
*   **Bad:** `def get_names() -> List[str]:`
*   **Good:** `def get_names() -> list[str]:`

### Logging & Exception Handling
*   **Logging:** Use the centralized logger from `common.analytics`.
    ```python
    from common.analytics import get_logger
    logger = get_logger(__name__)
    ```
*   **Exception Handling in Generators:** When using generators for streaming UI updates (especially with model calls), **ALWAYS** wrap the iteration loop in a `try-except` block. This prevents silent failures and UI freezes.
    ```python
    try:
        for step in generate_process(...):
            state.status = step.message
            yield
    except Exception as e:
        logger.error("Generation failed", exc_info=True)
        state.status = f"Error: {e}"
        yield
    ```

### Concurrency and Context Management
**Critical:** Mesop's `me.state()` and Flask/FastAPI request objects are **thread-local**. They are NOT accessible inside background threads (e.g., `ThreadPoolExecutor`).

*   **Pattern:** Extract all necessary data (user email, session ID, config) in the main thread *before* submitting a task to a thread pool. Pass these as simple arguments.
*   **Safe Logging:** Do not call logging functions that internally access `me.state()` from a background thread unless they have explicit error handling/fallback for missing context.

### Tool Usage Constraints
*   **No Command Substitution:** Do not use `$(...)` or backticks in shell commands. Run separate commands if needed.

---

## 2. Mesop Framework Guidelines

### Core Component Patterns
*   **Read, Don't Assume:** Always read the source code of custom components in `components/` to verify their argument signatures. They often differ from standard Mesop components.
*   **Type Hints:** Use `typing.Callable` for event handlers, NOT `me.EventHandler`.
*   **Keys:** Use the `key` parameter **only** on native Mesop components to differentiate instances or handle events. Do not add `key` to custom component wrappers unless explicitly supported.
*   **Styling:** `me.Style` objects are immutable. To merge styles, create a new `me.Style` object combining properties.
*   **Theme Awareness:** Never hardcode colors (e.g., `#fff`). Use `me.theme_var("surface")` to respect light/dark modes.

### State Management
*   **Global vs. Local:** `me.state(StateClass)` is global per user session.
    *   **Page State:** Define page-specific state classes in the same file as the `@me.page` function.
    *   **Global State:** Use `state.state.AppState` for cross-application data (User info, Session ID).
*   **Accessing State in Handlers:** Event handlers do not receive state as an argument. You must call `state = me.state(PageState)` inside the handler.
*   **Mutable Defaults:** Never use mutable defaults in dataclasses (e.g., `list[str] = []`). Use `field(default_factory=list)`.

### Event Handlers & Generators
*   **Yield, Don't Return:** Event handlers that update the UI during execution must use `yield`. `me.yield_value` is deprecated.
*   **Late Binding Closures:** Be careful with lambdas in loops. They capture the variable reference, not the value.
    *   **Bad:** `on_click=lambda e: handle(item.id)` (uses last `item.id`)
    *   **Good:** `key=item.id` on the component + `e.key` in the handler, OR `functools.partial`.

### Custom Web Components
*   **Decorator:** Use `@me.web_component(path="./my_component.js")`.
*   **Insertion:** Use `me.insert_web_component(name="my-component")`.
*   **Theming:** Pass `theme_mode` as a property and use CSS overrides in the web component to handle third-party content styling.

---

## 3. FastAPI & Backend Integration

### Routing & Mounting
*   **Sub-path Mounting:** Mount the Mesop app on a sub-path (e.g., `/`) using `WSGIMiddleware`, but define specific FastAPI API routes *before* the mount to prevent the catch-all from swallowing them.
*   **Static Files:** Explicitly mount `StaticFiles` to serve Mesop's internal assets when running with Uvicorn directly.

### Security & Headers
*   **Content Security Policy (CSP):** Apply CSP via a global FastAPI middleware (`@app.middleware("http")`). Page-level decorators are often stripped by the WSGI wrapper.

### Deployment (Cloud Run)
*   **Timeouts:** Cloud Run has a hard infrastructure timeout (default 300s). For long-running generation tasks, set `--timeout 3600` in `gcloud run deploy` AND ensure Gunicorn is configured with `--timeout 0`.
*   **Worker Class:** Use `uvicorn.workers.UvicornWorker` in the `Procfile`.

---

## 4. Data & Persistence

### Firestore & Data Models
*   **Centralized Logic:** Keep Firestore queries in `common/metadata.py`, not in UI pages.
*   **Data Lifecycle:** When adding a new field to a data model:
    1.  Update `state/` classes.
    2.  Update `models/requests.py`.
    3.  Update `common/metadata.py` (Write logic).
    4.  **CRITICAL:** Update `_create_media_item_from_dict` in `common/metadata.py` (Read logic).
*   **Consistency:** Ensure backend API parameters match frontend UI expectations (e.g., aspect ratios).

### Storage (GCS)
*   **URI Handling:** Use `common.utils` helpers:
    *   `gcs_uri_to_https_url(uri)` for UI display.
    *   `https_url_to_gcs_uri(url)` for model input.
*   **Unique Filenames:** Always generate unique filenames using `uuid.uuid4()` to prevent collisions.

---

## 5. Generative AI Integration

### Interaction Patterns
*   **Async UI Updates:**
    1.  Event handler calls a helper function to perform the API call.
    2.  Helper yields intermediate status updates (if possible) or returns result.
    3.  Event handler assigns result to state.
    4.  Event handler `yield`s to refresh UI.
*   **Debugging:** Log the full API response object, specifically `finish_reason` and `safety_ratings`, if a model returns empty/truncated text.

### Specific Model Notes
*   **Veo (Video):**
    *   **Bucket Requirement:** `veo_t2v`/`veo_i2v` tools require a full `gs://` URI for the bucket parameter.
    *   **Timeouts:** Retry with shorter durations (e.g., 25s -> 15s) if timeouts occur.
    *   **SDK Types:** Be strict with `google-genai` SDK types (e.g., wrapping images in `types.Image`).

---

## 6. Development Workflows

### Adding New Pages
1.  Create `pages/my_feature.py`.
2.  Decorate the main function: `@me.page(path="/my-feature", title="Title")`.
3.  Import the module in `main.py`.

### Refactoring Strategy
*   **Extraction:** Prefer creating new, smaller component files and importing them over modifying massive files in place.
*   **Protocol:** When changing a core function signature:
    1.  `search_file_content` to find all usages.
    2.  Update all call sites.
    3.  Verify with tests.

### Analytics
*   **Page Views:** Automatic via `page_scaffold`.
*   **Clicks:** Use `@track_click(element_id="...")` decorator on event handlers.
*   **Model Calls:** Use `with track_model_call(...):` context manager.
