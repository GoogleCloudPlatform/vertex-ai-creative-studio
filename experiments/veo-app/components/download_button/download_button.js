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
import 'https://esm.sh/@material/mwc-button';

class DownloadButton extends LitElement {
  static get properties() {
    return {
      url: { type: String }, // Expects a gs:// URI
      filename: { type: String },
      loading: { type: Boolean, state: true },
      error: { type: String, state: true },
    };
  }

  constructor() {
    super();
    this.url = '';
    this.filename = 'download';
    this.loading = false;
    this.error = '';
  }

  static styles = css`
    mwc-button {
      --mdc-theme-primary: var(--mdc-text-button-label-text-color, var(--mat-sys-color-on-surface));
      --mdc-typography-button-text-transform: none;
    }
    .error-message {
        color: var(--mat-sys-color-error, #B00020);
        font-size: 12px;
        margin-top: 4px;
    }
  `;

  async _handleDownload() {
    if (!this.url || !this.url.startsWith('gs://')) {
      this.error = 'Error: Invalid GCS URI provided.';
      return;
    }
    this.loading = true;
    this.error = '';

    try {
      // 1. Get the signed URL from our backend API.
      const signedUrlResponse = await fetch(`/api/get_signed_url?gcs_uri=${this.url}`);
      const signedUrlData = await signedUrlResponse.json();

      if (!signedUrlResponse.ok || signedUrlData.error) {
        throw new Error(signedUrlData.error || `API error! status: ${signedUrlResponse.status}`);
      }
      
      const signedUrl = signedUrlData.signed_url;
      if (!signedUrl) {
        throw new Error('Failed to retrieve signed URL from API.');
      }

      // 2. Fetch the resource using the signed URL.
      const response = await fetch(signedUrl);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 3. Get the data as a blob.
      const blob = await response.blob();

      // 4. Create a temporary link and trigger the download.
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = this.filename || 'download';
      document.body.appendChild(link);
      link.click();

      // 5. Clean up.
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);

    } catch (e) {
      console.error('Download failed:', e);
      this.error = e.message || `Download failed. Check CORS policy and network.`;
    } finally {
      this.loading = false;
    }
  }

  render() {
    const label = this.loading ? 'loading...' : 'download';
    const iconSvg = this.loading
      ? html`<svg slot="icon" xmlns="http://www.w3.org/2000/svg" height="18px" viewBox="0 0 24 24" width="18px" fill="currentColor"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/></svg>`
      : html`<svg slot="icon" xmlns="http://www.w3.org/2000/svg" height="18px" viewBox="0 0 24 24" width="18px" fill="currentColor"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>`;

    return html`
      <mwc-button
        @click="${this._handleDownload}"
        ?disabled="${this.loading}"
      >
        ${iconSvg}
        <span>${label}</span>
      </mwc-button>
      ${this.error ? html`<p class="error-message">${this.error}</p>` : ''}
    `;
  }
}

if (!customElements.get('download-button')) {
  customElements.define('download-button', DownloadButton);
}
