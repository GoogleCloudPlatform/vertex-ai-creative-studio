# Guide: Integrating Lit Web Components in Mesop

This document provides definitive patterns for implementing custom, interactive Lit-based Web Components within this project. The lessons below were learned through the process of building the `media_tile` and `media_detail_viewer` components.

**The Golden Rule: Data In, Events Out**
A web component is a "black box" to the Mesop server. Communication follows a strict contract:
-   **Data In:** Python passes data via **simple, serializable properties** (strings, JSON).
-   **Events Out:** The component sends events back to Python using `MesopEvent`.

---

## 1. The Definitive Pattern: The `media_tile` Example

This pattern is the foundation for all interactive components in this project.

### A. The Lit Component (`media_tile.js`)

The JavaScript component handles **all rendering and UI logic**. It receives simple data and uses it to build the HTML.

```javascript
import { LitElement, html } from 'https://esm.sh/lit';
import { SvgIcon } from '../svg_icon/svg_icon.js'; // Convention: Use local SVG component

class MediaTile extends LitElement {
  // Convention: Use static getter for properties
  static get properties() {
    return {
      mediaType: { type: String },
      thumbnailSrc: { type: String },
      pillsJson: { type: String }, // Data is passed as a JSON string
      clickEvent: { type: String },
    };
  }

  constructor() {
    super();
    this.addEventListener('click', this._handleClick);
  }

  render() {
    const pills = JSON.parse(this.pillsJson || '[]');
    // All rendering logic is client-side
    return html`
      <div class="thumbnail">
        ${this.mediaType === 'image' ? html`<img .src=${this.thumbnailSrc}>` : ''}
        ${this.mediaType === 'audio' ? html`<svg-icon .iconName=${'music_note'}></svg-icon>` : ''}
      </div>
      <div class="overlay">
        ${pills.map((p) => html`<div class="pill">${p.label}</div>`)}
      </div>
    `;
  }

  _handleClick() {
    if (!this.clickEvent) return;
    // Convention: Use MesopEvent for all communication to Python
    this.dispatchEvent(new MesopEvent(this.clickEvent, {}));
  }
}
customElements.define("media-tile", MediaTile);
```

### B. The Python Wrapper (`media_tile.py`)

The Python wrapper's job is to **prepare and serialize data**.

```python
import mesop as me
import typing
import json

@me.web_component(path="./media_tile.js")
def media_tile(
    *,
    item: MediaItem, // API can accept a complex object...
    on_click: typing.Callable[[me.WebEvent], None],
):
  # ...but it must prepare simple properties for the web component.
  return me.insert_web_component(
    name="media-tile",
    properties={
      "mediaType": item.media_type,
      "thumbnailSrc": gcs_uri_to_https_url(item.gcsuri),
      "pillsJson": json.dumps(item.pills), // Serialize complex data
    },
    events={
      "clickEvent": on_click, // Maps Python handler to JS property
    },
  )
```

---

## 2. Key Concepts & Best Practices

### A. Data Serialization is Mandatory

-   **Problem:** Passing a Python `dataclass` instance as a property fails silently. The JS component receives `null`.
-   **Solution:** The Python wrapper **must** transform complex objects into simple types. For lists or dicts, serialize them to a JSON string and parse the JSON in JavaScript. This is the pattern used by `media_tile` and `media_detail_viewer`.

### B. Event Handling: `MesopEvent` is Required

-   **Problem:** Using a standard `CustomEvent` in JavaScript will not trigger a Python event handler.
-   **Solution:** You **must** use the `MesopEvent` class, which is globally available. The first argument to `new MesopEvent()` must be the handler ID string that Mesop passes into the component's `events` property (e.g., `this.clickEvent`).
-   **Reference:** `interactive_tile.js`, `pixie_compositor.js`, `media_tile.js`.

### C. Client-Side Component Composition

-   **Pattern:** Web components can be composed directly within other web components on the client side. This is more efficient than trying to compose them on the server.
-   **Example:** The `media_detail_viewer` directly includes the `<download-button>` in its template, passing the required properties.
    ```javascript
    // media_detail_viewer.js
    import './download_button/download_button.js';
    // ...
    render() {
      return html`
        <download-button .url=${this.gcsUri}></download-button>
      `;
    }
    ```

### D. Accessing GCS Resources via Signed URLs

-   **Problem:** A web component cannot fetch `gs://` URIs directly.
-   **Solution:** The component must call a backend API endpoint (e.g., `/api/get_signed_url`) that uses the Python GCS library to generate a temporary, signed URL. 
-   **Reference:** The `download_button.js` component is the canonical example of this pattern.

### E. Follow Established Project Conventions

-   **JS Imports:** Always import from the full CDN URL: `import { LitElement } from 'https://esm.sh/lit';`
-   **JS Properties:** Always use the static getter: `static get properties() { return { ... } }`. Do not use `@property` decorators.
-   **Icons:** Do not use Material Symbol font ligatures (e.g., `<span class="icon">music_note</span>`). Use the project's custom `<svg-icon>` component (`<svg-icon .iconName=${'music_note'}></svg-icon>`), which renders hardcoded SVG paths.
