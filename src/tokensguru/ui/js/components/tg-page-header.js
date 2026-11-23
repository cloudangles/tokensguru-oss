import { h } from "../dom.js";
import { icon } from "../icons.js";
import { copyText } from "./tg-code-block.js";

export class TgPageHeader extends HTMLElement {
  set heading(value) {
    this._heading = value;
    if (this.isConnected) this.render();
  }

  get heading() {
    return this._heading || this.getAttribute("heading") || "";
  }

  connectedCallback() {
    this.render();
  }

  pageText() {
    const content = this.closest(".content");
    return content ? content.innerText : this.heading;
  }

  render() {
    const label = h("span", {}, "Copy page");
    const main = h("button", { type: "button", class: "split-main" }, icon("copy", 16), label);
    main.addEventListener("click", async () => {
      const copied = await copyText(this.pageText());
      label.textContent = copied ? "Copied" : "Copy failed";
      setTimeout(() => (label.textContent = "Copy page"), 1500);
    });
    const menu = document.createElement("tg-dropdown");
    menu.setAttribute("aria-label", "More copy options");
    menu.setAttribute("align", "end");
    menu.items = [
      { label: "Copy page text", icon: "copy", onClick: () => copyText(this.pageText()) },
      { label: "Copy link to this page", icon: "external", onClick: () => copyText(window.location.href) },
    ];
    this.replaceChildren(h("div", { class: "page-header" }, h("h1", {}, this.heading), h("div", { class: "split" }, main, menu)));
  }
}

customElements.define("tg-page-header", TgPageHeader);
