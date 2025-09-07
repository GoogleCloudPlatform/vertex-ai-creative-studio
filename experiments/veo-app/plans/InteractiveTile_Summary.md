# Interactive Tile Component Development Summary

This document summarizes the goals, development process, and final architecture for the interactive tile component used on the home page.

## 1. Goals & Objectives

The primary goal was to replace the static capability tiles on the home page with a more dynamic, interactive, and informative component. The key objectives were:

1.  **Dynamic Background:** For configured tiles, a looping MP4 video should play as a persistent background to create a visually engaging and "live" feel on the page.
2.  **Informative Hover Effect:** When a user hovers over a tile, the content should smoothly transition from an icon and label to a more detailed text description.
3.  **Seamless Navigation:** Clicking a tile should navigate the user to the appropriate page within the application.

## 2. Implementation Journey & Design Decisions

The development process was iterative, involving several key pivots to overcome technical constraints and improve the user experience.

### Initial Approach: Pure Mesop

The first attempt was to build the component purely in Python using Mesop's state management. The plan was to use `on_mouse_enter` and `on_mouse_leave` events to trigger re-renders.

-   **Problem:** This failed because the project's version of Mesop does not support these specific event handlers on the `me.box` component, leading to `pydantic` errors.

### Pivot to a Lit Web Component

Guided by existing patterns in the codebase, the strategy shifted to creating a client-side Lit Web Component (`interactive_tile.js`). This moved all hover and styling logic into the browser, making it independent of Mesop's server-side event model.

### Evolution 1: From GIF to MP4

The initial concept for the animated background was to use a GIF. However, this was updated to use MP4 video for significantly better performance, smaller file sizes, and higher visual quality. The component's properties and configuration were updated from `gif_url` to `video_url` to reflect this.

### Evolution 2: Solving the Content Security Policy (CSP) Error

When using external video URLs (from `deepmind.google`), the browser blocked them due to the application's Content Security Policy.

-   **Solution:** The global CSP was updated in `main.py` to include `https://deepmind.google` in the `media-src` directive, permitting the videos to be loaded securely.

### Evolution 3: UX Refinement to Eliminate Flicker

The initial implementation loaded the video background only during the hover state. This caused a noticeable "flicker" as the video element was rendered and loaded.

-   **Solution:** The component logic was refactored to make the video a *persistent* background if a `video_url` is provided. A semi-transparent dark overlay is now permanently rendered on top of the video to ensure the foreground content (icon or text) is always legible. The only change on hover is now the swapping of the content itself, which is a much smoother and more visually appealing effect.

### The Icon Rendering Challenge

A final challenge was correctly rendering Material Symbols icons inside the component's Shadow DOM. After several attempts using CSS font imports failed, the most robust solution was to use inline SVGs, which removes external font dependencies.

## 3. Final Architecture

-   **`interactive_tile.js`:** A self-contained Lit component.
    -   It renders a looping, muted `<video>` element as a persistent background if a `videoUrl` is provided.
    -   It renders a permanent, semi-transparent overlay on top of the video to ensure content visibility.
    -   It handles its own hover state to switch between showing an icon/label and a description.
    -   It uses inline SVGs for icons to avoid font-loading issues.
-   **`interactive_tile.py`:** A simple Python wrapper that exposes the Lit component to Mesop, mapping Python properties (like `video_url`) and event handlers to the web component's API.
-   **`main.py`:** The main application file contains the global Content Security Policy, which was modified to allow videos to be loaded from their external source.
-   **Configuration:** The component is driven by data from `config/navigation.json`. The Pydantic model `NavItem` in `config/default.py` was updated to support the `description` and `video_url` fields, making the component easily configurable from a central location.