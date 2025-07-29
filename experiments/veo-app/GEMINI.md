# Genmedia Creative Studio - Mesop python application

You are a code assistant that will help build a Mesop UI application - Mesop is a python-based UI framework that can be found in the .venv/lib. 

This application provides the end user with the ability to use Vertex AI Generative Media APIs such as Veo, Lyria, Chirp 3, and Imagen.

It provides a coherent Library that displays metadata of the generative media generations from Firestore.

See also AGENTS.md for more information.


# Critical Mesop Patterns

- **CRITICAL: READ, DON'T ASSUME, CUSTOM COMPONENT APIs.** This project contains many custom components in the `components/` directory. Their function signatures (the parameters they accept) are defined *within this project* and may not match your assumptions or standard Mesop patterns. Before using a custom component, you **MUST** read its source file to understand its exact API. Failure to do so will lead to `TypeError` exceptions (e.g., "unexpected keyword argument"). This is the most common and avoidable source of errors.
- **NEVER use `me.EventHandler` as a type hint.** It does not exist in the Mesop API and will cause an `AttributeError`. The correct type hint for event handler callbacks is `typing.Callable`.
- **The `key` parameter is for native Mesop components ONLY.** Do not add a `key` parameter to custom `@me.component` functions unless you have specifically programmed them to accept and use it. To differentiate between multiple instances of a custom component, pass a unique identifier to a *different*, dedicated prop (e.g., `component_id: str`) if needed. For event differentiation, the `key` should be placed on the clickable native component *inside* your custom component.
- **`me.Style` has no `combine` method.** Mesop `Style` objects are immutable and do not have a built-in merge or combine function. To override default styles, you must manually construct a new `me.Style` object, property by property, giving precedence to the custom styles.
- **`@me.content_component` must always render `me.slot()`**. A function decorated with `@me.content_component` must have a code path that calls `me.slot()`. Do not use an early `return` to control visibility. Instead, the component should always render, and its visibility should be controlled by the `display` property in its style (e.g., `display="block" if is_open else "none"`).
- **Components must be theme-aware.** Do not hardcode colors like `background="#fff"`. Instead, use `me.theme_var()` (e.g., `me.theme_var("surface")`) to ensure components adapt to the current light or dark theme.
- **Handle content overflow.** For container components like dialogs, always include `overflow_y="auto"` in the style to ensure that long content is scrollable and does not break the layout.

# Mesop Hints and Lessons Learned

- The `mesop` library was updated, and `me.yield_value(...)` was removed. It should be replaced with `yield`.
- The function directly assigned to an event handler (e.g., `on_value_change`, `on_click`) must be the generator function that `yield`s. Using a `lambda` to call another generator function will break the UI update chain, and the component will not refresh.
- **Building Custom Components from Primitives:** When a specific component like `me.icon_button` does not exist and causes an `AttributeError`, do not assume the library is deficient. Instead, build the desired functionality from more primitive, guaranteed components. For example, a clickable icon can be reliably constructed using a `me.box` with an `on_click` handler that contains a `me.icon`. This approach is more robust and avoids API-related errors.
- **Lambda Scope in Loops:** When creating event handlers inside a loop (e.g., for a list of items), be aware of Python's late binding in closures. A `lambda` function will capture the variable from the loop, not its value at each iteration. By the time the event is triggered, the variable will hold the value from the *last* iteration. The correct pattern is to use a dedicated event handler function and pass the necessary data through the component's `key` property. Alternatively, if a `lambda` is necessary, use a default argument to capture the value at definition time: `on_click=lambda e, my_value=item.value: handle_click(my_value)`.

## Interacting with Generative AI Models

Here are some key architectural lessons learned when integrating Mesop with Generative AI models:

1.  **Handling Asynchronous-like Operations:** When calling a long-running function (like a GenAI API) from a Mesop event handler, it's crucial to handle the state updates correctly. The recommended pattern is:
    -   The event handler should call a standard Python function that performs the API call and `return`s the result.
    -   The event handler should then assign the returned value to the appropriate state variable.
    -   Finally, the event handler should `yield` to trigger a UI update. This ensures that the result of the long-running operation is correctly reflected in the UI.

2.  **Debugging Model Behavior:** If a model returns an unexpected or truncated response, the issue is often in the prompt or the model parameters. To debug this effectively:
    -   Log the *entire* API response object, not just the text output.
    -   Inspect the response metadata, such as `finish_reason` and `safety_ratings`, to understand why the model stopped generating text.

