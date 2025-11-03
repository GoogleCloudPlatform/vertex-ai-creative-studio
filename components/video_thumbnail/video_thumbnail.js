import { LitElement, css, html } from 'https://esm.sh/lit';

class VideoThumbnail extends LitElement {
  static properties = {
    videoSrc: { type: String },
    selected: { type: Boolean },
    thumbnailClick: { type: String },
  };

  constructor() {
    super();
    this.videoSrc = '';
    this.selected = false;
  }

  handleMouseOver(e) { e.currentTarget.querySelector('video')?.play(); }
  handleMouseOut(e) {
    const video = e.currentTarget.querySelector('video');
    if (video) {
      video.pause();
      video.currentTime = 0;
    }
  }

  handleClick() {
    if (this.thumbnailClick) {
      this.dispatchEvent(new MesopEvent(this.thumbnailClick, {}));
    }
  }

  static styles = css`
    .wrapper {
      width: 100%;
      height: 100%;
      display: inline-block;
      position: relative;
      cursor: pointer;
      border-radius: 12px;
      padding: 4px;
      background-clip: content-box;
      transition: background-color 0.2s ease-in-out;
      background-color: transparent;
      box-sizing: border-box;
    }
    .wrapper.selected {
      background-color: var(--mesop-theme-primary, #6200EE);
    }
    video {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover; /* Ensures video covers the area without distortion */
      border-radius: 8px;
    }
  `;

  render() {
    return html`
      <div
        class="wrapper ${this.selected ? 'selected' : ''}"
        @mouseover=${this.handleMouseOver}
        @mouseout=${this.handleMouseOut}
        @click=${this.handleClick}
      >
        <video .src=${this.videoSrc} muted loop playsinline></video>
      </div>
    `;
  }
}

customElements.define('video-thumbnail', VideoThumbnail);