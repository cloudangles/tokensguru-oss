import { h } from "../dom.js";
import { icon } from "../icons.js";

export class TgDropdown extends HTMLElement {
  constructor() {
    super();
    this._items = [];
    this._onDocumentClick = (event) => {
      if (!this.contains(event.target)) this.close();
    };
    this._onKey = (event) => {
      if (event.key === "Escape" && this.isOpen) {
        this.close();
        this.trigger.focus();
      }
    };
  }

  get isOpen() {
    return this.trigger.getAttribute("aria-expanded") === "true";
  }

  set items(list) {
    this._items = list;
    if (this.isConnected) this.renderMenu();
  }

  connectedCallback() {
    const label = this.getAttribute("label") || "";
    this.trigger = h(
      "button",
      { type: "button", class: "dropdown-trigger", "aria-haspopup": "true", "aria-expanded": "false", "aria-label": this.getAttribute("aria-label") || label || "Open menu" },
      this.hasAttribute("leading-icon") ? icon(this.getAttribute("leading-icon"), 16) : null,
      label ? h("span", {}, label) : null,
      icon("chevron-down", 14),
    );
    this.trigger.addEventListener("click", () => (this.isOpen ? this.close() : this.open()));
    this.menu = h("div", { class: "dropdown-menu", role: "menu", hidden: true });
    this.replaceChildren(this.trigger, this.menu);
    this.renderMenu();
    document.addEventListener("click", this._onDocumentClick);
    document.addEventListener("keydown", this._onKey);
  }

  disconnectedCallback() {
    document.removeEventListener("click", this._onDocumentClick);
    document.removeEventListener("keydown", this._onKey);
  }

  renderMenu() {
    this.menu.replaceChildren(
      ...this._items.map((entry) => {
        const content = [entry.icon ? icon(entry.icon, 16) : null, h("span", {}, entry.label)];
        if (entry.href) {
          const link = h("a", { role: "menuitem", class: "dropdown-item", href: entry.href }, content);
          link.addEventListener("click", () => this.close());
          return link;
        }
        const button = h("button", { type: "button", role: "menuitem", class: "dropdown-item" }, content);
        button.addEventListener("click", async () => {
          this.close();
          if (entry.onClick) await entry.onClick();
        });
        return button;
      }),
    );
  }

  open() {
    this.menu.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
  }

  close() {
    this.menu.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
  }
}

customElements.define("tg-dropdown", TgDropdown);
