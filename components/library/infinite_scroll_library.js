/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { LitElement, html, css } from 'https://esm.sh/lit';

const GCS_PUBLIC_URL_PREFIX = 'https://storage.cloud.google.com/';

class InfiniteScrollLibrary extends LitElement {
  static properties = {
    items: { type: Array },
    hasMoreItems: { type: Boolean },
    // These properties are automatically populated by Mesop with unique handler IDs.
    loadMoreEvent: { type: String },
    imageSelectedEvent: { type: String },
  };

  static styles = css`
    .container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 16px;
      height: 100%;
      overflow-y: auto;
    }
    img {
      width: 100%;
      border-radius: 8px;
      object-fit: cover;
      cursor: pointer;
    }
    .loader {
      text-align: center;
      padding: 16px;
      grid-column: 1 / -1; /* Span all columns */
    }
  `;

  constructor() {
    super();
    this.items = [];
    this.hasMoreItems = true;
    this.loading = false;
  }

  render() {
    return html`
      <div class="container" @scroll=${this._handleScroll}>
        ${this.items.map(item => html`
          <img src="${this._formatGcsUri(item.uri)}" @click=${() => this._handleImageClick(item.uri)}>
        `)}
        ${this.hasMoreItems ? html`<div class="loader">Loading...</div>` : ''}
      </div>
    `;
  }

  _handleScroll(e) {
    if (this.loading || !this.hasMoreItems) return;
    const container = e.target;
    if (container.scrollTop + container.clientHeight >= container.scrollHeight - 200) {
      if (!this.loadMoreEvent) {
        console.error("Mesop event handler ID for loadMoreEvent is not set.");
        return;
      }
      this.loading = true;
      this.dispatchEvent(new MesopEvent(this.loadMoreEvent, {}));
      setTimeout(() => { this.loading = false; }, 1000);
    }
  }

  _handleImageClick(uri) {
    if (!this.imageSelectedEvent) {
      console.error("Mesop event handler ID for imageSelectedEvent is not set.");
      return;
    }
    this.dispatchEvent(new MesopEvent(this.imageSelectedEvent, { uri }));
  }

  _formatGcsUri(uri) {
    if (!uri) {
      return "";
    }
    if (uri.startsWith("https://")) {
      return uri;
    }
    if (uri.startsWith("gs://")) {
      return uri.replace('gs://', GCS_PUBLIC_URL_PREFIX);
    }
    return uri;
  }
}

customElements.define('infinite-scroll-library', InfiniteScrollLibrary);