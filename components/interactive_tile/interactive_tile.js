import { LitElement, css, html } from 'https://esm.sh/lit';
import { styleMap } from 'https://esm.sh/lit/directives/style-map.js';
import { SvgIcon } from '../svg_icon/svg_icon.js';

class InteractiveTile extends LitElement {
  // -- Define properties received from Python --
  static properties = {
    label: { type: String },
    icon: { type: String },
    description: { type: String },
    route: { type: String },
    videoUrl: { type: String },
    videoObjectPosition: { type: String },
    defaultBgColor: { type: String },
    defaultTextColor: { type: String },
    hoverBgColor: { type: String },
    hoverTextColor: { type: String },
    tileClickEvent: { type: String },
    isHovered: { state: true },
  };

  // -- Constructor --
  constructor() {
    super();
    this.label = '';
    this.icon = '';
    this.description = '';
    this.route = '';
    this.videoUrl = '';
    this.videoObjectPosition = 'center';
    this.defaultBgColor = '';
    this.defaultTextColor = '';
    this.hoverBgColor = '';
    this.hoverTextColor = '';
    this.tileClickEvent = '';
    this.isHovered = false;
  }

  // -- Event Handlers --
  handleMouseOver() { this.isHovered = true; }
  handleMouseOut() { this.isHovered = false; }
  handleClick() {
    if (!this.tileClickEvent) {
      console.error('Mesop event handler ID for tileClickEvent is not set.');
      return;
    }
    this.dispatchEvent(new MesopEvent(this.tileClickEvent, { route: this.route }));
  }

  // -- Styles --
  static styles = css`
    :host {
      display: block;
      cursor: pointer;
      font-family: 'Google Sans', 'Helvetica Neue', sans-serif;
    }
    .card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      width: 160px;
      height: 160px;
      padding: 16px;
      border-radius: 12px;
      border: 1px solid var(--mesop-theme-outline-variant, #ccc);
      transition: all 0.2s ease-in-out;
      box-sizing: border-box;
      background-size: cover;
      background-position: center;
      overflow: hidden;
      position: relative;
    }
    .icon-container {
      width: 48px;
      height: 48px;
      margin-bottom: 12px;
    }
    .icon-container svg-icon {
      width: 100%;
      height: 100%;
    }
    .label { font-weight: 500; }
    .description { font-size: 0.9em; }
    .hover-label {
      font-weight: bold;
      font-size: 1.1em;
      margin-bottom: 12px;
    }
    .content-container {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
      z-index: 2;
      position: relative;
      border-radius: 12px;
    }
    .background-video {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      z-index: 1;
    }

    /* --- New styles for stable hover effect --- */
    .card .hover-label, .card .description {
      display: none;
    }
    .card.is-hovered .icon-container, .card.is-hovered .label {
      display: none;
    }
    .card.is-hovered .hover-label, .card.is-hovered .description {
      display: block;
    }
  `;

  // -- Render method --
  render() {
    const hasVideo = this.videoUrl && this.videoUrl.length > 0;

    const cardStyles = {};
    if (hasVideo) {
      cardStyles.color = 'white';
    } else {
      cardStyles.backgroundColor = this.isHovered ? this.hoverBgColor : this.defaultBgColor;
      cardStyles.color = this.isHovered ? this.hoverTextColor : this.defaultTextColor;
    }

    const contentContainerStyles = {
      backgroundColor: hasVideo ? 'rgba(0, 0, 0, 0.15)' : 'transparent',
      textShadow: hasVideo ? '1px 1px 2px rgba(0,0,0,0.7)' : 'none',
    };

    const videoStyles = {
      objectPosition: this.videoObjectPosition,
    };

    return html`
      <div
        class="card ${this.isHovered ? 'is-hovered' : ''}"
        style=${styleMap(cardStyles)}
        @mouseover=${this.handleMouseOver}
        @mouseout=${this.handleMouseOut}
        @click=${this.handleClick}
      >
        ${hasVideo
          ? html`<video class="background-video" style=${styleMap(videoStyles)} autoplay loop muted playsinline .src=${this.videoUrl}></video>`
          : ''
        }

        <div class="content-container" style=${styleMap(contentContainerStyles)}>
          <!-- All elements are now always present in the HTML -->
          <div class="icon-container">
            <svg-icon .iconName=${this.icon}></svg-icon>
          </div>
          <div class="label">${this.label}</div>
          <div class="hover-label">${this.label}</div>
          <div class="description">${this.description}</div>
        </div>
      </div>
    `;
  }
}

customElements.define('interactive-tile', InteractiveTile);