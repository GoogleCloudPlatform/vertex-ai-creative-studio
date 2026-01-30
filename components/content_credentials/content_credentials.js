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

import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit/+esm';

export class ContentCredentialsViewer extends LitElement {
  static properties = {
    manifestJson: { type: String },
    _isOpen: { type: Boolean, state: true },
  };

  static styles = css`
    :host {
      display: inline-block;
      position: relative;
      font-family: 'Google Sans', Roboto, Arial, sans-serif;
    }

    .pin {
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.9);
      border-radius: 12px;
      padding: 4px 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      font-size: 12px;
      font-weight: 500;
      color: #333;
      gap: 4px;
      transition: background 0.2s;
    }
    
    .pin:hover {
      background: #fff;
    }

    .popover {
      position: absolute;
      top: 100%;
      right: 0;
      margin-top: 8px;
      width: 300px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.15);
      padding: 16px;
      z-index: 1000;
      color: #333;
      font-size: 13px;
      border: 1px solid #eee;
    }

    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .section {
      margin-bottom: 12px;
    }

    .label {
      font-weight: 500;
      color: #5f6368;
      font-size: 11px;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .value {
      color: #202124;
    }
    
    .icon {
        width: 16px;
        height: 16px;
    }
  `;

  constructor() {
    super();
    this._isOpen = false;
  }

  _toggle() {
    this._isOpen = !this._isOpen;
  }

