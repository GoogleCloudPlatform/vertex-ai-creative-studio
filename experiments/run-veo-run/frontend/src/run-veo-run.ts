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
import { customElement, state } from 'lit/decorators.js';
import '@material/web/button/filled-button.js';
import '@material/web/button/text-button.js';
import '@material/web/icon/icon.js';
import '@material/web/iconbutton/icon-button.js';
import '@material/web/progress/linear-progress.js';
import '@material/web/textfield/filled-text-field.js';
import '@material/web/checkbox/checkbox.js';
import '@material/web/dialog/dialog.js';
import '@material/web/select/outlined-select.js';
import '@material/web/select/select-option.js';
import '@material/web/tabs/tabs.js';
import '@material/web/tabs/primary-tab.js';
import type { MdDialog } from '@material/web/dialog/dialog.js';
import { generateVideo, extendVideo } from './api/veo';
import { analyzeVideo } from './api/gemini';
import './components/image-upload';
import './components/video-upload';
import type { UploadResult } from './components/image-upload';

type GenMode = 'text' | 'image' | 'storyboard' | 'ingredients' | 'video-upload';

@customElement('run-veo-run')
export class RunVeoRun extends LitElement {
  @state() private isRunning = false;
  @state() private statusMessage = '';
  @state() private timer = 0;
  @state() private videoUri = '';
  @state() private sourceUri = ''; // gs:// URI for extension
  @state() private prompt = 'A futuristic cyberpunk runner sprinting through neon streets, industrial techno vibe';
  @state() private error = '';
  
  @state() private selectedModel = 'veo-3.1-fast-generate-preview';
  @state() private selectedAspectRatio = '16:9';
  @state() private useContinuity = true;
  @state() private genMode: GenMode = 'text';
  @state() private startImageUri = '';
  @state() private lastImageUri = '';
  @state() private refImageUris: string[] = [];

  static styles = css`
    :host {
      display: block;
      background-color: var(--md-sys-color-background);
      padding: 2rem;
      height: 100vh;
      box-sizing: border-box;
      color: var(--md-sys-color-on-background);
    }
    
    .header {
      font-family: var(--md-ref-typeface-brand);
      font-size: 3rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 2rem;
      color: var(--md-sys-color-primary);
      text-shadow: 2px 2px 0px #000;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }

    .indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        color: var(--md-sys-color-primary);
        cursor: help;
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    video {
      width: 100%;
      border: 2px solid var(--md-sys-color-primary);
      background: #000;
    }

    .controls-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .continuity-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.9rem;
      color: var(--md-sys-color-on-background);
    }

    .timer {
      font-family: 'JetBrains Mono', monospace;
      font-size: 1.5rem;
      color: var(--md-sys-color-error);
      text-align: center;
      margin-top: 10px;
    }

    .error {
      color: var(--md-sys-color-error);
      font-family: 'JetBrains Mono', monospace;
      padding: 10px;
      border: 1px solid var(--md-sys-color-error);
    }

    md-dialog {
      --md-dialog-container-color: var(--md-sys-color-surface);
    }
    
    md-tabs {
        --md-sys-color-surface: var(--md-sys-color-background);
    }

    .uploads {
        display: flex;
        gap: 10px;
    }
    .uploads > * {
        flex: 1;
    }
    
    .aspect-warning {
        color: var(--md-sys-color-error);
        font-size: 0.8rem;
        margin-top: 4px;
    }
  `;

