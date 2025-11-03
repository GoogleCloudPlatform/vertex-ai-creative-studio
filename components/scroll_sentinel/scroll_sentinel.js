import { LitElement, css, html } from "https://esm.sh/lit";

class ScrollSentinel extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100px; /* Give it some space to be observed */
      display: flex;
      justify-content: center;
      align-items: center;
    }
  `;

  static get properties() {
    return {
      isLoading: { type: Boolean },
      allItemsLoaded: { type: Boolean },
      visible: { type: String }, // Event handler ID
    };
  }

  constructor() {
    super();
    this.isLoading = false;
    this.allItemsLoaded = false;
    this.visible = "";
    this.observer = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this.observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !this.isLoading && !this.allItemsLoaded) {
        if (this.visible) {
          this.dispatchEvent(new MesopEvent(this.visible, {}));
        }
      }
    });
    this.observer.observe(this);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  render() {
    if (this.isLoading) {
      return html`<p>Loading...</p>`;
    }
    if (this.allItemsLoaded) {
      return html`<p>End of list</p>`;
    }
    return html``; // Otherwise, be invisible
  }
}

customElements.define("scroll-sentinel", ScrollSentinel);
