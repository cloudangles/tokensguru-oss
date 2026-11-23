import { h } from "../dom.js";
import { icon } from "../icons.js";

const ICONS = { info: "info", tip: "bulb", warning: "warning" };

export class TgCallout extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    const type = ICONS[this.getAttribute("type")] ? this.getAttribute("type") : "info";
    const children = [...this.childNodes];
    this.setAttribute("role", "note");
    this.dataset.type = type;
    this.replaceChildren(h("span", { class: "callout-icon" }, icon(ICONS[type], 20)), h("div", { class: "callout-body" }, children));
  }
}

customElements.define("tg-callout", TgCallout);
