import { h } from "../dom.js";
import { icon } from "../icons.js";

export class TgCard extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    const href = this.getAttribute("href") || "#/";
    const external = /^https?:/.test(href);
    const children = [...this.childNodes];
    const cta = this.getAttribute("cta");
    this.replaceChildren(
      h(
        "a",
        { class: "card-link", href, target: external ? "_blank" : null, rel: external ? "noopener noreferrer" : null },
        this.getAttribute("icon") ? h("span", { class: "card-icon" }, icon(this.getAttribute("icon"), 24)) : null,
        h("h3", {}, this.getAttribute("heading") || ""),
        h("div", { class: "card-body" }, children),
        cta ? h("span", { class: "card-cta" }, cta, icon("chevron-right", 14)) : null,
      ),
    );
  }
}

customElements.define("tg-card", TgCard);
