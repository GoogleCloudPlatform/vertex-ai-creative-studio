# Developer's Guide

Welcome to the GenMedia Creative Studio application! This guide provides an overview of the application's architecture and a step-by-step tutorial for adding new pages. Its purpose is to help you understand the project's structure and contribute effectively.

## Application Architecture

This application is built using Python with the [Mesop](https://mesop-dev.github.io/mesop/) UI framework and a [FastAPI](https://fastapi.tiangolo.com/) backend. The project is structured to enforce a clear separation of concerns, making the codebase easier to navigate, maintain, and extend.

Here is a breakdown of the key directories and their roles:

*   **`main.py`**: This is the main entry point of the application. It is responsible for:
    *   Initializing the FastAPI server.
    *   Mounting the Mesop application as a WSGI middleware.
    *   Handling root-level routing for authentication and redirects.
    *   Applying global middleware, such as the Content Security Policy (CSP).

*   **`pages/`**: This directory contains the top-level UI code for each distinct page in the application (e.g., `/home`, `/imagen`, `/veo`). Each file in this directory typically defines a function that builds the UI for a specific page using Mesop components.

*   **`components/`**: This directory holds reusable UI components that are used across multiple pages. For example, the page header, side navigation, and custom dialogs are defined here. This promotes code reuse and a consistent look and feel.

*   **`models/`**: This is where the core business logic of the application resides. It contains the code for interacting with backend services, such as:
    *   Calling Generative AI models (e.g., Imagen, Veo).
    *   Interacting with databases (e.g., Firestore).
    *   Handling data transformations and other business logic.

*   **`state/`**: This directory defines the application's state management classes using Mesop's `@me.stateclass`. These classes hold the data that needs to be shared and preserved across different components and user interactions.

*   **`config/`**: This directory is for application configuration. It includes:
    *   `default.py`: For defining default application settings and loading environment variables.
    *   `navigation.json`: For configuring the application's side navigation.
    *   `rewriters.py`: For storing the prompt templates used by the AI models.

## Core Development Patterns and Lessons Learned

This section outlines the key architectural patterns and best practices that are essential for extending this application. Adhering to these conventions will help you avoid common errors and build features that are consistent with the existing codebase.

### Mesop UI and State Management

1.  **Co-locating Page State:**
    *   **Problem:** A page fails to load and throws a `NameError: name 'PageState' is not defined`.
    *   **Solution:** For state that is specific to a single page, the `@me.stateclass` definition **must** be in the same file as the `@me.page` function and its associated event handlers. This ensures that the state class is always in the correct scope. Only the global `AppState` should be in its own file (`state/state.py`).

2.  **Correctly Handling Event Handlers:**
    *   **Problem:** A UI element, like a slider or button, does not update the UI when interacted with.
    *   **Solution:** The function directly assigned to an event handler (e.g., `on_value_change`, `on_click`) must be the generator function that `yield`s. Using a `lambda` to call another generator function will break the UI update chain, and the component will not refresh.

3.  **Building Custom Components from Primitives:**
    *   **Problem:** The application crashes with an `AttributeError`, indicating that a Mesop component or type (e.g., `me.icon_button`, `me.EventHandler`) does not exist.
    *   **Solution:** Do not assume a component or type exists. When an `AttributeError` occurs, build the desired functionality from more primitive, guaranteed components. For example, a clickable icon can be reliably constructed using a `me.box` with an `on_click` handler that contains a `me.icon`.

4.  **Introspecting Custom Components:**
    *   **Problem:** The application crashes with a `TypeError` about an unexpected keyword argument when using a component from the `components/` directory (e.g., `components/dialog.py`).
    *   **Solution:** This project contains custom components. Unlike standard Mesop components, their specific API (the parameters they accept) is defined within this project. If you encounter a `TypeError` when using a custom component, do not guess its parameters. **Read the component's source file** to understand its exact function signature and use it accordingly.

5.  **Passing Data from Loops to Event Handlers:**
    *   **Problem:** An event handler for an item in a list always receives data from the *last* item in the list, regardless of which item was clicked.
    *   **Solution:** When creating a list of clickable components inside a `for` loop, you often need to know which specific item was clicked. The standard Mesop pattern for this is to pass the unique identifier of the item (e.g., its ID or a GCS URI) to the `key` property of the clickable component (like `me.box`). The event handler function will then receive this identifier in the `e.key` attribute of the event object.

### Data and Metadata Handling

1.  **Favor Flexible Generalization Over Brittle Replacement:**
    *   **Problem:** When refactoring, a specialized function (e.g., `add_vto_metadata`) is replaced by a generic one, but this new function loses the ability to handle the specific data fields of the original.
    *   **Solution:** When refactoring, favor generalization and flexibility. Instead of removing a specialized function, adapt the new, more general function to handle the specialized cases by accepting more flexible arguments (like `**kwargs`). This ensures no data is lost and the system can be extended more easily in the future.

2.  **Ensure Unique Filenames:**
    *   **Problem:** Generated files in Google Cloud Storage are being overwritten.
    *   **Solution:** When saving dynamically generated content (like images, videos, or audio files), always generate a unique filename for each asset. A good practice is to use Python's `uuid` module (e.g., `f"my_file_{uuid.uuid4()}.png"`) to create a universally unique identifier for each file.

### Backend and Frontend Consistency

*   **Problem:** A generated image appears stretched or improperly fitted in its UI container.
*   **Solution:** Ensure that parameters used in backend API calls (e.g., `models.image_models.generate_image_for_vto`) match the expectations of the frontend UI components that will display the result. For example, if a UI container is styled to be square (`1:1`), the corresponding API call to generate an image for that container should request a `1:1` aspect ratio. Mismatches will lead to distorted or improperly fitted media.

## Firestore Setup

This application uses Firestore to store metadata for the media library and user sessions. Here's how to set it up:

1.  **Create a Firestore Database:** In your Google Cloud Project, create a Firestore database in Native Mode.

2.  **Create Collections:**
    *   Create a collection named `genmedia` (or as configured by `GENMEDIA_COLLECTION_NAME`).
    *   Create a collection named `sessions` (or as configured by `SESSIONS_COLLECTION_NAME`).

3.  **Create an Index:** For the `genmedia` collection, create a single-field index for the `timestamp` field with the query scope set to "Collection" and the order set to "Descending". This will allow the library to sort media by the time it was created. The `sessions` collection does not require a custom index for its default functionality.

4.  **Set Security Rules:** To protect your data, set the following security rules in the "Rules" tab of your Firestore database. These rules ensure that users can only access their own media and session data.

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Match any document in the 'genmedia' collection
    match /genmedia/{docId} {
      // Allow read and write access only if the user is authenticated
      // and their email matches the 'user_email' field in the document.
      allow read, write: if request.auth != null && request.auth.token.email == resource.data.user_email;
    }

    // Match any document in the 'sessions' collection
    match /sessions/{sessionId} {
      // Allow read and write access only if the user is authenticated
      // and their email matches the 'user_email' field in the document.
      allow read, write: if request.auth != null && request.auth.token.email == resource.data.user_email;
    }
  }
}
```



## Authentication and Session Management

This application uses a FastAPI middleware to handle user authentication and session management in a way that is compatible with the Mesop UI framework. This approach ensures that user information is correctly and securely passed to the Mesop application on every request.

Here is the flow:

1.  **FastAPI Middleware:** A middleware function, `set_request_context` in `main.py`, runs for every incoming HTTP request. It is responsible for:
    *   Reading the user's identity from the `X-Goog-Authenticated-User-Email` header (for deployed environments) or falling back to an anonymous user (for local development).
    *   Retrieving a unique `session_id` from the request's cookies or creating a new one.
    *   Placing the `user_email` and `session_id` into the `request.scope` dictionary. The `request.scope` is a standard ASGI feature for passing request-scoped data.

2.  **WSGI Bridge:** The `WSGIMiddleware` that wraps the Mesop application automatically copies the data from the ASGI `request.scope` into the WSGI `request.environ` dictionary. This is the standard mechanism for bridging the two web server protocols.

3.  **Mesop State Initialization:** The `AppState` class in `state/state.py` has a custom `__init__` method. When Mesop creates a new user session, this method is called. It reads the user information directly from the `request.environ` dictionary, correctly initializing the state for the current user.

### Local Development and Service Account Impersonation

When running the application locally, you may encounter errors when trying to perform actions that require a service account with specific IAM permissions (e.g., generating signed URLs for GCS). This is because your local Application Default Credentials (ADC) are based on your user account, which may not have the necessary permissions.

To resolve this, you should configure your local ADC to impersonate the service account that your application uses when deployed. This allows your local server to act *as* the service account and perform the necessary actions.

**Command to Enable Impersonation:**

```bash
gcloud auth application-default login --impersonate-service-account=<SERVICE_ACCOUNT_EMAIL>
```

Replace `<SERVICE_ACCOUNT_EMAIL>` with the email address of the service account used by your deployed application. The Google Cloud client libraries in your Python application will automatically pick up these new credentials without any code changes.

### Avoiding Circular Imports and Import-Time Side Effects

**The Problem:** The application fails to start or crashes during navigation with a `NameError: name 'AppState' is not defined`, even though the import statement for `AppState` appears correct.

**The Cause:** This is a classic symptom of a **circular import dependency** or an **import-time side effect**.
*   **Circular Import:** `main.py` imports a page (e.g., `pages/home.py`), which in turn imports a component (e.g., `components/my_component.py`) that then imports something from `main.py`. This creates a loop that Python cannot resolve, leading to partially loaded modules.
*   **Import-Time Side Effect:** A module that is imported at startup (e.g., `config/default.py`) executes code that performs I/O operations (like reading a file) or other complex logic *at the module level*. This can interfere with the Mesop runtime's own module loading and initialization process, especially when using a development server with a file reloader.

**The Solution:**
1.  **One-Way Dependency:** Your `main.py` file should be the root of your application's dependency tree. It can import from any other module, but **no other module should ever import from `main.py`**.
2.  **Centralize State:** The global `AppState` should be defined in a single, dedicated file (e.g., `state/state.py`). All other modules that need access to the global state should import it from this file.
3.  **Defer Execution:** Avoid running complex code or I/O operations at the module level in configuration files. Instead of setting a global variable directly (`MY_CONFIG = load_config_from_file()`), wrap the logic in a function (`def get_my_config(): return load_config_from_file()`). Call this function only when the configuration is actually needed within a component or page function. This ensures that such side effects only occur during the rendering process, not during the sensitive module import phase.

## Configuration-Driven Architecture

A key architectural principle in this project is the use of centralized, type-safe configuration to drive the behavior of the UI and backend logic. This approach makes the application more robust, easier to maintain, and less prone to bugs.

A prime example of this is the handling of the VEO and Imagen models. Instead of hardcoding model names, capabilities, and constraints throughout the application, we define them in a single location:

-   **`config/veo_models.py`**
-   **`config/imagen_models.py`**

These files contain `dataclass` definitions that serve as a **single source of truth** for each model's properties, such as:

-   Supported aspect ratios
-   Valid video durations (min, max, and default)
-   Maximum number of samples
-   Supported generation modes (e.g., `t2v`, `i2v`, `interpolation`)

The UI components then read from these configuration objects to dynamically build the user interface. For example, the model selection dropdowns, sliders, and feature toggles are all populated and configured based on the capabilities of the currently selected model. This means that to add a new model or update an existing one, you only need to modify the relevant configuration file, and the entire application will adapt automatically.

This pattern is the preferred way to manage model capabilities and other complex configurations in this project.

## Testing Strategy

This project uses a combination of unit tests and integration tests to ensure code quality and reliability. The tests are located in the `test/` directory and are built using the `pytest` framework.

### Unit Tests

Unit tests are used to verify the internal logic of individual functions and components in isolation. They are fast, reliable, and do not depend on external services. We use mocking to simulate the behavior of external APIs, allowing us to test our code's logic without making real network calls.

### Integration Tests

Integration tests are used to verify the interaction between our application and live Google Cloud services. These tests make real API calls and are essential for confirming that our code can successfully communicate with the VEO and Imagen APIs.

-   **Marker:** Integration tests are marked with the `@pytest.mark.integration` decorator.
-   **Execution:** These tests are skipped by default. To run them, use the `-m` flag:
    ```bash
    pytest -m integration -v -s
    ```

### Component-Level Tests

For testing the data flow within our components (e.g., from a successful API call to the Firestore logging), we use component-level integration tests. These tests mock the external API calls but let the internal data handling and state management logic run as it normally would. This is a powerful way to catch bugs in our data mapping and event handling logic.

### Test Configuration

Tests that require access to Google Cloud Storage can be configured to use a custom GCS bucket via the `--gcs-bucket` command-line option. See the `test/README.md` file for more details.

## UI Navigation and Homepage

The application's navigation, including the side navigation and the categorized tiles on the homepage, is generated through a data-driven process that ensures consistency and makes modifications easy.

### How It Works: A Three-Step Process

1.  **`config/navigation.json` (The Data Source)**
    *   This file is the **single source of truth** for all possible navigation items.
    *   Each item in the `pages` list defines a page with properties like `id` (for sorting), `display` (the user-facing name), `icon`, `route`, and `group`.
    *   The **`group`** key is what defines the categories on the homepage (e.g., "foundation", "workflows", "app").

2.  **`config/default.py` (The Configuration Loader & Processor)**
    *   This file reads `navigation.json` and processes it using the `load_welcome_page_config` function.
    *   **Validation:** It uses Pydantic models (`NavItem`, `NavConfig`) to validate the JSON structure, preventing errors from malformed data.
    *   **Filtering:** It checks for a `feature_flag` on each item. A page will only be included if its corresponding feature flag is enabled in the environment configuration. This allows you to toggle navigation links on or off.
    *   **Sorting:** It sorts the final list of pages by their `id`.
    *   The processed list is stored in the `WELCOME_PAGE` constant, ready for the UI to consume.

3.  **`pages/home.py` (The Presentation Layer)**
    *   This file renders the homepage tiles.
    *   It defines a **`GROUP_ORDER`** list (e.g., `["foundation", "workflows", "app"]`) which explicitly controls the display order of the categories.
    *   It groups the items from `WELCOME_PAGE` by their `group` key and then renders each group's title and tiles in the sequence defined by `GROUP_ORDER`.

This system makes the navigation highly configurable and easy to manage.

#### Homepage vs. Side Navigation Rendering

It is critical to understand that different UI components use different keys from `navigation.json` to render their content. This separation of concerns allows for independent control over the homepage layout and the side navigation menu.

-   **`group`**: This key is used exclusively by the **homepage** (`pages/home.py`) to create the categorized tiles (e.g., "Foundation", "Workflows"). It has no effect on the side navigation.
-   **`align`**: This key is used exclusively by the **side navigation** (`components/side_nav.py`) to separate the main links from the utility links. An item with `"align": "bottom"` will be rendered in the lower section of the navigation bar. It has no effect on the homepage.

This allows for a fully data-driven approach to managing the side navigation links. To move a link from the top to the bottom, you only need to add the `align` property in `config/navigation.json`.

### Creating Page-Specific Dialogs

This application uses a reusable pattern to provide page-specific information or settings in a dialog, triggered by an icon in the header. This pattern keeps the header and dialog components generic while giving each page full control over the content it displays.

**Control Flow:**
1.  A page (e.g., `pages/portraits.py`) renders the `header` component, passing `show_info_button=True` and an `on_info_click` callback function.
2.  When the user clicks the info icon, the header calls the provided function.
3.  The function, defined in the page file, updates the page's state to open the dialog (e.g., `state.info_dialog_open = True`).
4.  The page's render function detects the state change and renders a generic `dialog` component, populating it with page-specific content (e.g., descriptions from `about_content.json` and current settings from the page state).

To add a settings/info dialog to a page, follow the implementation in `pages/portraits.py` as a template.

### The "About" Page and Cloud-Native Asset Hosting

Similar to the navigation, the content of the "About" page is managed by a structured data file. However, to support a scalable, production-ready deployment on Cloud Run, the media assets (images, videos) for this page are hosted on Google Cloud Storage (GCS) rather than being checked into the Git repository.

-   **Content Definition:** `config/about_content.json`. This file defines the text and the *relative paths* to the media assets.
-   **Asset Hosting:** A public Google Cloud Storage bucket is used to store the actual image and video files.
-   **Configuration:** The name of the GCS bucket is specified by the `GCS_ASSETS_BUCKET` environment variable.
-   **Rendering Logic:** The `config/default.py` file reads the bucket name from the environment, dynamically constructs the full public URLs for the assets, and makes them available to `pages/about.py` for rendering.

To modify the "About" page, you will need to:
1.  Update the text or asset paths in `config/about_content.json`.
2.  Upload the corresponding media files to the correct path in your configured GCS bucket.

For local development, if you do not set the `GCS_ASSETS_BUCKET` variable, the page will use local paths. To make this work, you can temporarily add a `StaticFiles` mount to `main.py`:
`app.mount("/assets", StaticFiles(directory="assets"), name="assets")`

## How to Add a New Page

Adding a new page to the application is a straightforward process. Here are the steps:

### Step 1: Create the Page File

Create a new Python file in the `pages/` directory. The name of the file should be descriptive of the page's purpose (e.g., `my_new_page.py`).

In this file, define a function that will contain the UI for your page. This function should accept the application state as an argument.

**`pages/my_new_page.py`:**
```python
import mesop as me
from state.state import AppState
from components.header import header
from components.page_scaffold import page_frame, page_scaffold