3.  **Explicit Prompting for Iterative Tasks:** When you need a model to perform the same task on multiple items (e.g., critiquing a list of images), your prompt must be very explicit. To ensure the model completes the entire task:
    -   Instruct the model to iterate through each item.
    -   Define the exact format for each part of the response.
    -   This prevents the model from stopping prematurely after processing only the first item.

## Component Layout and Styling

- **Debugging Visual and Layout Issues:** If you encounter visual artifacts (like extra scrollbars) or layout problems (like broken alignment), the issue is almost always in a `me.Style()` block. Carefully review the `display`, `height`, `margin`, and `padding` properties of the affected component and its parent. Use your browser's developer tools to inspect the generated HTML and CSS to understand the layout issue.
*   **Use `dialog_actions` for button rows:** When you want to display a row of buttons in a dialog, wrap them in the `dialog_actions` component. This will ensure they are laid out correctly.

*   **Avoid `max_width` for expanding content:** If you want a component to fill the available space in its container, avoid using the `max_width` style property. This will allow the component to expand as expected.

*   **Use `me.Style(margin=me.Margin(top=...))` for spacing:** To add spacing between components, use the `margin` property in the `me.Style` class. This is the correct way to add padding and margins to components.
*   **Placeholders for Conditional Content:** For components that display conditionally loaded content (like an uploaded image), use a permanently styled container (`me.box`). Render content *inside* this container based on the current state (e.g., a placeholder icon, a loading spinner, or the final content). This prevents layout shifts and creates a more polished user experience.


## Best Practices for Using Mesop with FastAPI

This document outlines key lessons learned and best practices for integrating the Mesop UI library with a FastAPI backend. Following these guidelines can help avoid common issues related to routing, static file serving, and security policies.

### 1. Handling Routing and Path Conflicts

**The Problem:** FastAPI routes (e.g., `@app.get('/')`) do not work as expected if a Mesop app is mounted at the same root path.

**The Cause:** When you mount the Mesop application using `WSGIMiddleware` at a specific path (like `/`), it acts as a catch-all for all requests under that path. This means the Mesop app will receive the request before your FastAPI route handler has a chance to execute, leading to a "Not Found" error in Mesop if the path isn't a registered Mesop page.

**The Solution:** Mount the Mesop WSGI application on a sub-path (e.g., `/app`). This allows FastAPI's router to handle specific root-level paths (like `/` for redirects or `/__/auth/` for authentication) first, before passing requests to the Mesop application.

**Example:**
```python
# Allows FastAPI to handle the root path for redirects
@app.get("/")
def home() -> RedirectResponse:
    return RedirectResponse(url="/app/home")

# Mounts the Mesop app on a sub-path
app.mount(
    "/app",
    WSGIMiddleware(
        me.create_wsgi_app()
    ),
)
```

### 2. Serving Mesop's Static Frontend Assets

**The Problem:** When running the application directly with an ASGI server like Uvicorn (e.g., `python main.py`), the Mesop UI is blank, and the browser console shows 404 (Not Found) errors for files like `prod_bundle.js` and `styles.css`.

**The Cause:** The `mesop` command-line tool automatically handles the serving of Mesop's internal frontend assets. When you bypass this and run your own server, you become responsible for serving these files.

**The Solution:** You must explicitly add a `StaticFiles` mount to your FastAPI application that points to the location of Mesop's frontend assets within the installed `mesop` package. You can find this path dynamically using Python's `inspect` and `os` modules.

**Example:**
```python
import inspect
import os
import mesop as me
from fastapi.staticfiles import StaticFiles

# ... your FastAPI app setup ...

app.mount(
    "/static",
    StaticFiles(
        directory=os.path.join(
            os.path.dirname(inspect.getfile(me)), "web", "src", "app", "prod", "web_package"
        )
    ),
    name="static",
)
```

### 3. Applying a Content Security Policy (CSP)

**The Problem:** A Content Security Policy (CSP) defined in a page-specific decorator (`@me.page(security_policy=...)`) is not applied, causing the browser to block external scripts or resources.

**The Cause:** When Mesop is run inside FastAPI's `WSGIMiddleware`, the environment can prevent these page-specific headers from being correctly propagated to the final HTTP response sent by FastAPI.

**The Solution:** The most reliable method is to apply a global CSP using a FastAPI middleware. This intercepts every outgoing response and adds the necessary `Content-Security-Policy` header, ensuring it is applied consistently across all pages.

