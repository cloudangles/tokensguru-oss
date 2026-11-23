import { h } from "../dom.js";
import { icon } from "../icons.js";
import { LINKS } from "../nav.js";
import { currentOptimizers, onSectionsChange } from "../nav-state.js";
import { optimizerIcon } from "../icons.js";

const isMac = /Mac|iPhone|iPad/.test(navigator.platform || "");

export class TgNavbar extends HTMLElement {
  connectedCallback() {
    const menuButton = h("button", { type: "button", class: "icon-button menu-button", "aria-label": "Toggle navigation" }, icon("menu", 18));
    menuButton.addEventListener("click", () => document.body.classList.toggle("nav-open"));

    this.dropdown = document.createElement("tg-dropdown");
    this.dropdown.setAttribute("label", "Optimizers");
    this.dropdown.setAttribute("leading-icon", "layers");
    this.fillDropdown();

    const search = h(
      "button",
      { type: "button", class: "search-trigger", "aria-label": "Search the docs" },
      icon("search", 16),
      h("span", { class: "search-placeholder" }, "Search..."),
      h("kbd", {}, isMac ? "⌘ K" : "Ctrl K"),
    );
    search.addEventListener("click", () => {
      const palette = document.querySelector("tg-search");
      if (palette) palette.open();
    });

    this.replaceChildren(
      h(
        "header",
        { class: "topbar" },
        h(
          "div",
          { class: "container topbar-row" },
          menuButton,
          h(
            "a",
            { class: "logo", href: "#/", "aria-label": "tokensguru home" },
            h("img", { class: "logo-mark", src: "assets/logo-mark.png", alt: "", width: "34", height: "34", decoding: "async" }),
            h("span", { class: "logo-word", role: "img", "aria-label": "tokensguru" }),
          ),
          this.dropdown,
          search,
          h(
            "div",
            { class: "topbar-actions" },
            h("a", { class: "pill", href: LINKS.github, target: "_blank", rel: "noopener noreferrer" }, icon("github", 16), h("span", {}, "GitHub")),
            h("a", { class: "pill primary", href: "#/install" }, h("span", {}, "Get started"), icon("chevron-right", 14)),
            document.createElement("tg-theme-toggle"),
          ),
        ),
        h("div", { class: "container tabs-wrap" }, document.createElement("tg-tabs")),
      ),
    );
    this.stop = onSectionsChange(() => this.fillDropdown());
    const bar = this.firstElementChild;
    this.observe = new ResizeObserver(() => document.documentElement.style.setProperty("--header-h", `${bar.offsetHeight}px`));
    this.observe.observe(bar);
    let waiting = false;
    this.onScroll = () => {
      if (waiting) return;
      waiting = true;
      requestAnimationFrame(() => {
        bar.classList.toggle("scrolled", window.scrollY > 4);
        waiting = false;
      });
    };
    window.addEventListener("scroll", this.onScroll, { passive: true });
  }

  disconnectedCallback() {
    if (this.stop) this.stop();
    if (this.observe) this.observe.disconnect();
    window.removeEventListener("scroll", this.onScroll);
  }

  fillDropdown() {
    this.dropdown.items = [
      { label: "All optimizers", href: "#/optimizers", icon: "layers" },
      ...currentOptimizers().map((entry) => ({ label: entry.name, href: `#/optimizers/${entry.id}`, icon: optimizerIcon(entry.id) })),
      { label: "Playground", href: "#/playground", icon: "play" },
    ];
  }
}

customElements.define("tg-navbar", TgNavbar);
