# Developer Guide

This guide provides information for developers working on the GenMedia Creative Studio application.

## Analytics and Instrumentation

When adding new features, it is important to instrument them with the analytics framework from `common/analytics.py` to provide insights into user behavior and application performance.

### Page Views

Page view tracking is handled automatically by the `page_scaffold` component. When creating a new page, ensure it is wrapped with this scaffold to enable automatic page view logging.

### UI Interactions

There are two ways to track UI interactions: the `@track_click` decorator for simple button clicks, and the `log_ui_click` function for other controls.

#### Button Clicks

To track clicks on buttons, use the `@track_click` decorator on your event handler. This is the simplest way to instrument a button.

**Example:**

```python
from common.analytics import track_click

@track_click(element_id="my_page_generate_button")
def on_generate_click(e: me.ClickEvent):
    # Your event handler logic here
    yield
```

#### Other Controls

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

### Model Calls

To track the performance and status of calls to generative models, use the `track_model_call` context manager.

**Example:**

```python
from common.analytics import track_model_call

with track_model_call("my-generative-model-v1", prompt_length=len(prompt)):
    model.generate_content(...)
```

## State Management

### Working with Dataclasses

When using dataclasses in the Mesop state, it's important to be aware of how they are serialized. Mesop's state management system does not automatically serialize dataclasses that contain non-serializable objects, such as `datetime.datetime`.

To work around this, you have two options:

1.  **Use simple types:** The simplest solution is to use only simple types (e.g., `str`, `int`, `float`, `bool`, `list`, `dict`) in your dataclasses. For example, instead of using a `datetime.datetime` object for a timestamp, you can use an ISO 8601 string.

2.  **Use `asdict`:** If you need to use complex types in your dataclasses, you can use the `asdict` function from Python's `dataclasses` module to convert the dataclass instance to a dictionary before assigning it to the state.

    **Example:**

    ```python
    from dataclasses import asdict

    # ...

    state.my_dataclass = asdict(MyDataClass(timestamp=datetime.datetime.now()))
    ```

    When you access the dataclass from the state, you will need to access it as a dictionary:

    ```python
    timestamp = state.my_dataclass["timestamp"]
    ```

## Using the Media Chooser Component

The application provides a generic, high-performance component for selecting media (`video`, `audio`, or `image`) from the library. This component, `media_chooser_button`, uses a **parent-managed state** pattern. This means the page that uses the button is responsible for managing the state and rendering of the chooser dialog.

This pattern is robust and avoids the complex state-collision bugs that can occur with self-contained components in Mesop. Here’s how to use it:

### 1. Add State to Your Page

First, add the necessary fields to your page's `@me.stateclass` to manage the dialog's visibility, content, and data loading.

**Example:**
```python
from dataclasses import field
from common.metadata import MediaItem

@me.stateclass
class PageState:
    # ... your other page state fields ...

    # State for the media chooser dialog
    show_chooser_dialog: bool = False
    chooser_dialog_media_type: str = ""
    chooser_dialog_key: str = "" # To track which button opened the dialog
    chooser_is_loading: bool = False
    chooser_media_items: list[MediaItem] = field(default_factory=list)
    chooser_last_doc_id: str = "" # For pagination
    chooser_all_items_loaded: bool = False
```

### 2. Render the Button and Create an Event Handler

Place the `media_chooser_button` in your UI. Its `on_click` event should trigger a handler that sets the dialog state and starts the data fetching process.

**Example:**
```python
from components.library.media_chooser_button import media_chooser_button
from common.metadata import get_media_for_chooser

# In your page's layout function:
media_chooser_button(
    key="my_video_chooser", # A unique key for this button
    on_click=open_chooser,
    media_type="video",
    button_label="Choose a Video"
)

# The event handler to open the dialog and load the first page of items:
def open_chooser(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_chooser_dialog = True
    state.chooser_dialog_media_type = "video" # Set the type of media to show
    state.chooser_dialog_key = e.key
    state.chooser_is_loading = True
    state.chooser_media_items = []
    state.chooser_all_items_loaded = False
    state.chooser_last_doc_id = ""
    yield

    items, last_doc = get_media_for_chooser(media_type="video", page_size=20)
    state.chooser_media_items = items
    state.chooser_last_doc_id = last_doc.id if last_doc else ""
    if not last_doc:
        state.chooser_all_items_loaded = True
    state.chooser_is_loading = False
    yield
```

### 3. Render the Dialog

Finally, add a component to your page that renders the dialog itself. This component will read the state you set in the previous step to show the dialog, display the items, and handle selection and infinite scrolling.

For a complete, working example, see `pages/test_media_chooser.py`.
