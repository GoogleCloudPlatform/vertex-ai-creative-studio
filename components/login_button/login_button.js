import { LitElement, html, css } from 'https://esm.sh/lit';

class LoginButton extends LitElement {
  static get properties() {
    return {
      label: { type: String },
      password: { type: String },
      loading: { type: Boolean },
      error: { type: String },
    };
  }

  constructor() {
    super();
    this.label = 'Login';
    this.password = '';
    this.loading = false;
    this.error = '';
  }

  static styles = css`
    button {
      width: 100%;
      padding: 12px 24px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      background: var(--mat-sys-color-primary, #1a73e8);
      color: var(--mat-sys-color-on-primary, #fff);
      font-size: 14px;
    }
    .error-message {
      color: var(--mat-sys-color-error, #B00020);
      font-size: 12px;
      margin-top: 8px;
    }
  `;

  async _handleClick() {
    if (!this.password) {
      this.error = 'Please enter a password';
      return;
    }
    this.loading = true;
    this.error = '';
    try {
      // Prefer JSON POST so we can handle 401 without leaving the page
      const resp = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ password: this.password }),
      });

      if (!resp.ok) {
        let message = 'Invalid password';
        try {
          const data = await resp.json();
          message = data?.detail || data?.message || message;
        } catch (_) {}
        this.error = message;
        return;
      }

      // Success: cookie set by server, go to home
      window.location.assign('/home');
    } catch (e) {
      console.error('Login failed', e);
      this.error = e?.message || 'Login failed';
    } finally {
      this.loading = false;
    }
  }

  render() {
    return html`
      <button @click=${this._handleClick} ?disabled=${this.loading}>
        ${this.loading ? 'Loading…' : this.label}
      </button>
      ${this.error ? html`<div class="error-message">${this.error}</div>` : ''}
    `;
  }
}

customElements.define('login-button', LoginButton);