def my_new_page_content(app_state: AppState):
    with page_scaffold():
        with page_frame():
            header("My New Page", "rocket_launch")
            me.text("Welcome to my new page!")
```

### Step 2: Register the Page in `main.py`

Next, you need to register your new page in `main.py` so that the application knows how to serve it.

1.  Import your new page function at the top of `main.py`:
    ```python
    from pages.my_new_page import my_new_page_content
    ```

2.  Add a new `@me.page` decorator to define the route and other page settings:
    ```python
    @me.page(
        path="/my_new_page",
        title="My New Page - GenMedia Creative Studio",
        on_load=on_load,
    )
    def my_new_page():
        my_new_page_content(me.state(AppState))
    ```

### Step 3: Add the Page to the Navigation

To make your new page accessible to users, you need to add it to the side navigation.

1.  Open the `config/navigation.json` file.
2.  Add a new JSON object to the `pages` array for your new page. Make sure to give it a unique `id`.

**`config/navigation.json`:**
```json
{
  "pages": [
    // ... other pages ...
    {
      "id": 60, // Make sure this ID is unique
      "display": "My New Page",
      "icon": "rocket_launch",
      "route": "/my_new_page",
      "group": "workflows"
    }
  ]
}
```

### Step 4: (Optional) Control with a Feature Flag

If you want to control the visibility of your new page with an environment variable, you can add a `feature_flag` to its entry in `navigation.json`.

```json
{
  "id": 60,
  "display": "My New Page",
  "icon": "rocket_launch",
  "route": "/my_new_page",
  "group": "workflows",
  "feature_flag": "MY_NEW_PAGE_ENABLED"
}
```

Now, the "My New Page" link will only appear in the navigation if the `MY_NEW_PAGE_ENABLED` environment variable is set to `True` in your `.env` file.

That's it! When you restart the application, your new page will be available at the route you defined and will appear in the side navigation.

### Choosing an Image from the Library

This application provides two different components for selecting an image from the library. You should choose the one that best fits your needs.

-   **`library_chooser_button` (Basic):** This is a simple, pure-Mesop component. It is reliable but loads a single, fixed page of recent images. It is suitable for simple use cases.
-   **`infinite_scroll_chooser_button` (Advanced, Recommended):** This is a more advanced component that uses a Lit-based Web Component to provide an "infinite scroll" experience. It offers a much better user experience for large libraries but is currently considered experimental.

Both components are documented below.

### How to Use the `library_chooser_button` Component (Basic)

The `library_chooser_button` is a reusable component that allows users to select an image from the library as an input. Here is how to use it on a page:

1.  **Import the component and its event type:**
    ```python
    from components.library.library_chooser_button import library_chooser_button
    from components.library.events import LibrarySelectionChangeEvent
    ```

2.  **Define a callback handler:** Create a generator function on your page to handle the selection event. This function will receive the `LibrarySelectionChangeEvent` object, which contains the `gcs_uri` of the selected image and the `chooser_id` of the button that was clicked.

    *   **For a single chooser button on a page:**
        ```python
        def on_image_select(e: LibrarySelectionChangeEvent):
            state = me.state(YourPageState)
            state.your_image_field = e.gcs_uri
            yield
        ```

    *   **For multiple chooser buttons on the same page:**
        ```python
        def on_image_select(e: LibrarySelectionChangeEvent):
            state = me.state(YourPageState)
            if e.chooser_id == "person_chooser":
                state.person_image_gcs = e.gcs_uri
            elif e.chooser_id == "product_chooser":
                state.product_image_gcs = e.gcs_uri
            yield
        ```

3.  **Instantiate the component:** Call the component in your page's UI logic, passing the callback handler to the `on_library_select` prop. You must provide a unique `key` if you have multiple choosers on the same page.
    ```python
    # For a single chooser
    library_chooser_button(
        key="my_unique_chooser_key",
        on_library_select=on_image_select,
        button_label="Select from Library"
    )
    ```

    )

### How to Use the `infinite_scroll_chooser_button` Component (Advanced, Recommended)

The `infinite_scroll_chooser_button` is the new, recommended component for selecting an image from the library. It provides a much better user experience for large libraries by loading images dynamically as the user scrolls.

Here is how to use it on a page:

1.  **Import the component and its event type:**
    ```python
    from components.library.infinite_scroll_chooser_button import infinite_scroll_chooser_button
    from components.library.events import LibrarySelectionChangeEvent
    ```

2.  **Define a callback handler:** Create a generator function on your page to handle the selection event. This function will receive the `LibrarySelectionChangeEvent` object, which contains the `gcs_uri` of the selected image.

    ```python
    def on_image_select(e: LibrarySelectionChangeEvent):
        state = me.state(YourPageState)
        state.your_image_field = e.gcs_uri
        yield
    ```

3.  **Instantiate the component:** Call the component in your page's UI logic, passing the callback handler to the `on_library_select` prop.

    ```python
    infinite_scroll_chooser_button(
        on_library_select=on_image_select,
        button_label="Select from Library"
    )
    ```

## Key Takeaways from the VTO Page Development

- **GCS URI Handling:** This is a critical and recurring theme. The `common.storage.store_to_gcs` function returns a **full** GCS URI (e.g., `gs://your-bucket/your-object.png`). When using this value, you must be careful not to prepend the `gs://` prefix or the bucket name again. Doing so will create an invalid path and lead to "No such object" errors.
    - **For API Calls:** Pass the GCS URI returned from `store_to_gcs` directly to the API.
    - **For Displaying in Mesop:** To create a public URL for the `me.image` component, use the `.replace("gs://", "https://storage.mtls.cloud.google.com/")` method on the full GCS URI.