  render() {
    const isFast = this.selectedModel.includes('fast');
    const modelLabel = isFast ? 'Veo 3.1 Fast' : 'Veo 3.1 Standard';
    const modelIcon = isFast ? 'speed' : 'high_quality';
    
    const isLandscape = this.selectedAspectRatio === '16:9';
    const ratioLabel = isLandscape ? 'Landscape (16:9)' : 'Portrait (9:16)';
    const ratioIcon = isLandscape ? 'crop_landscape' : 'crop_portrait';

    return html`
      <div class="container">
        <div class="header">
          <span>Run Veo Run</span>
          <div class="header-actions">
            <div class="indicator" title="${modelLabel}">
                <md-icon>${modelIcon}</md-icon>
            </div>
            <div class="indicator" title="${ratioLabel}">
                <md-icon>${ratioIcon}</md-icon>
            </div>
            <md-icon-button @click="${this.openInfo}">
              <md-icon>info</md-icon>
            </md-icon-button>
            <md-icon-button @click="${this.openSettings}">
              <md-icon>settings</md-icon>
            </md-icon-button>
          </div>
        </div>
        
        ${this.videoUri ? html`
          <video src="${this.videoUri}" controls autoplay loop></video>
        ` : ''}

        ${!this.sourceUri ? html`
          <md-tabs 
            .activeTabIndex="${this.getTabIndex()}"
            @change="${this.handleTabChange}">
            <md-primary-tab>Text</md-primary-tab>
            <md-primary-tab>Image</md-primary-tab>
            <md-primary-tab>Storyboard</md-primary-tab>
            <md-primary-tab>Ingredients</md-primary-tab>
            <md-primary-tab>Upload</md-primary-tab>
          </md-tabs>
        ` : ''}

        <div class="uploads">
            ${(this.genMode === 'image' || this.genMode === 'storyboard') && !this.sourceUri ? html`
            <image-upload 
                label="Start Frame"
                @upload-complete="${this.handleImageUpload}">
            </image-upload>
            ` : ''}

            ${this.genMode === 'storyboard' && !this.sourceUri ? html`
            <image-upload 
                label="End Frame"
                @upload-complete="${this.handleLastFrameUpload}">
            </image-upload>
            ` : ''}

            ${this.genMode === 'ingredients' && !this.sourceUri ? html`
            <image-upload 
                label="Asset 1"
                @upload-complete="${(e: CustomEvent<UploadResult>) => this.handleRefUpload(e, 0)}">
            </image-upload>
            <image-upload 
                label="Asset 2"
                @upload-complete="${(e: CustomEvent<UploadResult>) => this.handleRefUpload(e, 1)}">
            </image-upload>
            <image-upload 
                label="Asset 3"
                @upload-complete="${(e: CustomEvent<UploadResult>) => this.handleRefUpload(e, 2)}">
            </image-upload>
            ` : ''}

            ${this.genMode === 'video-upload' && !this.sourceUri ? html`
            <video-upload
                label="Upload Video to Extend"
                @upload-complete="${this.handleVideoUpload}">
            </video-upload>
            ` : ''}
        </div>

        <md-filled-text-field
          label="${this.sourceUri ? 'Extension Prompt' : 'Prompt'}"
          type="textarea"
          rows="3"
          .value="${this.prompt}"
          @input="${(e: Event) => this.prompt = (e.target as HTMLInputElement).value}"
          ?disabled="${this.isRunning}">
        </md-filled-text-field>

        ${this.sourceUri ? html`
          <div class="controls-row">
            <div class="continuity-toggle">
              <md-checkbox 
                touch-target="wrapper" 
                ?checked="${this.useContinuity}"
                @change="${(e: Event) => this.useContinuity = (e.target as HTMLInputElement).checked}">
              </md-checkbox>
              <span>Enhance with Context Analysis</span>
            </div>
          </div>
        ` : ''}

        ${this.error ? html`<div class="error">${this.error}</div>` : ''}

        <md-filled-button 
          @click="${this.handleRun}"
          ?disabled="${this.isRunDisabled()}"
          style="width: 100%; height: 60px; font-size: 1.2rem;">
          ${this.isRunning 
            ? (this.statusMessage || 'PROCESSING...') 
            : (this.sourceUri ? 'EXTEND TIMELINE' : 'RUN SIMULATION')}
          <md-icon slot="icon">
            ${this.isRunning ? 'hourglass_empty' : 'play_arrow'}
          </md-icon>
        </md-filled-button>

        ${this.isRunning ? html`
          <div>
            <md-linear-progress indeterminate></md-linear-progress>
            <div class="timer">T+${this.timer.toFixed(2)}s</div>
          </div>
        ` : ''}

        ${this.sourceUri && !this.isRunning ? html`
            <md-text-button @click="${this.reset}">RESET TIMELINE</md-text-button>
        ` : ''}
      </div>

      <md-dialog id="settings-dialog">
        <div slot="headline">Simulation Settings</div>
        <form slot="content" id="settings-form" method="dialog" style="display: flex; flex-direction: column; gap: 16px;">
          <md-outlined-select
            label="Veo Model"
            .value="${this.selectedModel}"
            @change="${(e: Event) => this.selectedModel = (e.target as HTMLSelectElement).value}">
            <md-select-option value="veo-3.1-fast-generate-preview">
              <div slot="headline">Veo 3.1 Fast (Preview)</div>
            </md-select-option>
            <md-select-option value="veo-3.1-generate-preview">
              <div slot="headline">Veo 3.1 Standard (Preview)</div>
            </md-select-option>
          </md-outlined-select>

          <div>
              <md-outlined-select
                label="Aspect Ratio"
                .value="${this.selectedAspectRatio}"
                @change="${(e: Event) => this.selectedAspectRatio = (e.target as HTMLSelectElement).value}"
                ?disabled="${this.genMode === 'ingredients' || !!this.sourceUri}">
                <md-select-option value="16:9">
                  <div slot="headline">16:9 (Landscape)</div>
                </md-select-option>
                <md-select-option value="9:16">
                  <div slot="headline">9:16 (Portrait)</div>
                </md-select-option>
              </md-outlined-select>
              ${this.genMode === 'ingredients' ? html`
                <div class="aspect-warning">Aspect Ratio locked to 16:9 in Ingredients mode.</div>
              ` : ''}
              ${!!this.sourceUri ? html`
                <div class="aspect-warning">Aspect Ratio locked during extension.</div>
              ` : ''}
          </div>
        </form>
        <div slot="actions">
          <md-text-button form="settings-form" value="close">Close</md-text-button>
        </div>
      </md-dialog>

      <md-dialog id="info-dialog">
        <div slot="headline">About Run, Veo, Run</div>
        <div slot="content">
          <p>
            <b>Run, Veo, Run</b> is a sequential video generation experiment inspired by the kinetic energy of "Run, Lola, Run".
          </p>
          <p>
            It uses <b>Vertex AI Veo 3.1</b> to extend video clips up through 30 seconds.
            When "Enhance with Context Analysis" is enabled, <em>Gemini 3</em> analyzes the previous clip to ensure visual style and character consistency in the next segment.
          </p>
          <p>
            <em>The ball is round. The game lasts 90 minutes. Everything else is pure theory.</em>
          </p>
        </div>
        <div slot="actions">
          <md-text-button @click="${this.closeInfo}">Close</md-text-button>
        </div>
      </md-dialog>
    `;
  }

