import { h } from "../dom.js";
import { icon } from "../icons.js";
import { LINKS } from "../nav.js";
import { readFlag, writeFlag } from "../prefs.js";

const KEY = "tokensguru-docs-banner-dismissed-v2";

export class TgBanner extends HTMLElement {
  connectedCallback() {
    if (readFlag(KEY)) {
      this.hidden = true;
      return;
    }
    const close = h("button", { type: "button", class: "banner-close", "aria-label": "Dismiss announcement" }, icon("x", 18));
    close.addEventListener("click", () => {
      writeFlag(KEY);
      this.hidden = true;
    });
    this.replaceChildren(
      h(
        "div",
        { class: "banner", role: "region", "aria-label": "Announcement" },
        h(
          "p",
          {},
          h("span", { class: "banner-badge" }, "Open source"),
          h("span", { class: "banner-text" }, "tokensguru is free and open source. Need more cloud features or enterprise-level support? "),
          h("a", { class: "banner-cta", href: LINKS.contact }, "Contact us", icon("chevron-right", 14)),
        ),
        close,
      ),
    );
  }
}

customElements.define("tg-banner", TgBanner);
