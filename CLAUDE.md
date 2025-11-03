# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GenMedia Creative Studio is a web application showcasing Google Cloud's generative media capabilities (Veo, Lyria, Chirp, Imagen, Gemini) built with Mesop (Python UI framework) and FastAPI backend. This is a demonstration project for exploring generative AI workflows.

## Common Commands

### Development

```bash
# Setup virtual environment and install dependencies
uv sync

# Run development server with hot reload
mesop main.py

# Run with uvicorn (production-like)
uv run main.py
```

### Testing

```bash
# Run unit tests
pytest

# Run integration tests (requires GCP credentials and makes real API calls)
pytest -m integration -v -s

# Run specific test file
pytest test/test_veo_generation_flow.py -v
```

### Code Quality

```bash
# Format code with ruff
ruff format .

# Lint code
ruff check .
```

### Deployment

```bash
# Build and deploy to Cloud Run
./build.sh

# Initialize Terraform infrastructure
terraform init
terraform apply
```

## Architecture Overview

### Core Structure

- **`main.py`**: FastAPI app entry point. Mounts Mesop as WSGI middleware, handles authentication via IAP headers, manages session cookies, and applies CSP middleware.

- **`pages/`**: Top-level page definitions. Each file contains a `@me.page` decorated function. Page-specific state classes must be co-located in the same file as the page function.

- **`components/`**: Reusable UI components used across pages (header, side nav, dialogs, etc.).

- **`models/`**: Business logic layer. Contains functions for calling generative AI APIs (Imagen, Veo, Lyria, Chirp), interacting with Firestore, and orchestrating multi-step workflows.

- **`state/`**: State management classes using `@me.stateclass`. Global `AppState` is in `state/state.py`. Page-specific state must be co-located with the page file.

- **`config/`**: Configuration files including `default.py` (environment variables), `navigation.json` (side nav and homepage tiles), and model configurations (`veo_models.py`, `imagen_models.py`).

- **`common/`**: Shared utilities for storage, metadata (Firestore), authentication, analytics, and error handling.

### Request Flow

1. User interaction in UI (`pages/`) triggers event handler
2. Event handler calls business logic in `models/`
3. Model layer makes API calls to Vertex AI
4. Results saved to Firestore via `common/metadata.py`
5. State updated, triggering UI re-render

### Authentication & Session Management

- **Production**: User identity extracted from `X-Goog-Authenticated-User-Email` header (set by Identity Aware Proxy)
- **Local Dev**: Falls back to `anonymous@google.com`
- Session ID stored in cookies and passed to Mesop via `request.scope`
- `AppState.__init__` reads user email from `request.environ`

### Configuration-Driven Design

Model capabilities are defined in configuration files (`config/veo_models.py`, `config/imagen_models.py`) using dataclasses. UI components dynamically adapt based on these configurations. To add/modify a model, update the config file—the UI will adapt automatically.

Navigation is defined in `config/navigation.json`. The file is loaded by `config/default.py`, validated with Pydantic, filtered by feature flags, and consumed by `pages/home.py` and `components/side_nav.py`.

## Critical Mesop Patterns

### State Management

**Page-specific state MUST be co-located** with the page function in the same file. Only `AppState` lives in `state/state.py`. Failure to do this causes `NameError: name 'PageState' is not defined`.

### Event Handlers

The function **directly assigned** to an event handler must be a generator that yields. Do NOT wrap it in a lambda—this breaks the UI update chain.

```python
# CORRECT
def on_change(e: me.InputEvent):
    state = me.state(PageState)
    state.value = e.value
    yield

me.input(on_input=on_change)

# WRONG - UI won't update
me.input(on_input=lambda e: on_change(e))
```

### Passing Data from Loops

To identify which item was clicked in a list, pass the item's unique identifier to the `key` property. Access it via `e.key` in the event handler.

```python
for item in items:
    with me.box(key=item.gcs_uri, on_click=handle_click):
        me.text(item.name)

def handle_click(e: me.ClickEvent):
    selected_uri = e.key  # The gcs_uri of clicked item
    yield
```

### Custom Components