  private getTabIndex() {
      switch(this.genMode) {
          case 'text': return 0;
          case 'image': return 1;
          case 'storyboard': return 2;
          case 'ingredients': return 3;
          case 'video-upload': return 4;
          default: return 0;
      }
  }

  private handleTabChange(e: Event) {
      const tabs = e.target as any; 
      if (tabs.activeTabIndex === 0) this.genMode = 'text';
      else if (tabs.activeTabIndex === 1) this.genMode = 'image';
      else if (tabs.activeTabIndex === 2) this.genMode = 'storyboard';
      else if (tabs.activeTabIndex === 3) {
          this.genMode = 'ingredients';
          // Ingredients requires Standard model and 16:9
          if (this.selectedModel === 'veo-3.1-fast-generate-preview') {
              this.selectedModel = 'veo-3.1-generate-preview';
          }
          if (this.selectedAspectRatio === '9:16') {
              this.selectedAspectRatio = '16:9';
          }
      }
      else this.genMode = 'video-upload';
  }

  private handleImageUpload(e: CustomEvent<UploadResult>) {
      this.startImageUri = e.detail.uri;
  }

  private handleLastFrameUpload(e: CustomEvent<UploadResult>) {
      this.lastImageUri = e.detail.uri;
  }
  
  private handleVideoUpload(e: CustomEvent<UploadResult>) {
      // Set the uploaded video as the source for extension
      this.sourceUri = e.detail.uri;
      this.videoUri = e.detail.signedUri;
      // Also switch tab context if needed, but the UI should update due to sourceUri check
  }

