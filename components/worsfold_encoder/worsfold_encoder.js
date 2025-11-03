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

import { LitElement, html } from 'https://esm.sh/lit';

class WorsfoldEncoder extends LitElement {
  // --- Properties (Inputs from Mesop) ---
  static get properties() {
    return {
      videoUrl: { type: String },
      config: { type: Object },
      startEncode: { type: Boolean },
      // These properties will be automatically populated by Mesop with event handler IDs.
      encodeCompleteEvent: { type: String },
      progressEvent: { type: String },
      logEvent: { type: String },
      loadCompleteEvent: { type: String },
    };
  }

  constructor() {
    super();
    this.videoUrl = '';
    this.config = { fps: 15, scale: 0.5 };
    this.startEncode = false;
    this.ffmpeg = null;
    this.loaded = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this.loadFFmpeg();
  }

  _loadScript(url) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  async loadFFmpeg() {
    try {
      await this._loadScript('/assets/ffmpeg/ffmpeg/package/dist/umd/ffmpeg.js');

      const { FFmpeg } = window.FFmpegWASM;

      this.ffmpeg = new FFmpeg();

      this.ffmpeg.on('log', ({ message }) => {
        this._onLog(message);
      });
      const baseURL = '/assets/ffmpeg';
      await this.ffmpeg.load({
          coreURL: `${baseURL}/ffmpeg-core.js`,
          wasmURL: `${baseURL}/ffmpeg-core.wasm`,
          workerURL: `${baseURL}/ffmpeg-core.worker.js`
      });
      this.loaded = true;
      console.log('FFmpeg loaded');
      this._onLoadComplete();
    } catch (e) {
        console.error("Error loading ffmpeg", e);
    }
  }

  // --- Events (Outputs to Mesop) ---

  _onLoadComplete() {
    console.log("Firing onLoadComplete event. Handler ID:", this.loadCompleteEvent);
    if (!this.loadCompleteEvent) return;
    this.dispatchEvent(new MesopEvent(this.loadCompleteEvent, {}));
  }

  _onEncodeComplete(dataUrl) {
    if (!this.encodeCompleteEvent) return;
    this.dispatchEvent(new MesopEvent(this.encodeCompleteEvent, dataUrl));
  }

  _onProgress(progress) {
    if (!this.progressEvent) return;
    this.dispatchEvent(new MesopEvent(this.progressEvent, progress));
  }

  _onLog(logMessage) {
    if (!this.logEvent) return;
    this.dispatchEvent(new MesopEvent(this.logEvent, logMessage));
  }

  // --- Lifecycle Methods ---

  willUpdate(changedProperties) {
    if (changedProperties.has('startEncode') && this.startEncode) {
      this.startEncode = false;
      this._beginEncodingProcess();
    }
  }

  // --- Core Logic ---

  async _beginEncodingProcess() {
    if (!this.loaded) {
        console.error('FFmpeg is not loaded yet.');
        return;
    }
    if (!this.videoUrl) {
      console.error('Video URL is not set.');
      return;
    }

    console.log(`Starting encoding for: ${this.videoUrl}`);
    this._onLog('Starting encoding...');
    this._onProgress(0);

    // Get signed URL
    const signedUrlResponse = await fetch(`/api/get_signed_url?gcs_uri=${this.videoUrl}`);
    const signedUrlData = await signedUrlResponse.json();
    const signedUrl = signedUrlData.signed_url;
    console.log("Got signed URL:", signedUrl);

    // Fetch the video data as an ArrayBuffer
    const videoResponse = await fetch(signedUrl);
    const videoData = await videoResponse.arrayBuffer();
    console.log(`Fetched video data, size: ${videoData.byteLength} bytes`);

    const { fps, scale } = this.config;
    const inputName = 'input.mp4';
    const paletteName = 'palette.png';
    const outputName = 'output.gif';

    // Write the video file to ffmpeg's memory
    await this.ffmpeg.writeFile(inputName, new Uint8Array(videoData));

    // Generate palette
    const paletteArgs = [
      '-i', inputName,
      '-vf', `fps=${fps},scale=iw*${scale}:-1:flags=lanczos,palettegen`,
      '-y', paletteName
    ];
    await this.ffmpeg.exec(paletteArgs);

    // Generate GIF
    const gifArgs = [
      '-i', inputName,
      '-i', paletteName,
      '-lavfi', `fps=${fps},scale=iw*${scale}:-1:flags=lanczos[x];[x][1:v]paletteuse`,
      '-y', outputName
    ];
    await this.ffmpeg.exec(gifArgs);

    const gifData = await this.ffmpeg.readFile(outputName);

    // Convert the data to a Base64 data URL
    const reader = new FileReader();
    reader.readAsDataURL(new Blob([gifData.buffer], { type: 'image/gif' }));
    reader.onloadend = () => {
      const dataUrl = reader.result;
      this._onProgress(100);
      this._onLog('Encoding complete!');
      this._onEncodeComplete(dataUrl);
    };
  }

  render() {
    return html``;
  }
}

customElements.define('worsfold-encoder', WorsfoldEncoder);