This project contains custom components in `components/`. Do NOT assume their API—read the source file to understand parameters. Standard Mesop components may not exist (e.g., no `me.icon_button`). Build from primitives like `me.box` with `me.icon` inside.

## Error Handling Pattern

**Models layer raises, Pages layer catches**

1. Functions in `models/` should log errors then **re-raise** the exception
2. Event handlers in `pages/` wrap model calls in `try/except` blocks
3. On exception, update page state (e.g., `error_dialog_open = True`, `error_message = str(e)`)
4. Page render function displays error dialog based on state

This maintains separation of concerns and consistent UX.

## Data Management

### GCS URI Handling

Always use utilities in `common/utils.py`:
- `gcs_uri_to_https_url(uri)`: Convert `gs://` to public HTTPS URL for display
- `https_url_to_gcs_uri(url)`: Convert public URL back to `gs://` for API calls

### Firestore Metadata

Media metadata is stored in Firestore. When adding a new field to generated media:

1. Add field to `MediaItem` dataclass in `common/metadata.py`
2. Populate field in page's generation handler
3. Update `get_media_for_page()` in `pages/library.py` to read the field
4. Update library details dialog to display the field

### Unique Filenames

Always generate unique filenames using `uuid.uuid4()` to prevent overwriting:

```python
import uuid
filename = f"generated_{uuid.uuid4()}.png"
```

## Navigation System

Navigation is data-driven via `config/navigation.json`:

- `id`: Unique identifier, used for sorting
- `display`: Link text
- `icon`: Material Symbol name
- `route`: App route (e.g., `/veo`)
- `group`: Category for homepage tiles (e.g., `foundation`, `workflows`)
- `align`: Set to `bottom` for bottom-aligned nav items
- `feature_flag`: Environment variable to control visibility

The `group` key only affects homepage tiles. The `align` key only affects side navigation.

## Adding a New Page

1. Create file in `pages/` (e.g., `pages/my_page.py`)
2. Define page-specific state class with `@me.stateclass` (in same file)
3. Create content function and page route function with `@me.page` decorator
4. Import page in `main.py`: `from pages import my_page`
5. Add entry to `config/navigation.json` with unique `id`, `route`, and optional `feature_flag`

## Adding a Generative Workflow

For multi-step workflows (e.g., Motion Portraits, Shop the Look):

1. Create workflow generator function in `models/` that orchestrates API calls
2. Use `yield` to emit status updates after each step
3. Keep page event handler simple—just call workflow and update state with status
4. Use `common/analytics.py` decorators:
   - `@track_click("element_id")` for button clicks
   - `with track_model_call("model_name"):` for API calls

## Key Files and Locations

- **Environment config**: `.env` (local), `config/default.py` (loads env vars)
- **Model configs**: `config/veo_models.py`, `config/imagen_models.py`, `config/chirp_3hd.py`
- **Navigation**: `config/navigation.json`
- **Firestore collections**: `genmedia` (media metadata), `sessions` (user sessions)
- **GCS buckets**: Configured via `GENMEDIA_BUCKET`, `VIDEO_BUCKET`, `IMAGE_BUCKET` env vars

## Important Constraints

- **Python version**: Requires Python 3.13+
- **Region**: Default is `us-central1` (validate GenAI model availability before changing)
- **No circular imports**: `main.py` imports other modules, but no module should import from `main.py`
- **SDK specificity**: Veo SDK requires precise `types.Image` wrappers—wrong type causes Pydantic validation errors

## Testing Notes

- Unit tests mock external APIs
- Integration tests (marked with `@pytest.mark.integration`) make real API calls
- Use `--gcs-bucket` flag to specify test bucket
- Tests are in `test/` directory

## Deployment Architecture

Two deployment options:
1. **Custom domain with Load Balancer + IAP**: Requires DNS A record, supports external identities
2. **Cloud Run domain with IAP**: No DNS needed, but has known limitations

Key components:
- Cloud Run (serverless container hosting)
- Cloud Firestore (metadata storage)
- Cloud Storage (media files)
- Identity Aware Proxy (authentication)
- Terraform (infrastructure as code)
- Cloud Build (container builds)