  private handleRefUpload(e: CustomEvent<UploadResult>, index: number) {
      const newRefs = [...this.refImageUris];
      newRefs[index] = e.detail.uri;
      this.refImageUris = newRefs;
  }

  private isRunDisabled() {
      if (this.isRunning) return true;
      if (this.sourceUri) return false; 
      
      if (this.genMode === 'image' && !this.startImageUri) return true;
      if (this.genMode === 'storyboard' && (!this.startImageUri || !this.lastImageUri)) return true;
      if (this.genMode === 'ingredients' && this.refImageUris.filter(u => u).length === 0) return true;
      if (this.genMode === 'video-upload' && !this.sourceUri) return true;

      return false;
  }

  private openSettings() {
    const dialog = this.shadowRoot?.querySelector('#settings-dialog') as MdDialog;
    dialog.show();
  }

  private openInfo() {
    const dialog = this.shadowRoot?.querySelector('#info-dialog') as MdDialog;
    dialog.show();
  }

  private closeInfo() {
    const dialog = this.shadowRoot?.querySelector('#info-dialog') as MdDialog;
    dialog.close();
  }

  private async handleRun() {
    if (!this.prompt) return;

    this.isRunning = true;
    this.error = '';
    this.timer = 0;
    this.startTimer();

    try {
      let finalPrompt = this.prompt;
      
      // Continuity Analysis Phase
      if (this.sourceUri && this.useContinuity) {
        this.statusMessage = 'ANALYZING CONTEXT...';
        try {
          const analysis = await analyzeVideo(this.sourceUri);
          console.log('Context:', analysis.context);
          finalPrompt = `${this.prompt} 

[Visual Context: ${analysis.context}]`;
        } catch (e) {
          console.warn('Analysis failed, proceeding with raw prompt', e);
        }
      }

      // Generation Phase
      this.statusMessage = this.sourceUri ? 'EXTENDING TIMELINE...' : 'RUNNING SIMULATION...';
      
      let result;
      if (this.sourceUri) {
        result = await extendVideo(this.sourceUri, finalPrompt, this.selectedModel);
      } else {
        const validRefs = this.refImageUris.filter(u => u);
        result = await generateVideo({
            prompt: finalPrompt,
            model: this.selectedModel,
            aspectRatio: this.selectedAspectRatio,
            imageUri: (this.genMode === 'image' || this.genMode === 'storyboard') ? this.startImageUri : undefined,
            lastFrameUri: (this.genMode === 'storyboard') ? this.lastImageUri : undefined,
            refImageUris: (this.genMode === 'ingredients') ? validRefs : undefined,
            refImageTypes: (this.genMode === 'ingredients') ? validRefs.map(() => 'ASSET') : undefined
        });
      }
      
      this.videoUri = result.videoUri;
      if ('sourceUri' in result) {
          // @ts-ignore
          this.sourceUri = result.sourceUri;
      }
    } catch (e: any) {
      this.error = e.message;
    } finally {
      this.isRunning = false;
      this.statusMessage = '';
    }
  }

  private reset() {
    this.videoUri = '';
    this.sourceUri = '';
    this.prompt = 'A futuristic cyberpunk runner sprinting through neon streets, industrial techno vibe';
    this.error = '';
    this.useContinuity = true;
    this.genMode = 'text';
    this.startImageUri = '';
    this.lastImageUri = '';
    this.refImageUris = [];
    this.selectedAspectRatio = '16:9'; // Reset aspect ratio
  }

  private startTimer() {
    const startTime = Date.now();
    const interval = setInterval(() => {
        if (!this.isRunning) {
            clearInterval(interval);
            return;
        }
        this.timer = (Date.now() - startTime) / 1000;
    }, 10);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'run-veo-run': RunVeoRun;
  }
}