- **Displaying GCS Images:** The `me.image` component requires a public HTTPS URL, not a `gs://` URI. To display images from GCS, replace `gs://` with `https://storage.mtls.cloud.google.com/`.

- **State Management:** Avoid using mutable default values (like `[]`) in your state classes. Instead, use `field(default_factory=list)` to ensure that a new list is created for each user session.

- **UI Components:** If a component doesn't support a specific parameter (like `label` on `me.slider`), you can often achieve the same result by wrapping it in a `me.box` and using other components (like `me.text`) to create the desired layout.

- **Generator Functions:** When working with generator functions (those that use `yield`), make sure to include a `yield` statement after updating the state to ensure that the UI is updated.

- **CORS Configuration for GCS:** To allow the browser to load images from your Google Cloud Storage bucket, you must configure Cross-Origin Resource Sharing (CORS) on the bucket. See the main `README.md` for instructions on how to create the `cors.json` file, apply it to your bucket, and troubleshoot the configuration.

## Key Takeaways from the Veo Model Refactor

- **SDK Type Specificity:** The `google-genai` SDK requires different `types` for different kinds of image-based video generation. Using the wrong type will result in a Pydantic validation error. The key is to be precise:
    - For a standard **Image-to-Video** call (one input image), the image must be wrapped in `types.Image(gcs_uri=..., mime_type=...)`.
    - For **Interpolation** (a first and last frame), both images must also be wrapped in `types.Image(gcs_uri=..., mime_type=...)`. The first frame is passed as the main `image` parameter, and the last frame is passed as the `last_frame` parameter inside the `GenerateVideosConfig`.

