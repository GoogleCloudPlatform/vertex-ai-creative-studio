# Guide: Integrating Interactive Lit Web Components in a FastAPI-based Mesop App

This document provides a comprehensive, definitive guide to correctly implementing and debugging custom, **interactive** Lit-based Web Components within a Mesop application that is served by a custom FastAPI server.

**Last Updated:** 2025-08-10

## 1. The Core Challenge: Two-Way Communication

Integrating a custom JavaScript component is straightforward when it only needs to receive data from Python. The challenge arises when the component needs to send events *back* to Python (e.g., from a click or a scroll event). This two-way communication requires a specific, non-obvious implementation pattern.

This guide outlines the definitive, working patterns discovered through a rigorous debugging process.

## 2. The Definitive Pattern: A Complete Example

Here is a complete, working example of an interactive component. The following sections will break down why each part is essential.

### A. The Lit Component (`.js`)

```javascript
// components/my_interactive_component.js
import { LitElement, html } from 'https://esm.sh/lit';

class MyInteractiveComponent extends LitElement {
  static properties = {
    // 1. Receives data from Python.
    items: { type: Array },
    // 2. Receives a unique handler ID string from the Mesop framework.
    itemClickEvent: { type: String },
  };

  // Use connectedCallback for initialization logic that needs Mesop.
  connectedCallback() {
    super.connectedCallback();
    // Now it's safe to dispatch events.
  }

  render() {
    return html`
      <ul>
        ${this.items.map(
          (item) => html`<li @click=${() => this._handleClick(item)}>${item.name}</li>`
        )}
      </ul>
    `;
  }

  _handleClick(item) {
    // 3. Check if the handler ID property was passed from Python.
    if (!this.itemClickEvent) {
      console.error("Mesop event handler ID for itemClickEvent is not set.");
      return;
    }
    // 4. Dispatch a MesopEvent, using the handler ID as the event name.
    // The MesopEvent class is globally available in the browser.
    this.dispatchEvent(new MesopEvent(this.itemClickEvent, { clicked_item: item }));
  }
}
customElements.define("my-interactive-component", MyInteractiveComponent);
```

### B. The Python Wrapper (`.py`)

```python
# components/my_interactive_component.py
import mesop as me
import typing

@me.web_component(path="./my_interactive_component.js")
def my_interactive_component(
    *,
    items: list[dict],
    # 1. Define the event handler prop that the parent will provide.
    on_item_click: typing.Callable[[me.WebEvent], None],
    key: str | None = None,
):
  """Defines the API for the interactive web component."""
  # 2. Render the component, passing properties and the event mapping.
  return me.insert_web_component(
    key=key,
    name="my-interactive-component", # Matches customElements.define()
    properties={"items": items},
    events={
      # 3. The key MUST be the exact name of the JS property.
      "itemClickEvent": on_item_click,
    },
  )
```

### C. The Parent Component (Usage)

```python
# pages/my_page.py
import mesop as me
from .components.my_interactive_component import my_interactive_component

@me.stateclass
class State:
    last_clicked: str = ""

@me.page(path="/my_page")
def my_page():
    state = me.state(State)

    # 1. Define the handler function.
    def handle_click(e: me.WebEvent):
        # 2. Access the data from the `e.value` attribute.
        state.last_clicked = e.value["clicked_item"]["name"]
        yield

    # 3. Call the component, passing the handler to the `on_...` prop.
    my_interactive_component(
        items=[{"name": "Apple"}, {"name": "Banana"}],
        on_item_click=handle_click,
    )
    if state.last_clicked:
        me.text(f"You clicked: {state.last_clicked}")
```

## 3. Key Concepts & Lessons Learned

### A. Event Naming: The `events` Dictionary

This is the most critical and subtle part of the integration.

-   The **key** in the `events` dictionary in the Python wrapper (e.g., `"itemClickEvent"`) must **exactly match** the property name in your Lit component that will receive the event handler ID.
-   The convention is to name the property in your Lit component `eventNameEvent`.
-   The `on_event_name` parameter in the Python wrapper function is what receives the handler from the parent page.

Failure to follow this will result in the event handler ID property being `undefined` in your web component, and events will not be sent to the backend.

### B. Lifecycle Timing: `connectedCallback` is Essential

If your web component needs to perform initialization that communicates with the backend (e.g., dispatching a "load complete" event) or depends on a Mesop-provided global (like `MesopEvent`), you **must** delay this logic.

-   **DO NOT** perform this initialization in the component's `constructor()`.
-   **DO** perform this initialization in the `connectedCallback()` lifecycle method.

`connectedCallback()` is guaranteed to run only after the component is attached to the DOM, by which time the Mesop framework has fully initialized and injected the necessary globals and properties.

### C. Loading JavaScript Libraries (UMD, Workers, etc.)

