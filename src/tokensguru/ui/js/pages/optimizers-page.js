import { h } from "../dom.js";
import { getOptimizers } from "../api.js";
import { optimizerIcon } from "../icons.js";
import { callout, card, cards, renderPage, skeletons } from "../components/ui.js";

const FILTERS = [["all", "All"], ["text", "Text"], ["messages", "Chat messages"]];

export class TgOptimizersPage extends HTMLElement {
  connectedCallback() {
    this.filter = "all";
    this.filters = h("div", { class: "filters", role: "group", "aria-label": "Filter optimizers" });
    this.list = h("div", { "aria-live": "polite", "aria-busy": "true" }, skeletons(6));
    renderPage(
      this,
      "All optimizers",
      h("p", { class: "lead" }, "Each optimizer does one job. Open one to see exactly what it changes and what it deliberately leaves alone."),
      callout("tip", "Not sure which to use? ", h("code", {}, "Pipeline"), " runs all the text optimizers in a sensible order."),
      this.filters,
      this.list,
    );
    getOptimizers()
      .then((items) => {
        this.items = items;
        this.render();
      })
      .catch((error) => this.list.replaceChildren(h("div", { class: "error", role: "alert" }, error.message)));
  }

  render() {
    this.filters.replaceChildren(
      ...FILTERS.map(([value, label]) => {
        const button = h("button", { type: "button", class: this.filter === value ? "chip active" : "chip", "aria-pressed": String(this.filter === value) }, label);
        button.addEventListener("click", () => {
          this.filter = value;
          this.render();
        });
        return button;
      }),
    );
    const visible = this.items.filter((entry) => this.filter === "all" || entry.kind === this.filter || (this.filter === "text" && entry.kind === "pipeline"));
    this.list.replaceChildren(cards(...visible.map((entry) => card({ heading: entry.name, icon: optimizerIcon(entry.id), href: `#/optimizers/${entry.id}`, cta: "Read more" }, entry.summary))));
  }
}

customElements.define("tg-optimizers-page", TgOptimizersPage);