  render() {
    if (!this.manifestJson) {
      return html``;
    }

    let manifest;
    try {
        manifest = JSON.parse(this.manifestJson);
    } catch (e) {
        console.error("Failed to parse C2PA manifest JSON", e);
        return html``;
    }

    const activeManifestLabel = manifest.active_manifest;
    const activeManifest = manifest.manifests[activeManifestLabel];
    
    if (!activeManifest) return html``;

    const title = activeManifest.title || "Untitled";
    let generator = activeManifest.claim_generator;
    if ((!generator || generator === "Unknown") && activeManifest.claim_generator_info && activeManifest.claim_generator_info.length > 0) {
        generator = activeManifest.claim_generator_info[0].name;
    }
    generator = generator || "Unknown";
    const issuer = activeManifest.signature_info?.issuer || 'Unknown';
    const time = activeManifest.signature_info?.time ? new Date(activeManifest.signature_info.time).toLocaleString() : 'Unknown';
    
    // Extract actions
    let actionsList = [];
    const actionsAssertion = activeManifest.assertions.find(a => a.label === 'c2pa.actions' || a.label === 'c2pa.actions.v2');
    if (actionsAssertion) {
       const actions = actionsAssertion.data.actions;
       if (actions && actions.length > 0) {
           actionsList = actions.map(a => {
               let text = a.description || a.action;
               if (a.softwareAgent && !text.includes(a.softwareAgent)) {
                   text += ` (${a.softwareAgent})`;
               }
               return text;
           });
       }
    }

    return html`
      <div class="container">
        <div class="pin" @click="${this._toggle}">
          <svg class="icon" fill="currentColor"><path fill-rule="evenodd" d="M15.0281 14.56V8C15.0281 4.37701 12.0911 1.44 8.46814 1.44C4.84515 1.44 1.90814 4.37701 1.90814 8C1.90814 11.623 4.84515 14.56 8.46814 14.56H15.0281ZM8.46814 0C4.04986 0 0.46814 3.58172 0.46814 8C0.46814 12.4183 4.04986 16 8.46814 16H16.4681V8C16.4681 3.58172 12.8864 0 8.46814 0ZM9.87614 5.40479H11.2585V6.03839C11.6118 5.56991 12.1417 5.33567 12.8483 5.33567H13.2054V6.69503H12.8368C12.5833 6.69503 12.3683 6.72191 12.1917 6.77567C12.0227 6.82943 11.8768 6.91391 11.7539 7.02911C11.4621 7.27487 11.3161 7.67039 11.3161 8.21567V11.28H9.87614V5.40479ZM5.01726 11.0266C5.4627 11.303 5.9811 11.4413 6.57246 11.4413C7.04862 11.4413 7.4787 11.3453 7.8627 11.1533C8.2467 10.9536 8.56158 10.6848 8.80734 10.3469C9.0531 10.0013 9.21822 9.61344 9.3027 9.18336H7.83966C7.73982 9.4752 7.57854 9.7056 7.35582 9.87456C7.14078 10.0435 6.87966 10.128 6.57246 10.128C6.26526 10.128 6.0003 10.055 5.77758 9.90912C5.55486 9.75552 5.37822 9.54432 5.24766 9.27552C5.12478 9.00672 5.06334 8.69568 5.06334 8.3424C5.06334 7.98912 5.12478 7.67808 5.24766 7.40928C5.37822 7.14048 5.55486 6.93312 5.77758 6.7872C6.0003 6.6336 6.26526 6.5568 6.57246 6.5568C6.8643 6.5568 7.11774 6.63744 7.33278 6.79872C7.54782 6.95232 7.7091 7.16736 7.81662 7.44384H9.29118C9.15294 6.79872 8.8419 6.27264 8.35806 5.8656C7.87422 5.45088 7.27902 5.24352 6.57246 5.24352C5.9811 5.24352 5.4627 5.3856 5.01726 5.66976C4.5795 5.94624 4.23774 6.32256 3.99198 6.79872C3.7539 7.2672 3.63486 7.78176 3.63486 8.3424C3.63486 8.90304 3.7539 9.42144 3.99198 9.8976C4.23774 10.3661 4.5795 10.7424 5.01726 11.0266ZM81.2356 11.064C81.3647 10.9754 81.4837 10.8773 81.5927 10.7696V11.2944H82.9866V3H81.5467V5.8885C81.4536 5.80176 81.3538 5.72213 81.2471 5.6496C80.8631 5.38848 80.4139 5.25792 79.8993 5.25792C79.354 5.25792 78.874 5.4 78.4593 5.68416C78.0446 5.96064 77.7259 6.30624 77.5027 6.72192C77.2795 7.1376 77.1679 7.63584 77.1679 8.21664C77.1679 8.79744 77.2795 9.29568 77.5027 9.71136C77.7259 10.127 78.0446 10.4726 78.4593 10.7491C78.874 11.0256 79.354 11.1638 79.8993 11.1638C80.4139 11.1638 80.8595 11.0309 81.2356 10.7652V11.064ZM79.8993 9.9792C79.6613 9.9792 79.4579 9.91008 79.2891 9.77184C79.1203 9.6336 78.9883 9.43872 78.8931 9.1872C78.7979 8.93568 78.7503 8.6448 78.7503 8.31456V8.11872C78.7503 7.78848 78.7979 7.4976 78.8931 7.24608C78.9883 6.99456 79.1203 6.79968 79.2891 6.66144C79.4579 6.5232 79.6613 6.45408 79.8993 6.45408C80.1373 6.45408 80.3407 6.5232 80.5095 6.66144C80.6783 6.79968 80.8103 6.99456 80.9055 7.24608C81.0007 7.4976 81.0483 7.78848 81.0483 8.11872V8.31456C81.0483 8.6448 81.0007 8.93568 80.9055 9.1872C80.8103 9.43872 80.6783 9.6336 80.5095 9.77184C80.3407 9.91008 80.1373 9.9792 79.8993 9.9792Z"/></svg>
          <!-- span>CR</span -->
        </div>

        ${this._isOpen ? html`
          <div class="popover">
            <h3>
               <svg class="icon" fill="#188038"><path fill-rule="evenodd" d="M15.0281 14.56V8C15.0281 4.37701 12.0911 1.44 8.46814 1.44C4.84515 1.44 1.90814 4.37701 1.90814 8C1.90814 11.623 4.84515 14.56 8.46814 14.56H15.0281ZM8.46814 0C4.04986 0 0.46814 3.58172 0.46814 8C0.46814 12.4183 4.04986 16 8.46814 16H16.4681V8C16.4681 3.58172 12.8864 0 8.46814 0ZM9.87614 5.40479H11.2585V6.03839C11.6118 5.56991 12.1417 5.33567 12.8483 5.33567H13.2054V6.69503H12.8368C12.5833 6.69503 12.3683 6.72191 12.1917 6.77567C12.0227 6.82943 11.8768 6.91391 11.7539 7.02911C11.4621 7.27487 11.3161 7.67039 11.3161 8.21567V11.28H9.87614V5.40479ZM5.01726 11.0266C5.4627 11.303 5.9811 11.4413 6.57246 11.4413C7.04862 11.4413 7.4787 11.3453 7.8627 11.1533C8.2467 10.9536 8.56158 10.6848 8.80734 10.3469C9.0531 10.0013 9.21822 9.61344 9.3027 9.18336H7.83966C7.73982 9.4752 7.57854 9.7056 7.35582 9.87456C7.14078 10.0435 6.87966 10.128 6.57246 10.128C6.26526 10.128 6.0003 10.055 5.77758 9.90912C5.55486 9.75552 5.37822 9.54432 5.24766 9.27552C5.12478 9.00672 5.06334 8.69568 5.06334 8.3424C5.06334 7.98912 5.12478 7.67808 5.24766 7.40928C5.37822 7.14048 5.55486 6.93312 5.77758 6.7872C6.0003 6.6336 6.26526 6.5568 6.57246 6.5568C6.8643 6.5568 7.11774 6.63744 7.33278 6.79872C7.54782 6.95232 7.7091 7.16736 7.81662 7.44384H9.29118C9.15294 6.79872 8.8419 6.27264 8.35806 5.8656C7.87422 5.45088 7.27902 5.24352 6.57246 5.24352C5.9811 5.24352 5.4627 5.3856 5.01726 5.66976C4.5795 5.94624 4.23774 6.32256 3.99198 6.79872C3.7539 7.2672 3.63486 7.78176 3.63486 8.3424C3.63486 8.90304 3.7539 9.42144 3.99198 9.8976C4.23774 10.3661 4.5795 10.7424 5.01726 11.0266ZM81.2356 11.064C81.3647 10.9754 81.4837 10.8773 81.5927 10.7696V11.2944H82.9866V3H81.5467V5.8885C81.4536 5.80176 81.3538 5.72213 81.2471 5.6496C80.8631 5.38848 80.4139 5.25792 79.8993 5.25792C79.354 5.25792 78.874 5.4 78.4593 5.68416C78.0446 5.96064 77.7259 6.30624 77.5027 6.72192C77.2795 7.1376 77.1679 7.63584 77.1679 8.21664C77.1679 8.79744 77.2795 9.29568 77.5027 9.71136C77.7259 10.127 78.0446 10.4726 78.4593 10.7491C78.874 11.0256 79.354 11.1638 79.8993 11.1638C80.4139 11.1638 80.8595 11.0309 81.2356 10.7652V11.064ZM79.8993 9.9792C79.6613 9.9792 79.4579 9.91008 79.2891 9.77184C79.1203 9.6336 78.9883 9.43872 78.8931 9.1872C78.7979 8.93568 78.7503 8.6448 78.7503 8.31456V8.11872C78.7503 7.78848 78.7979 7.4976 78.8931 7.24608C78.9883 6.99456 79.1203 6.79968 79.2891 6.66144C79.4579 6.5232 79.6613 6.45408 79.8993 6.45408C80.1373 6.45408 80.3407 6.5232 80.5095 6.66144C80.6783 6.79968 80.8103 6.99456 80.9055 7.24608C81.0007 7.4976 81.0483 7.78848 81.0483 8.11872V8.31456C81.0483 8.6448 81.0007 8.93568 80.9055 9.1872C80.8103 9.43872 80.6783 9.6336 80.5095 9.77184C80.3407 9.91008 80.1373 9.9792 79.8993 9.9792Z"/></svg>
               Content Credentials
            </h3>
            
            <div class="section">
                <div class="label">Issuer</div>
                <div class="value">${issuer}</div>
            </div>

            <div class="section">
                <div class="label">Issued On</div>
                <div class="value">${time}</div>
            </div>

            <div class="section">
                <div class="label">Produced With</div>
                <div class="value">${generator}</div>
            </div>
            
            ${actionsList.length > 0 ? html`
                <div class="section">
                    <div class="label">Actions</div>
                    <div class="value">
                        ${actionsList.map(action => html`<div>• ${action}</div>`)}
                    </div>
                </div>
            ` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }
}

customElements.define('content-credentials-viewer', ContentCredentialsViewer);