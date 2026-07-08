import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit/+esm';

export class GcsUploader extends LitElement {
  static properties = {
    signedUrl: { type: String },
    gcsUri: { type: String },
    acceptedFileTypes: { type: Array },
    disabled: { type: Boolean },
    label: { type: String },
    requestSignedUrl: { type: String },
    uploadComplete: { type: String },
    uploadProgress: { type: String },
    uploadError: { type: String }
  };

  constructor() {
    super();
    this.signedUrl = '';
    this.gcsUri = '';
    this.acceptedFileTypes = ['video/mp4'];
    this.disabled = false;
    this.label = 'Upload File';
    this._selectedFile = null;
  }

  static styles = css`
    :host {
      display: inline-flex;
      flex-direction: column;
      font-family: var(--md-sys-typescale-body-medium-font-family-name, sans-serif);
      width: 100%;
    }

    .uploader-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
    }

    .upload-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      height: 40px;
      padding: 0 24px;
      border-radius: 20px;
      border: 1px solid var(--md-sys-color-outline);
      background-color: var(--md-sys-color-surface-container-low, #f7f2fa);
      color: var(--md-sys-color-primary, #6750a4);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease-in-out;
    }

    .upload-button:hover:not(:disabled) {
      background-color: var(--md-sys-color-surface-container-high, #ece6f0);
    }

    .upload-button:disabled {
      color: var(--md-sys-color-on-surface-disabled, rgba(29, 27, 30, 0.38));
      border-color: var(--md-sys-color-outline-variant, rgba(29, 27, 30, 0.12));
      cursor: not-allowed;
    }

    .progress-bar-container {
      width: 100%;
      height: 4px;
      background-color: var(--md-sys-color-surface-variant, #e7e0ec);
      border-radius: 2px;
      overflow: hidden;
      display: none;
    }

    .progress-bar {
      height: 100%;
      width: 0%;
      background-color: var(--md-sys-color-primary, #6750a4);
      transition: width 0.1s ease;
    }

    .status-text {
      font-size: 12px;
      color: var(--md-sys-color-on-surface-variant);
    }
  `;

  updated(changedProperties) {
    if (changedProperties.has('signedUrl') && this.signedUrl && this._selectedFile) {
      console.log("GcsUploader: Received Signed URL. Starting upload...");
      this._startDirectUpload();
    }
  }

  _triggerFileInput() {
    if (this.disabled) return;
    this.shadowRoot.getElementById('fileInput').click();
  }

  _handleFileSelection(event) {
    const file = event.target.files[0];
    if (!file) return;

    this._selectedFile = file;

    // Show progress bar and reset width
    const pContainer = this.shadowRoot.querySelector('.progress-bar-container');
    const pBar = this.shadowRoot.querySelector('.progress-bar');
    const statusText = this.shadowRoot.querySelector('.status-text');
    if (pContainer) pContainer.style.display = 'block';
    if (pBar) pBar.style.width = '0%';
    if (statusText) statusText.innerText = `Preparing upload: ${file.name}...`;

    // Request Signed URL from Python backend
    console.log("GcsUploader: Requesting Signed URL for", file.name);
    this.dispatchEvent(new MesopEvent(this.requestSignedUrl, {
      value: JSON.stringify({
        filename: file.name,
        contentType: file.type || 'video/mp4',
        fileSize: file.size
      })
    }));
  }

  _startDirectUpload() {
    const file = this._selectedFile;
    const url = this.signedUrl;
    const targetGcsUri = this.gcsUri;
    
    // Clear selected file reference to prevent double upload if state updates again
    this._selectedFile = null;

    const xhr = new XMLHttpRequest();
    const pBar = this.shadowRoot.querySelector('.progress-bar');
    const statusText = this.shadowRoot.querySelector('.status-text');

    // Track upload progress
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        if (pBar) pBar.style.width = `${percent}%`;
        if (statusText) statusText.innerText = `Uploading: ${percent}% of ${this._formatBytes(e.total)}`;
        
        // Notify Mesop of progress
        this.dispatchEvent(new MesopEvent(this.uploadProgress, { value: String(percent) }));
      }
    };

    // Upload complete handler
    xhr.onload = () => {
      const pContainer = this.shadowRoot.querySelector('.progress-bar-container');
      if (pContainer) pContainer.style.display = 'none';

      if (xhr.status === 200) {
        console.log("GcsUploader: Upload completed successfully. URI:", targetGcsUri);
        if (statusText) statusText.innerText = "Upload complete!";
        this.dispatchEvent(new MesopEvent(this.uploadComplete, { value: targetGcsUri }));
      } else {
        console.error("GcsUploader: Upload failed with status", xhr.status);
        const errMsg = `Upload failed (HTTP ${xhr.status})`;
        if (statusText) statusText.innerText = errMsg;
        this.dispatchEvent(new MesopEvent(this.uploadError, { value: errMsg }));
      }
    };

    // Network error handler
    xhr.onerror = () => {
      const pContainer = this.shadowRoot.querySelector('.progress-bar-container');
      if (pContainer) pContainer.style.display = 'none';
      
      console.error("GcsUploader: Network error during upload.");
      const errMsg = "Upload failed: Network error.";
      if (statusText) statusText.innerText = errMsg;
      this.dispatchEvent(new MesopEvent(this.uploadError, { value: errMsg }));
    };

    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type || 'video/mp4');
    xhr.send(file);
  }

  _formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  render() {
    return html`
      <div class="uploader-container">
        <input 
          type="file" 
          id="fileInput" 
          style="display: none;" 
          accept=${this.acceptedFileTypes.join(',')}
          @change=${this._handleFileSelection}
        />
        <button 
          class="upload-button" 
          ?disabled=${this.disabled} 
          @click=${this._triggerFileInput}
        >
          <slot name="icon">
            <svg style="width:24px;height:24px" viewBox="0 0 24 24">
              <path fill="currentColor" d="M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z" />
            </svg>
          </slot>
          ${this.label}
        </button>
        <div class="progress-bar-container">
          <div class="progress-bar"></div>
        </div>
        <div class="status-text"></div>
      </div>
    `;
  }
}

customElements.define('gcs-uploader', GcsUploader);
