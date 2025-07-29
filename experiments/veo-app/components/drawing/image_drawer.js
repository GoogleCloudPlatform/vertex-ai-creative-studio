import { LitElement, html, css } from 'https://esm.sh/lit';

export class ImageDrawer extends LitElement {
  static properties = {
    imageUrl: { type: String },
    penColor: { type: String },
    penWidth: { type: Number },
    isDrawing: { state: true },
    lastX: { state: true },
    lastY: { state: true },
  };

  constructor() {
    super();
    this.imageUrl = '';
    this.penColor = '#ff0000';
    this.penWidth = 4;
    this.isDrawing = false;
    this.lastX = 0;
    this.lastY = 0;
    this.canvas = null;
    this.ctx = null;
  }

  static styles = css`
    :host {
      display: block;
      border: 2px dashed #ccc;
      padding: 1rem;
      font-family: sans-serif;
    }
    .controls {
      display: flex;
      gap: 1rem;
      align-items: center;
      margin-bottom: 1rem;
    }
    .controls label {
      font-weight: bold;
    }
    canvas {
      cursor: crosshair;
      border: 1px solid #000;
    }
  `;

  firstUpdated() {
    this.canvas = this.shadowRoot.querySelector('#drawing-canvas');
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
    this.setupDrawingListeners();
  }

  updated(changedProperties) {
    if (changedProperties.has('imageUrl') && this.imageUrl) {
      this.loadImageAndDraw();
    }
  }

  async loadImageAndDraw() {
    const response = await fetch(`/api/get_signed_url?gcs_uri=${this.imageUrl}`);
    const data = await response.json();
    const signedUrl = data.signed_url;

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = signedUrl;
    
    img.onload = () => {
      this.canvas.width = img.width;
      this.canvas.height = img.height;
      this.ctx.drawImage(img, 0, 0, img.width, img.height);
    };
    img.onerror = () => {
        console.error(`Failed to load image: ${this.imageUrl}`);
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }

  setupDrawingListeners() {
    this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
    this.canvas.addEventListener('mousemove', (e) => this.draw(e));
    this.canvas.addEventListener('mouseup', () => this.stopDrawing());
    this.canvas.addEventListener('mouseout', () => this.stopDrawing());
  }
  
  startDrawing(e) {
    this.isDrawing = true;
    [this.lastX, this.lastY] = [e.offsetX, e.offsetY];
  }

  stopDrawing() {
    this.isDrawing = false;
  }
  
  draw(e) {
    if (!this.isDrawing) return;

    this.ctx.strokeStyle = this.penColor;
    this.ctx.lineWidth = this.penWidth;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    this.ctx.beginPath();
    this.ctx.moveTo(this.lastX, this.lastY);
    this.ctx.lineTo(e.offsetX, e.offsetY);
    this.ctx.stroke();

    [this.lastX, this.lastY] = [e.offsetX, e.offsetY];
  }

  getResultAsDataUrl() {
    return this.canvas.toDataURL('image/png');
  }

  clearDrawing() {
      this.loadImageAndDraw();
  }

  render() {
    return html`
      <div class="controls">
        <label for="pen-color">Pen Color:</label>
        <input 
          type="color" 
          id="pen-color" 
          .value=${this.penColor}
          @input=${(e) => this.penColor = e.target.value}
        >
        
        <label for="pen-width">Pen Width:</label>
        <input 
          type="range" 
          id="pen-width" 
          min="1" 
          max="50" 
          .value=${this.penWidth}
          @input=${(e) => this.penWidth = e.target.value}
        >
        <span>${this.penWidth}px</span>

        <button @click=${this.clearDrawing}>Clear</button>
      </div>

      <canvas id="drawing-canvas"></canvas>
    `;
  }
}

customElements.define('image-drawer', ImageDrawer);