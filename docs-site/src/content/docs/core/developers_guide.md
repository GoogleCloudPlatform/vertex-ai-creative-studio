---
title: "Developer's Guide"
---

Welcome to the GenMedia Creative Studio application! This guide provides an overview of the application's architecture, key development patterns, and a step-by-step tutorial for adding new pages. Its purpose is to help you understand the project's structure and contribute effectively.

## Application Architecture

This application is built using Python with the [Mesop](https://mesop-dev.github.io/mesop/) UI framework and a [FastAPI](https://fastapi.tiangolo.com/) backend. The project is structured to enforce a clear separation of concerns, making the codebase easier to navigate, maintain, and extend.

Here is a breakdown of the key directories and their roles:

*   **`main.py`**: The main entry point of the application, responsible for initializing the FastAPI server, mounting the Mesop application, handling root-level routing, and applying global middleware.
*   **`pages/`**: Contains the top-level UI code for each distinct page in the application (e.g., `/home`, `/imagen`).
*   **`components/`**: Holds reusable UI components (e.g., headers, dialogs) used across multiple pages.
*   **`models/`**: Contains the core business logic, including interactions with Generative AI models and databases.
*   **`state/`**: Defines the application's state management classes using Mesop's `@me.stateclass`.
*   **`config/`**: For application configuration, including default settings, navigation structure, and prompt templates.

### Visual Workflow

The following sequence diagram shows the typical flow for a generative AI feature in this application, using the VEO page as an example.

![veo sequence diagram](https://github.com/user-attachments/assets/9df0cece-47b0-4c0f-848a-6d6dbf24465c)

This diagram illustrates the flow:
1.  A user interaction happens in the **UI (`pages/`)**.
2.  The UI calls a function in the **business logic layer (`models/`)**.
3.  The model layer interacts with **external Google Cloud APIs**.
4.  Data is saved to **Firestore** via the metadata service (`common/metadata.py`).
5.  The **UI State (`state/`)** is updated, causing the UI to re-render and display the result.

## Core Development Patterns and Lessons Learned

This section outlines the key architectural patterns and best practices that are essential for extending this application.

### Mesop UI and State Management

1.  **Co-locating Page State:**
    *   **Problem:** A page fails to load with a `NameError`.
    *   **Solution:** For state that is specific to a single page, the `@me.stateclass` definition **must** be in the same file as the `@me.page` function. Only the global `AppState` should be in its own file (`state/state.py`).

2.  **Displaying Temporary Notifications with `snackbar`:**
    *   **Problem:** You need to show a temporary, non-blocking notification to the user (e.g., "Saved to library" or an error message).
    *   **Solution:** Use the page-local snackbar pattern. This involves three parts:
        1.  **State:** Add `show_snackbar: bool = False` and `snackbar_message: str = ""` to your page's local `@me.stateclass`.
        2.  **UI:** Add the `<snackbar>` component to your page's layout, binding it to the state variables: `snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)`.
        3.  **Handler:** Create a helper generator function that manages the show/hide cycle and call it from your event handlers using `yield from`.

    *   **Example Implementation:**
        ```python
        # In your pages/my_page.py

        import time
        from components.snackbar import snackbar

        @me.stateclass
        class PageState:
            # ... other state properties
            show_snackbar: bool = False
            snackbar_message: str = ""

        def page_content():
            state = me.state(PageState)
            # ... your page layout
            snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)

        def show_snackbar_helper(state: PageState, message: str):
            """Helper to show and automatically hide the snackbar."""
            state.snackbar_message = message
            state.show_snackbar = True
            yield
            time.sleep(3)
            state.show_snackbar = False
            yield

        def on_some_action(e: me.ClickEvent):
            state = me.state(PageState)
            try:
                # ... do some work ...
                yield from show_snackbar_helper(state, "Action was successful!")
            except Exception as ex:
                yield from show_snackbar_helper(state, f"An error occurred: {ex}")
        ```

3.  **Correctly Handling Event Handlers:**
    *   **Problem:** A UI element does not update the UI when interacted with.
    *   **Solution:** The function directly assigned to an event handler (e.g., `on_click`) must be the generator function that `yield`s. Using a `lambda` to call another generator can break the UI update chain.

4.  **Introspecting Custom Components:**
    *   **Problem:** A `TypeError` about an unexpected keyword argument occurs when using a component from the `components/` directory.
    *   **Solution:** This project's custom components have specific APIs. If you encounter a `TypeError`, **read the component's source file** to understand its exact function signature.

5.  **Passing Data from Loops to Event Handlers:**
    *   **Problem:** An event handler for an item in a list always receives data from the *last* item.
    *   **Solution:** Use the `key` property of the clickable component to pass a unique identifier. The event handler can then access this value via `e.key`.

### Composable UI for Image Uploads

*   **Problem:** You need to create a UI where a user can either upload a new image or select one from the media library. This UI should display a placeholder when empty and the selected image when populated.
*   **Solution:** Follow a compositional pattern by combining several small, reusable components. Do not build a single, monolithic "uploader" component for your page.

*   **Core Components:**
    *   **`image_thumbnail`:** Use this to display an image that has already been uploaded or selected. It includes a built-in "remove" button.
    *   **`_uploader_placeholder`:** Create a private component within your page that renders a styled placeholder box. This component should contain:
        *   An `me.uploader` component for local file uploads.
        *   The `library_chooser_button` component for opening the media library.
    *   **Page Logic:** Your main page component is responsible for the logic. It should conditionally render either the `_uploader_placeholder` (if no image is selected) or the `image_thumbnail` (if an image is selected).

*   **Example Structure:**
    ```python
    # In your pages/my_page.py
    from components.image_thumbnail import image_thumbnail
    from components.library.library_chooser_button import library_chooser_button

    @me.component
    def _uploader_placeholder(on_upload, on_open_library):
        with me.box(style=...): # Dashed border style
            me.uploader(on_upload=on_upload, ...)
            library_chooser_button(on_library_select=on_open_library, ...)

    def my_page_content():
        state = me.state(PageState)
        if state.my_image_uri:
            image_thumbnail(
                image_uri=state.my_image_uri,
                on_remove=handle_remove_image,
                ...
            )
        else:
            _uploader_placeholder(
                on_upload=handle_upload,
                on_open_library=handle_open_library,
            )
    ```

### Analytics and Instrumentation

When adding new features, it is important to instrument them with the analytics framework from `common/analytics.py` to provide insights into user behavior and application performance.

#### Page Views

Page view tracking is handled automatically by the `page_scaffold` component. When creating a new page, ensure it is wrapped with this scaffold to enable automatic page view logging.

#### UI Interactions

There are two ways to track UI interactions: the `@track_click` decorator for simple button clicks, and the `log_ui_click` function for other controls.

##### Button Clicks

To track clicks on buttons, use the `@track_click` decorator on your event handler. This is the simplest way to instrument a button.

**Example:**

```python
from common.analytics import track_click

@track_click(element_id="my_page_generate_button")
def on_generate_click(e: me.ClickEvent):
    # Your event handler logic here
    yield
```

##### Other Controls

For UI elements that don't have a simple click event (e.g., sliders, selects, text inputs), you can use the `log_ui_click` function directly inside the event handler.

**Example:**

```python
from common.analytics import log_ui_click
from state.state import AppState

def on_slider_change(e: me.SliderValueChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="my_page_slider",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    # Your event handler logic here
    yield
```

#### Element IDs

When choosing an `element_id`, use a consistent naming convention. A good practice is to use the format `page_name_element_type_name`. For example:

*   `imagen_generate_button`
*   `veo_aspect_ratio_select`
*   `chirp_text_input`

#### Model Calls

To track the performance and status of calls to generative models, use the `track_model_call` context manager.

**Example:**

```python
from common.analytics import track_model_call

with track_model_call("my-generative-model-v1", prompt_length=len(prompt)):
    model.generate_content(...)
```

## How to Add a New Page

Adding a new page to the application follows a streamlined, modular pattern that keeps page-specific logic self-contained.

### Step 1: Create the Page File

Create a new Python file in the `pages/` directory (e.g., `my_new_page.py`).

### Step 2: Define the Page Structure

Inside your new file, define the core components of your page. A typical page file includes:

1.  **State Class:** If your page has its own state, define a state class using `@me.stateclass`.
2.  **UI Content Function:** Create a function that builds the UI for your page (e.g., `my_new_page_content()`).
3.  **Page Route Function:** Create the main page entry point function, typically named `page()`, decorated with `@me.page(...)`.

**`pages/my_new_page.py`:**
```python
import mesop as me
from state.state import AppState
from components.header import header
from components.page_scaffold import page_frame, page_scaffold

@me.stateclass
class PageState:
    my_value: str = "Hello"

def my_new_page_content():
    state = me.state(PageState)
    with page_frame():
        header("My New Page", "rocket_launch")
        me.text(f"Welcome to my new page! My value is: {state.my_value}")

@me.page(
    path="/my_new_page",
    title="My New Page - GenMedia Creative Studio",
)
def page():
    with page_scaffold(page_name="my_new_page"):
        my_new_page_content()
```

### Step 3: Register the Page in `main.py`

Import your new page module in `main.py` to make it discoverable.

```python
from pages import my_new_page as my_new_page_page
```

### Step 4: Add the Page to the Navigation

Add your new page to `config/navigation.json` to make it accessible in the UI.

```json
{
  "id": 60,
  "display": "My New Page",
  "icon": "rocket_launch",
  "route": "/my_new_page",
  "group": "workflows"
}
```