**Example:**
```python
from fastapi import Request, Response

# ... your FastAPI app setup ...

@app.middleware("http")
async def add_custom_header(request: Request, call_next):
    response = await call_next(request)
    # This is an example policy. Adjust it to your needs.
    response.headers["Content-Security-Policy"] = "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self';"
    return response
```

## Application Architecture and State Management

### 1. Co-locating Page State

**The Problem:** A page fails to load and throws a `NameError: name 'PageState' is not defined`.

**The Cause:** The page-specific state class (`@me.stateclass`) was defined in a separate `state/` directory, but the page's rendering function and event handlers in the `pages/` directory could not find it in their scope during execution.

**The Solution:** Adhere to the project's established convention. For state that is specific to a single page, the `@me.stateclass` definition must be in the *same file* as the `@me.page` function and its associated event handlers. This ensures that the state class is always in the correct scope. Only the global `AppState` should be in its own file.

### 2. Accessing Global State in Event Handlers

**The Problem:** An event handler (e.g., `on_click`) throws a `NameError` because it cannot access the global `AppState`.

**The Cause:** Unlike the main page function, which receives the application state as a parameter, event handlers operate in a different scope and do not automatically have access to it. 

**The Solution:** You must explicitly get a reference to the global state inside the event handler function by calling `me.state(AppState)`.

**Example:**
```python
from state.state import AppState

def on_click_my_button(e: me.ClickEvent):
    # Correctly get a reference to the global state
    app_state = me.state(AppState)
    
    # Now you can access properties of the global state
    print(f"The current user is: {app_state.user_email}")
```

### 3. Separating Configuration from Code

**The Problem:** The application's navigation menu is hardcoded as a list of dictionaries in a Python file, making it difficult to manage.

**The Best Practice:** For data that is essentially static configuration, such as navigation links or dropdown options, it is better to store it in a dedicated data file (e.g., JSON or YAML) rather than embedding it in Python code. This separates the application's configuration from its logic. Always source configuration values like model names, API endpoints, or bucket names from the `config/default.py` file. Avoid hardcoding these 'magic strings' directly in component or model logic to improve maintainability and prevent errors.

**The Solution:**
1.  Create a `config/navigation.json` file to define the navigation structure.
2.  In your Python code, read this file and parse it. 
3.  (Recommended) Use Pydantic models to validate the structure of the loaded data, which prevents errors from malformed configuration.

This approach makes the configuration easier to read, modify (even for non-developers), and validate.

### 4. Deploying with Gunicorn and Uvicorn

**The Problem:** When deploying to a service like Cloud Run, the application fails to start, or authentication routes do not work.

**The Cause:** The `Procfile` command is configured to run a standard WSGI application, but a FastAPI-wrapped Mesop app is an ASGI application.

**The Solution:** You must instruct the Gunicorn process manager to use a Uvicorn worker, which knows how to run ASGI applications. The `Procfile` command should point to the FastAPI `app` object in your `main.py` file.

**Example `Procfile`:**
```
web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 -k uvicorn.workers.UvicornWorker main:app
```

### 5. Bridging FastAPI to Mesop State & Avoiding Module Load Errors

