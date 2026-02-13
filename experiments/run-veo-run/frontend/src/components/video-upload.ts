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

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import '@material/web/icon/icon.js';
import '@material/web/iconbutton/icon-button.js';
import '@material/web/progress/linear-progress.js';

export interface UploadResult {
  uri: string;
  signedUri: string;
}

@customElement('video-upload')
export class VideoUpload extends LitElement {
  @property({ type: String }) label = 'Upload Video';
  @state() private previewUrl = '';
  @state() private isUploading = false;
  @state() private error = '';

  static styles = css`
    :host {
      display: block;
      font-family: 'JetBrains Mono', monospace;
    }

    .upload-container {
      border: 2px dashed var(--md-sys-color-outline, #666);
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      cursor: pointer;
      position: relative;
      transition: border-color 0.2s;
      background: rgba(255, 255, 255, 0.05);
      min-height: 150px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
    }

    .upload-container:hover {
      border-color: var(--md-sys-color-primary);
      background: rgba(255, 255, 255, 0.1);
    }

    .preview {
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: 6px;
      position: absolute;
      top: 0;
      left: 0;
    }

    input[type="file"] {
      display: none;
    }

    .label {
      margin-top: 10px;
      color: var(--md-sys-color-on-surface);
    }

    .actions {
      position: absolute;
      top: 5px;
      right: 5px;
      background: rgba(0,0,0,0.5);
      border-radius: 50%;
      z-index: 10;
    }

    .error {
      color: var(--md-sys-color-error);
      margin-top: 5px;
      font-size: 0.8rem;
    }
  `;

  render() {
    return html`
      <div class="upload-container" @click="${this.triggerFileSelect}">
        ${this.previewUrl 
          ? html`
              <video src="${this.previewUrl}" class="preview" autoplay loop muted></video>
              <div class="actions" @click="${(e: Event) => e.stopPropagation()}">
                <md-icon-button @click="${this.clear}">
                  <md-icon>close</md-icon>
                </md-icon-button>
              </div>
            `
          : html`
              <md-icon style="font-size: 48px; color: var(--md-sys-color-primary)">movie</md-icon>
              <div class="label">${this.isUploading ? 'Uploading...' : this.label}</div>
            `
        }
        
        ${this.isUploading 
          ? html`<md-linear-progress indeterminate style="width: 80%; position: absolute; bottom: 20px;"></md-linear-progress>` 
          : ''}
          
        <input type="file" id="fileInput" accept="video/mp4" @change="${this.handleFileChange}">
      </div>
      ${this.error ? html`<div class="error">${this.error}</div>` : ''}
    `;
  }

  private triggerFileSelect() {
    if (this.isUploading || this.previewUrl) return;
    this.shadowRoot?.getElementById('fileInput')?.click();
  }

  private async handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    
    // 1. Validate MIME
    if (file.type !== 'video/mp4') {
        this.error = 'Only MP4 videos are supported.';
        input.value = '';
        return;
    }

    // 2. Validate Metadata (Duration & Resolution)
    try {
        await this.validateVideo(file);
    } catch (e: any) {
        this.error = e.message;
        input.value = '';
        return;
    }

    await this.uploadFile(file);
  }

  private validateVideo(file: File): Promise<void> {
      return new Promise((resolve, reject) => {
          const video = document.createElement('video');
          video.preload = 'metadata';
          video.onloadedmetadata = () => {
              window.URL.revokeObjectURL(video.src);
              
              // Duration Check
              if (video.duration > 30) {
                  reject(new Error(`Video duration (${video.duration.toFixed(1)}s) exceeds limit (30s).`));
                  return;
              }
              if (video.duration < 1) {
                  reject(new Error(`Video is too short (< 1s).`));
                  return;
              }

              // Resolution Check
              const w = video.videoWidth;
              const h = video.videoHeight;
              const validRes = [
                  '1280x720', '1920x1080', // 16:9
                  '720x1280', '1080x1920'  // 9:16
              ];
              const res = `${w}x${h}`;
              
              if (!validRes.includes(res)) {
                  reject(new Error(`Invalid resolution: ${res}. Allowed: 720p or 1080p (16:9 or 9:16).`));
                  return;
              }

              resolve();
          };
          video.onerror = () => {
              window.URL.revokeObjectURL(video.src);
              reject(new Error('Failed to load video metadata.'));
          };
          video.src = URL.createObjectURL(file);
      });
  }

  private async uploadFile(file: File) {
    this.isUploading = true;
    this.error = '';

    // Show local preview immediately
    this.previewUrl = URL.createObjectURL(file);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result: UploadResult = await response.json();
      
      this.dispatchEvent(new CustomEvent('upload-complete', {
        detail: result,
        bubbles: true,
        composed: true,
      }));

    } catch (e: any) {
      this.error = e.message;
      this.previewUrl = ''; // Clear preview on error
    } finally {
      this.isUploading = false;
    }
  }

  private clear(e: Event) {
    e.stopPropagation(); // Prevent re-triggering file select
    this.previewUrl = '';
    this.dispatchEvent(new CustomEvent('upload-cleared', {
      bubbles: true,
      composed: true,
    }));
    // Reset input
    const input = this.shadowRoot?.getElementById('fileInput') as HTMLInputElement;
    if (input) input.value = '';
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'video-upload': VideoUpload;
  }
}
