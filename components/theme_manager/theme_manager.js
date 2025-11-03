import { LitElement } from 'https://esm.sh/lit';

class ThemeManager extends LitElement {
  static get properties() {
    return {
      theme: { type: String },
      themeLoaded: { type: String },
    };
  }

  constructor() {
    super();
    this.theme = '';
  }

  connectedCallback() {
    super.connectedCallback();
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme) {
      this.dispatchEvent(new MesopEvent(this.themeLoaded, { theme: storedTheme }));
    }
  }

  updated(changedProperties) {
    if (changedProperties.has('theme') && this.theme) {
      localStorage.setItem('theme', this.theme);
    }
  }

  render() {
    // This component is non-visual
    return '';
  }
}

customElements.define('theme-manager', ThemeManager);