**The Problem:** The application crashes on startup or navigation with a `NameError: name 'AppState' is not defined`, or user-specific data (like the current user's email) is not correctly passed from a FastAPI middleware to the Mesop UI state.

**The Cause:** This is caused by a combination of two subtle but critical issues:
1.  **Circular Imports / Import-Time Side Effects:** A page or component imports a module (e.g., `config/default.py`) that performs file I/O or other complex logic at the module level (i.e., not inside a function). This interferes with Mesop's module loading process, leading to partially initialized modules and the `NameError`.
2.  **Incorrect Context Passing:** Attempts to pass data from a FastAPI middleware to the Mesop state by directly modifying Mesop's internal state or using incorrect context objects will fail because of the boundary between the ASGI (FastAPI) and WSGI (Mesop) applications.

**The Solution: The Middleware-to-Environ-to-State Pattern**

This is the established, robust pattern for this application:

1.  **One-Way Dependencies:** Ensure `main.py` is the root of the dependency tree. It can import from any other module, but **no other module should ever import from `main.py`**.
2.  **Centralize State:** The global `AppState` should be defined in a single, dedicated file (`state/state.py`). All other modules that need access to the global state should import it from this file.
3.  **Defer Configuration Loading:** In configuration files like `config/default.py`, wrap any logic that reads files or performs I/O in a function (e.g., `get_welcome_page_config()`). Call this function only when the data is needed inside a page or component, not at the module level.
4.  **Use the ASGI Scope:** In your FastAPI middleware, place user-specific data into the `request.scope` dictionary using standard, uppercase environment variable keys (e.g., `request.scope["MESOP_USER_EMAIL"] = ...`).
5.  **Initialize State from `environ`:** In the `__init__` method of your `AppState` class (`state/state.py`), import `request` from `flask` and read the user data from the `request.environ` dictionary. The `WSGIMiddleware` automatically bridges the keys from the ASGI `scope` to the WSGI `environ`.

**Example:**

**`main.py` (Middleware):**
```python
@app.middleware("http")
async def set_request_context(request: Request, call_next):
    user_email = request.headers.get("X-Goog-Authenticated-User-Email", "anonymous@google.com")
    # ... strip prefix ...
    request.scope["MESOP_USER_EMAIL"] = user_email
    # ...
    response = await call_next(request)
    return response
```

**`state/state.py` (State Initialization):**
```python
from flask import request
import mesop as me

@me.stateclass
class AppState:
    # ... fields ...
    def __init__(self):
        if "MESOP_USER_EMAIL" in request.environ:
            self.user_email = request.environ["MESOP_USER_EMAIL"]
        # ...
```

### 5. Avoiding Circular Imports and Import-Time Side Effects

**The Problem:** The application fails to start or crashes during navigation with a `NameError: name 'AppState' is not defined`, even though the import statement for `AppState` appears correct.

**The Cause:** This is a classic symptom of a **circular import dependency** or an **import-time side effect**.
*   **Circular Import:** `main.py` imports a page (e.g., `pages/home.py`), which in turn imports a component (e.g., `components/my_component.py`) that then imports something from `main.py`. This creates a loop that Python cannot resolve, leading to partially loaded modules.
*   **Import-Time Side Effect:** A module that is imported at startup (e.g., `config/default.py`) executes code that performs I/O operations (like reading a file) or other complex logic *at the module level*. This can interfere with the Mesop runtime's own module loading and initialization process, especially when using a development server with a file reloader.

**The Solution:**
1.  **One-Way Dependency:** Your `main.py` file should be the root of your application's dependency tree. It can import from any other module, but **no other module should ever import from `main.py`**.
2.  **Centralize State:** The global `AppState` should be defined in a single, dedicated file (e.g., `state/state.py`). All other modules that need access to the global state should import it from this file.
3.  **Defer Execution:** Avoid running complex code or I/O operations at the module level in configuration files. Instead of setting a global variable directly (`MY_CONFIG = load_config_from_file()`), wrap the logic in a function (`def get_my_config(): return load_config_from_file()`). Call this function only when the configuration is actually needed within a component or page function. This ensures that such side effects only occur during the rendering process, not during the sensitive module import phase.

## Backend and Frontend Consistency
Ensure that parameters used in backend API calls (e.g., `models.image_models.generate_image_for_vto`) match the expectations of the frontend UI components that will display the result. For example, if a UI container is styled to be square (`1:1`), the corresponding API call to generate an image for that container should request a `1:1` aspect ratio. Mismatches will lead to distorted or improperly fitted media.

## File and Storage Management
*   **Ensure Unique Filenames:** When saving dynamically generated content (like images, videos, or audio files) to a shared storage system like Google Cloud Storage, always generate a unique filename for each asset. This prevents files from being overwritten. A good practice is to use Python's `uuid` module (e.g., `f"my_file_{uuid.uuid4()}.png"`) to create a universally unique identifier for each file.

## VTO Page Lessons Learned: Creating the Virtual Try-On (VTO) Page

This section summarizes the process of creating the Virtual Try-On (VTO) page, including the challenges encountered and the solutions implemented.
- **Mutable Default Values:** When defining a state class, avoid using mutable default values like `[]` for fields. Instead, use `field(default_factory=list)` to ensure that a new list is created for each user session.

- **Slider Component:** If the `me.slider` component doesn't support a `label` parameter, you can wrap it in a `me.box` and use a `me.text` component as the label.

- **Generator Functions:** Generator functions (those that use `yield`) must have a `yield` statement after updating the state to ensure that the UI is updated.

- **API Error Handling:** When an API returns an "Internal error" with an Operation ID, it signifies a server-side issue. The best course of action is to wait and retry, and if the problem persists, report the Operation ID to Google Cloud support.

- **GCS URI Construction:** When working with GCS URIs, be mindful of duplicate prefixes. The `store_to_gcs` function returns a full `gs://` URI, so do not prepend the prefix again in the calling function. This applies to both creating display URLs (e.g., `https://storage.mtls.cloud.google.com/`) and passing URIs to the API.

### 1. Initial Scaffolding and Page Creation

- **File Structure:** Following the existing architecture, we created three new files:
    - `pages/vto.py`: For the UI and page logic.
    - `state/vto_state.py`: For managing the page's state.
    - `models/vto.py`: For handling the VTO model interaction.
- **Page Registration:** The new page was registered in `main.py` and added to the navigation in `config/navigation.json`.

### 2. File Uploads and GCS Integration

- **GCS Uploads:** We used the existing `common/storage.py` module to upload the person and product images to Google Cloud Storage.
- **Displaying GCS Images:** We learned that the `me.image` component requires a public HTTPS URL, not a `gs://` URI. The correct way to display GCS images is to replace `gs://` with `https://storage.mtls.cloud.google.com/`.

### 3. Interacting with the VTO Model

- **Model API:** We adapted the provided [generative-ai/vision/getting-started
/virtual_try_on.ipynb](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/vision/getting-started/virtual_try_on.ipynb) sample to work within our application's architecture. This involved:
    - Using GCS URIs instead of local files.
    - Passing the `sampleCount` and `baseSteps` parameters to the model.
    - Handling multiple generated images in the response.
- **Configuration:** We moved the VTO model name to the `config/default.py` file to avoid hardcoding it.

### 4. UI/UX Improvements

- **Image Display:** We resized the person and product images to a maximum width of 400px and centered them under their respective upload buttons.
- **Slider Control:** We added a slider to control the number of images generated, and we displayed the currently selected value next to the slider.
- **Clear Button:** We added a "Clear" button to reset the person, product, and generated images.

### 5. State Management and Debugging

- **Mutable Default Values:** We encountered a `TypeError` because we were using a mutable default value (`[]`) for the `result_images` list in our state class. We resolved this by using `field(default_factory=list)` instead.
- **Slider Component:** We encountered an `Unexpected keyword argument` error when using the `label` parameter on the `me.slider` component. We resolved this by wrapping the slider in a `me.box` and using a `me.text` component as the label.
- **Generator Functions:** Generator functions (those that use `yield`) must have a `yield` statement after updating the state to ensure that the UI is updated.

## Library and Data Flow Lessons

- **`on_load` is for Pages, Not Components:** The `on_load` event handler should only be used in the `@me.page` decorator. It fires once when the page is first loaded in the browser. It is not a general-purpose component lifecycle hook and will cause an `Unexpected keyword argument` error if used on a standard component like `me.box`.
- **Top-Down Data Flow is Key:** The correct way to manage dynamic data is for parent components to own the data-fetching logic. The parent should fetch the data and then pass it down to child components as parameters. Child components should be as "presentational" as possible.
- **Triggering Refreshes via State:** To make a component re-fetch its data, you must trigger a change in its state. The most reliable way to do this from a parent component is to have the parent manage the data directly and simply re-render the child with the new data.
- **Unpacking Lists in UI:** When displaying data from a list within a list (like the `gcs_uris` in a `MediaItem`), you must use nested loops in the rendering logic to ensure every item is displayed.
- **Centralize Data Access:** Data access logic (like Firestore queries) should be centralized in a dedicated data layer (e.g., `common/metadata.py`) rather than being co-located with UI components in the `pages/` directory. This improves architecture and maintainability.

## Veo Model Interaction: Lessons Learned

- **SDK Type Specificity:** The `google-genai` SDK requires different `types` for different kinds of image-based video generation. Using the wrong type will result in a Pydantic validation error. The key is to be precise:
    - For a standard **Image-to-Video** call (one input image), the image must be wrapped in `types.Image(gcs_uri=..., mime_type=...)`.
    - For **Interpolation** (a first and last frame), both images must also be wrapped in `types.Image(gcs_uri=..., mime_type=...)`. The first frame is passed as the main `image` parameter, and the last frame is passed as the `last_frame` parameter inside the `GenerateVideosConfig`.

- **Configuration-Driven Lookups:** When a feature (like the Motion Portraits page) needs to get configuration for a model, it's crucial to use the correct key. Our `config/veo_models.py` uses a short version string (e.g., `"2.0"`) as the key, not the full model ID (e.g., `"veo-2.0-generate-001"`). Passing the wrong identifier will lead to an "Unsupported model" error. Always ensure the UI state provides the simple version string for lookups.

- **Isolating and Removing Legacy Code:** A major source of our errors was the presence of an old, non-SDK-based function (`generate_video_aiplatform`) that was still being called by one of the pages. This highlights the importance of completely removing obsolete code after a refactor to prevent it from being used accidentally. A single, unified function (`generate_video`) that handles all generation paths is much easier to maintain and debug.

- **Enhanced Error Logging:** When polling a long-running operation from the `google-genai` SDK, the `operation.error` attribute contains a detailed error message if the operation fails. It is critical to log this specific message in the exception handler. Relying on a generic error message hides the root cause and makes debugging significantly harder.


# More Lessons Learned

Fact: When working with the Mesop framework, access shared or global state within an event handler by calling app_state = me.state(AppState) inside that handler. Do not pass state objects directly as parameters to  components, as this will cause a Pydantic validation error.

1. Prioritize Compatibility Over Premature Optimization: My first error was introducing an ImportError with CountAggregation. While the intention was to make counting faster, it relied on a newer version of the  google-cloud-firestore library than was installed in the project. The lesson is to always work within the  constraints of the project's existing dependencies. A slightly less performant but working solution is always  better than a broken one.


2. Refactoring Requires Thoroughness (Read and Write): When we changed the MediaItem dataclass (renaming  enhanced_prompt to enhanced_prompt_used), I initially only fixed where the data was written. This led to the AttributeError because I didn't fix all the places where the data was read (like the library page). The lesson is that refactoring a data structure requires a global search to update every single point of access.


3. Understand Framework-Specific State Management: This was the most important lesson. My final two errors were  caused by misunderstanding Mesop's state management pattern.
    * The Error: I tried to "push" the global AppState into a component as a parameter  (generation_controls(app_state=...)).
    * The Mesop Way: Components should be self-contained. The correct pattern is for an event handler (like  on_click_generate_images) to "pull" the state it needs when it's triggered, by calling me.state(AppState)  within the function itself.


# Refactoring Checklist

When refactoring code, follow these steps to avoid common errors:

1.  **Find all uses of the code being changed.** Use `search_file_content` to find all instances of the code you are changing. This will help you to avoid missing any instances of the code that need to be updated.
2.  **Pay close attention to data models.** When changing a data model, make sure to update all code that uses that data model. This includes code that reads from and writes to the data model.
3.  **Run tests after making changes.** This will help you to catch any errors that you may have introduced.

# Data Consistency

When working with Firestore, it is important to keep the data in Firestore consistent with the data models in the code. This can be done by:

*   **Using a single source of truth for your data models.** This will help to ensure that all code is using the same data models.
*   **Using a data migration tool to update your data in Firestore when you change your data models.** This will help to ensure that your data in Firestore is always consistent with your data models.

# Working with GCS URIs

When working with GCS URIs, it is important to construct them correctly. The correct way to construct a GCS URI is to use the following format:

```
gs://<bucket-name>/<object-name>
```

When constructing a GCS URI, make sure to not include the `gs://` prefix more than once.

# Feature Implementation: The Full Data Lifecycle Checklist

When adding a new data field (e.g., a prompt, parameter, or setting) to a feature, you must trace and modify its entire lifecycle. Before marking the task as complete, verify each of the following steps:

1.  **State:** Has the field been added to the appropriate state class in `state/`?
2.  **UI Input:** Has the UI component for user input been added or modified in `pages/`?
3.  **Request Schema:** Has the data contract in `models/requests.py` been updated?
4.  **Model Logic:** Has the core generation function in `models/` been updated to use the field?
5.  **Persistence (Write):** Has the `MediaItem` in `common/metadata.py` been updated, AND is the field being saved correctly from the page's `on_click` handler?
6.  **Persistence (Read):** Has the data loading function (`get_media_for_page` in `pages/library.py`) been updated to read the field from Firestore into the `MediaItem` object?
7.  **UI Display:** Is the field now displayed correctly in all relevant views (e.g., the library details dialog)?
8.  **Edge Cases:** Have all related user actions, like "Clear" or "Reset" buttons, been updated to handle the new field?