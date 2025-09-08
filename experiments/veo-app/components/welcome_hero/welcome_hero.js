import { LitElement, css, html } from 'https://esm.sh/lit';
import { SvgIcon } from '../svg_icon/svg_icon.js';

class WelcomeHero extends LitElement {
  static properties = {
    title: { type: String },
    subtitle: { type: String },
    videoUrl: { type: String },
    tiles: { type: String }, // Expecting a JSON string for the tiles
    tileClickEvent: { type: String },
  };

  constructor() {
    super();
    this.title = '';
    this.subtitle = '';
    this.videoUrl = '';
    this.tiles = '[]';
    this.tileClickEvent = '';
  }

  handleClick(route) {
    if (!this.tileClickEvent) {
      console.error('Mesop event handler ID for tileClickEvent is not set.');
      return;
    }
    this.dispatchEvent(new MesopEvent(this.tileClickEvent, { route }));
  }

  static styles = css`
    :host {
      display: block;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      position: fixed;
      top: 0;
      left: 0;
    }
    .hero-container {
      width: 100%;
      height: 100%;
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: white;
      font-family: 'Google Sans', 'Helvetica Neue', sans-serif;
    }
    .background-video {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      min-width: 100%;
      min-height: 100%;
      width: auto;
      height: auto;
      z-index: 1;
    }
    .overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.5);
      z-index: 2;
    }
    .content {
      z-index: 3;
      text-align: center;
      padding: 0 2rem;
    }
    h1 {
      font-size: 4rem;
      font-weight: 500;
      margin-bottom: 1rem;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .subtitle {
      font-size: 1.25rem;
      font-weight: 300;
      max-width: 600px;
      margin: 0 auto 2.5rem auto;
      line-height: 1.5;
      text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    .tiles-container {
      display: flex;
      gap: 1.5rem;
      align-items: center;
    }
    .tile {
      background-color: rgba(255, 255, 255, 0.15);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 999px; /* Lozenge shape */
      padding: 0.75rem 1.5rem;
      cursor: pointer;
      transition: background-color 0.2s ease-in-out;
      font-size: 1.1rem;
      font-weight: 500;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px; /* Add gap for icon and label */
    }
    .tile:hover {
      background-color: rgba(255, 255, 255, 0.3);
    }
    .tile.no-border {
      border-color: transparent;
      background-color: transparent;
    }
    .tile.no-border:hover {
      background-color: rgba(255, 255, 255, 0.15);
    }
    .icon-wrapper {
      width: 24px;
      height: 24px;
    }
    .icon-wrapper svg-icon {
      width: 100%;
      height: 100%;
    }
  `;

  render() {
    let parsedTiles = [];
    try {
      parsedTiles = JSON.parse(this.tiles);
    } catch (e) {
      console.error('Failed to parse tiles JSON:', e);
    }

    return html`
      <div class="hero-container">
        <video class="background-video" autoplay loop muted playsinline .src=${this.videoUrl}></video>
        <div class="overlay"></div>
        <div class="content">
          <h1>${this.title}</h1>
          <p class="subtitle">${this.subtitle}</p>
          <div class="tiles-container">
            ${parsedTiles.map(
              (tile) => html`
                <div 
                  class="tile ${tile.border === false ? 'no-border' : ''}" 
                  @click=${() => this.handleClick(tile.route)}
                >
                  ${tile.icon
                    ? html`<div class="icon-wrapper"><svg-icon .iconName=${tile.icon}></svg-icon></div>`
                    : ''}
                  ${tile.label ? html`<span>${tile.label}</span>` : ''}
                </div>
              `
            )}
          </div>
        </div>
      </div>
    `;
  }
}

customElements.define('welcome-hero', WelcomeHero);
