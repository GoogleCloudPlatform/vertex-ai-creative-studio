# Plan: Interactive Doodle Page with Lit Web Component

This document outlines the plan to create a new page in the application that allows users to draw on an image using a custom Lit-based Web Component.

### 1. Analysis and Core Challenges

1.  **Data Flow (Python -> JS):** The flow of data from Python to the Lit component is straightforward. We will use the existing `infinite_scroll_chooser_button` to get a GCS URI of an image. We will then pass this URI as the `imageUrl` property to our new `image-drawer` Lit component.

2.  **Data Flow (JS -> Python):** This is the most complex part. The Lit component will have the final, edited image data on the canvas. We need a way to send this large binary data back to the Python server.
    *   The standard `MesopEvent` is designed for small, JSON-serializable data, not large image files. Sending a Base64-encoded data URL in an event is possible but inefficient and might hit size limits.
    *   A much better approach is to have the Python side *request* the data from the component. We can do this by creating a "Save" button in the Mesop UI. When clicked, this will trigger a Python event handler. This handler will then need to call a public method on the Lit component (like the `getResultAsDataUrl()` you've already defined) to get the image data. This "pull" model is more robust for large data.

3.  **Persistence:** Once the Base64 data URL is back in Python, we need to:
    *   Decode it from a string into raw bytes.
    *   Use our existing `common/storage.py` module to upload these bytes to a new GCS bucket/folder (e.g., `doodles/`).
    *   Log the new image and its source to the Firestore `genmedia` collection for library integration.

4.  **Component Integration:** We need to follow the patterns in `WEB_COMPONENT_INTEGRATION_GUIDE.md` precisely to create the Python wrapper for our new Lit component, ensuring we correctly handle properties and events.

### 2. The Plan

This will be a multi-phase implementation.

**Phase 1: Create the "Doodle" Page and Lit Component**

1.  **Create `pages/doodle.py`:** I will create a new page file. This will be the main container for our new feature.
2.  **Create `components/drawing/` Directory:** I will create a new directory to house the drawing component's files.
3.  **Create `components/drawing/image_drawer.js`:** I will save the Lit component code you provided into this new file.
4.  **Create `components/drawing/image_drawer.py`:** I will create the Python wrapper for the Lit component, following the patterns in the integration guide. This will define the component's API for Mesop.
5.  **Register the New Page:** I will add the new `/doodle` page to `main.py` and `config/navigation.json` so it's accessible.

**Phase 2: Implement the Image Selection and Display**

1.  **Add the Chooser Button:** In `pages/doodle.py`, I will add the `infinite_scroll_chooser_button`.
2.  **Handle the Selection Event:** I will create an event handler that, when an image is selected, updates the page's state with the GCS URI of the selected image.
3.  **Pass Data to the Component:** I will pass the selected image's public URL to the `imageUrl` property of our new `image-drawer` component. At this point, you should be able to see an image from your library appear in the canvas, ready to be drawn on.

**Phase 3: Implement the Save Functionality (JS -> Python)**

1.  **Add a "Save" Button:** In `pages/doodle.py`, I will add a Mesop `me.button` next to the drawing canvas.
2.  **Create a Save Event Handler:** The `on_click` handler for this button will be the key. It will need to trigger a JavaScript call. We can do this by using `me.call_js_function`.
3.  **Implement the JS->Python Bridge:** The `me.call_js_function` will call a small JavaScript function that gets the `image-drawer` element, calls its public `getResultAsDataUrl()` method, and then dispatches a *new* `MesopEvent` containing the Base64 data.
4.  **Handle the Data Event:** A Python event handler will catch this new event, receive the Base64 data, decode it, and save it to GCS and Firestore.

### 3. Testing Plan

1.  **Component Rendering:** After Phase 1, we will verify that the new `/doodle` page loads without errors and that the empty canvas and its controls are visible.
2.  **Image Loading:** After Phase 2, we will test selecting an image from the library and confirm that it correctly appears in the drawing canvas.
3.  **Drawing:** We will manually test the drawing functionality, changing pen color and width.
4.  **Saving:** After Phase 3, we will test the "Save" button. We will verify that:
    *   A new image file appears in the correct GCS bucket.
    *   A new entry is created in the Firestore `genmedia` collection.
    *   The new "doodle" appears in the main library view.

### 4. Regression Impacts and Mitigations

*   **Risk:** A new, complex Web Component could introduce JavaScript errors that affect the rest of the application.
    *   **Mitigation:** The component will be isolated to its own page (`/doodle`). Any errors will be contained there and will not impact existing, stable pages like `/imagen` or `/veo`. We will thoroughly test the new page in isolation.
*   **Risk:** The new component could introduce a new circular dependency or module loading issue.
    *   **Mitigation:** We will follow the lessons learned from our previous debugging session. All new modules will have a clean, one-way dependency structure. We will add the new page to `main.py` last, after all other components are created, to minimize risk.