- **Configuration-Driven Lookups:** When a feature (like the Motion Portraits page) needs to get configuration for a model, it's crucial to use the correct key. Our `config/veo_models.py` uses a short version string (e.g., `"2.0"`) as the key, not the full model ID (e.g., `"veo-2.0-generate-001"`). Passing the wrong identifier will lead to an "Unsupported model" error. Always ensure the UI state provides the simple version string for lookups.

- **Isolating and Removing Legacy Code:** A major source of our errors was the presence of an old, non-SDK-based function (`generate_video_aiplatform`) that was still being called by one of the pages. This highlights the importance of completely removing obsolete code after a refactor to prevent it from being used accidentally. A single, unified function (`generate_video`) that handles all generation paths is much easier to maintain and debug.

- **Enhanced Error Logging:** When polling a long-running operation from the `google-genai` SDK, the `operation.error` attribute contains a detailed error message if the operation fails. It is critical to log this specific message in the exception handler. Relying on a generic error message hides the root cause and makes debugging significantly harder.

### Adding a New Field to a Generation Page

Adding a new parameter or field (like a negative prompt or a quality setting) to a generation page (e.g., Imagen, Veo) requires touching multiple files across the application stack. This guide outlines the data lifecycle you must consider.

Follow this checklist to ensure your feature is fully integrated:

1.  **State (`state/`):** Add your new field to the appropriate state class (e.g., `VeoState`). This is where the UI will store the user's input.
2.  **UI (`pages/`):** Add the UI control (e.g., `me.textarea`, `me.slider`) to the main page file (e.g., `pages/veo.py`) and create its corresponding event handler.
3.  **Request Schema (`models/requests.py`):** Update the request class (e.g., `VideoGenerationRequest`) to include your new field. This creates a clean data contract for the model layer.
4.  **Model Logic (`models/`):** Update the core generation function (e.g., `models/veo.py`) to use the new field from the request object and pass it to the underlying generative API.
5.  **Save to Firestore (`common/metadata.py` & `pages/`):**
    *   First, add the field to the `MediaItem` dataclass in `common/metadata.py`.
    *   Then, in the page's `on_click` handler (e.g., `on_click_veo`), ensure you populate this new field when creating the `MediaItem` to be logged.
6.  **Load from Firestore (`pages/library.py`):**
    *   This is a critical and easily missed step. In `pages/library.py`, find the `get_media_for_page` function.
    *   Update the `MediaItem` constructor inside this function to read your new field from the `raw_item_data` dictionary.
7.  **Display in Library (`pages/library.py`):** Update the details dialog within the library page to display the new field from the `MediaItem` object.
8.  **Handle Edge Cases:** Remember to update any related functionality. For example, does the "Clear" button on the page need to reset your new field?