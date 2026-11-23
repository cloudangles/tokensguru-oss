import { h } from "../dom.js";
import { currentRoute, onRouteChange } from "../router.js";
import { loadSections } from "../nav-state.js";
import { renderPage } from "./ui.js";

export class TgApp extends HTMLElement {
  connectedCallback() {
    this.main = h("main", { class: "content", id: "main", tabindex: "-1" });
    const skip = h("a", { class: "skip-link", href: "#main" }, "Skip to content");
    skip.addEventListener("click", (event) => {
      event.preventDefault();
      this.main.focus();
    });
    this.replaceChildren(
      skip,
      document.createElement("tg-banner"),
      document.createElement("tg-navbar"),
      h("div", { class: "container layout" }, h("aside", { class: "sidebar" }, document.createElement("tg-sidebar")), this.main),
      document.createElement("tg-search"),
    );
    this.stop = onRouteChange(() => this.render(true));
    this.render(false);
    loadSections();
  }

  disconnectedCallback() {
    if (this.stop) this.stop();
  }

  render(moveFocus) {
    document.body.classList.remove("nav-open");
    const { route, params, args } = currentRoute();
    try {
      if (!route) {
        const back = h("div", {}, h("p", { class: "lead" }, "That page does not exist."), h("a", { class: "btn primary", href: "#/" }, "Back to the overview"));
        renderPage(this.main, "Page not found", back);
      } else {
        const page = document.createElement(route.tag);
        page.params = params;
        page.args = args;
        this.main.replaceChildren(page);
        document.title = `${route.title} · tokensguru docs`;
      }
    } catch (error) {
      renderPage(this.main, "Something went wrong", h("div", { class: "error", role: "alert" }, `This page could not be shown: ${error.message}`), h("a", { class: "btn primary", href: "#/" }, "Back to the overview"));
    }
    window.scrollTo({ top: 0, behavior: "instant" });
    if (moveFocus) this.main.focus({ preventScroll: true });
  }
}

customElements.define("tg-app", TgApp);
