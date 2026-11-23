import { h } from "../dom.js";
import { icon } from "../icons.js";
import { applyTheme, nextTheme, storedTheme } from "../prefs.js";

const ICONS = { system: "monitor", light: "sun", dark: "moon" };

export class TgThemeToggle extends HTMLElement {
  connectedCallback() {
    this.theme = storedTheme();
    this.button = h("button", { type: "button", class: "icon-button" });
    this.button.addEventListener("click", () => {
      this.theme = nextTheme(this.theme);
      applyTheme(this.theme);
      this.render();
    });
    this.replaceChildren(this.button);
    this.render();
  }

  render() {
    const label = `Theme: ${this.theme}. Click to change.`;
    this.button.setAttribute("aria-label", label);
    this.button.setAttribute("title", label);
    this.button.replaceChildren(icon(ICONS[this.theme], 16));
  }
}

customElements.define("tg-theme-toggle", TgThemeToggle);