-   **Web Worker Same-Origin Policy:** A script running on your server **cannot** load a Web Worker script from a different origin (e.g., a CDN). This is a fundamental browser security policy. Any library that uses Web Workers **must** be served from your own application.
-   **Loading UMD Scripts:** UMD scripts often create global variables (e.g., `window.FFmpegWASM`) instead of using standard ES module exports. You cannot use `import { ... } from ...` with these files. The correct way to load them from within a Lit component is to manually create a `<script>` tag and append it to the document, which executes it in the global scope.

**Example:**
```javascript
  _loadScript(url) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  async loadMyLibrary() {
    await this._loadScript('/path/to/my-library.umd.js');
    // Now access the library via the global window object
    const myLibrary = window.MyLibraryGlobal;
    // ...
  }
```

### D. Accessing GCS Resources: Signed URLs are Essential

-   **The Problem:** Directly fetching GCS URLs (especially `gs://` or `https://storage.mtls.cloud.google.com`) from a web component will fail due to CORS and redirect issues, even if the bucket is public.
-   **The Solution:** The frontend must not use GCS URIs directly. Instead, create a FastAPI endpoint (e.g., `/api/get_signed_url`) that uses the Python GCS client library to generate a short-lived, signed URL. The web component then fetches this signed URL, which is designed for public, temporary access and will not have cross-origin issues.
-   **Local Development vs. Cloud Run (IAP):** The implementation of the signed URL endpoint needs to be environment-aware.
    -   **Local:** Your local Application Default Credentials (ADC) must be configured to impersonate the application's service account using `gcloud auth application-default login --impersonate-service-account=<SA_EMAIL>`.
    -   **Cloud Run (with IAP):** When deployed with IAP, the endpoint receives the end-user's identity, not the service account's. The code must explicitly impersonate the service account to get a credential with a private key for signing.

**Robust, Environment-Aware Endpoint:**
```python
from google.auth import impersonated_credentials
import google.auth

@app.get("/api/get_signed_url")
def get_signed_url(gcs_uri: str):
    try:
        storage_client = storage.Client()
        # On Cloud Run, the default credentials are for the service account,
        # but they don't have a private key. We need to impersonate.
        if os.environ.get("K_SERVICE"):
            source_credentials, project = google.auth.default()
            storage_client = storage.Client(
                credentials=impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=os.environ.get("SERVICE_ACCOUNT_EMAIL"),
                    target_scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
                )
            )

        bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="GET",
            service_account_email=os.environ.get("SERVICE_ACCOUNT_EMAIL"),
        )
        return {"signed_url": signed_url}
    except Exception as e:
        return {"error": str(e)}, 500
```

### E. Content Security Policy (CSP)

A global CSP, implemented as a FastAPI middleware in `main.py`, is the most robust way to manage security policies. It must be configured to allow all the resources your application and its components need.

**Example Policy Directives:**
```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://esm.sh; "
"connect-src 'self' https://storage.googleapis.com https://*.googleusercontent.com; "
"media-src 'self' blob: https://storage.googleapis.com https://*.googleusercontent.com; "
"worker-src 'self' blob:;"
```

### F. Theming and Styling (Passing CSS Variables)

-   **The Problem:** CSS Custom Properties (variables) from the main document, like Mesop's theme colors (`--mesop-theme-secondary-container`), may not reliably penetrate the Shadow DOM boundary of a web component. Relying on `var(...)` in your component's stylesheet can fail, causing it to use fallback values and appear visually inconsistent with the rest of the application.

-   **The Solution:** The most robust pattern is to pass the CSS variable *names* from Python into the web component as string properties. The component then uses these properties in inline styles, which guarantees the browser can resolve them against the main document's stylesheet.

**Example Implementation:**

1.  **Update the Python Wrapper (`.py`):** Add properties to accept the theme variable strings.

    ```python
    @me.web_component(path="./interactive_tile.js")
    def interactive_tile(
        # ... other properties
        default_bg_color: str = "",
        hover_bg_color: str = "",
    ):
        return me.insert_web_component(
            # ...
            properties={
                # ... other properties
                "defaultBgColor": default_bg_color,
                "hoverBgColor": hover_bg_color,
            },
        )
    ```

2.  **Update the Parent/Usage (`.py`):** When you call the component, use `me.theme_var()` to pass the variable names.

    ```python
    import mesop.components.interactive_tile.interactive_tile as interactive_tile

    interactive_tile.interactive_tile(
        # ...
        default_bg_color=me.theme_var("secondary-container"),
        hover_bg_color=me.theme_var("tertiary-container"),
    )
    ```

3.  **Update the Lit Component (`.js`):** Receive the properties and use them to dynamically build an inline style object.

    ```javascript
    class InteractiveTile extends LitElement {
      static properties = {
        // ...
        defaultBgColor: { type: String },
        hoverBgColor: { type: String },
      };

      render() {
        const cardStyles = {};
        // Apply the passed-in CSS variable name to the inline style.
        cardStyles.backgroundColor = this.isHovered ? this.hoverBgColor : this.defaultBgColor;

        return html`
          <div class="card" style=${styleMap(cardStyles)}>
            ...
          </div>
        `;
      }
    }
    ```

This pattern bypasses the Shadow DOM inheritance issue entirely and ensures visual consistency.
