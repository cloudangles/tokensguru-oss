import { h } from "../dom.js";
import { icon } from "../icons.js";
import { allPages } from "../nav.js";
import { currentOptimizers, currentSections, onSectionsChange } from "../nav-state.js";

const MAX_RESULTS = 8;

function buildIndex() {
  const summaries = new Map(currentOptimizers().map((entry) => [`/optimizers/${entry.id}`, entry.summary]));
  return allPages(currentSections())
    .filter((page) => !page.path.includes("?"))
    .map((page) => ({ ...page, summary: summaries.get(page.path) || "" }));
}

export function searchPages(index, query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return index.slice(0, MAX_RESULTS);
  const scored = [];
  for (const page of index) {
    const title = page.title.toLowerCase();
    const haystack = `${title} ${page.section.toLowerCase()} ${page.summary.toLowerCase()}`;
    if (!words.every((word) => haystack.includes(word))) continue;
    const score = words.reduce((total, word) => total + (title.startsWith(word) ? 3 : title.includes(word) ? 2 : 1), 0);
    scored.push({ page, score });
  }
  return scored.sort((a, b) => b.score - a.score).slice(0, MAX_RESULTS).map((entry) => entry.page);
}

export class TgSearch extends HTMLElement {
  connectedCallback() {
    this.active = 0;
    this.results = [];
    this.input = h("input", { type: "search", class: "search-input", placeholder: "Search the docs", "aria-label": "Search the docs", autocomplete: "off", spellcheck: "false", role: "combobox", "aria-expanded": "true", "aria-controls": "search-results" });
    this.list = h("ul", { class: "search-results", id: "search-results", role: "listbox" });
    this.box = h(
      "div",
      { class: "search-box", role: "dialog", "aria-modal": "true", "aria-label": "Search" },
      h("div", { class: "search-field" }, icon("search", 18), this.input),
      this.list,
      h("div", { class: "search-foot" }, "↑ ↓ to move, Enter to open, Esc to close"),
    );
    this.overlay = h("div", { class: "search-overlay", hidden: true }, this.box);
    this.replaceChildren(this.overlay);

    this.overlay.addEventListener("mousedown", (event) => {
      if (event.target === this.overlay) this.close();
    });
    this.input.addEventListener("input", () => this.update());
    this.input.addEventListener("keydown", (event) => this.onKey(event));
    this.onGlobalKey = (event) => {
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement && document.activeElement.tagName);
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        this.open();
      } else if (event.key === "/" && !typing && this.overlay.hidden) {
        event.preventDefault();
        this.open();
      }
    };
    document.addEventListener("keydown", this.onGlobalKey);
    this.stop = onSectionsChange(() => !this.overlay.hidden && this.update());
  }

  disconnectedCallback() {
    document.removeEventListener("keydown", this.onGlobalKey);
    if (this.stop) this.stop();
  }

  open() {
    this.returnFocus = document.activeElement;
    this.overlay.hidden = false;
    this.input.value = "";
    this.update();
    this.input.focus();
  }

  close() {
    this.overlay.hidden = true;
    if (this.returnFocus && this.returnFocus.focus) this.returnFocus.focus();
  }

  update() {
    this.results = searchPages(buildIndex(), this.input.value.trim());
    this.active = 0;
    this.renderResults();
  }

  renderResults() {
    if (!this.results.length) {
      this.list.replaceChildren(h("li", { class: "search-empty" }, "No results"));
      return;
    }
    this.list.replaceChildren(
      ...this.results.map((page, index) => {
        const item = h("li", { role: "option", id: `search-result-${index}`, "aria-selected": String(index === this.active), class: "search-result" }, h("div", { class: "search-title" }, page.title), h("div", { class: "search-meta" }, [page.section, page.summary].filter(Boolean).join(" · ")));
        item.addEventListener("mousemove", () => this.select(index));
        item.addEventListener("click", () => this.go(page));
        return item;
      }),
    );
    this.input.setAttribute("aria-activedescendant", `search-result-${this.active}`);
  }

  select(index) {
    this.active = index;
    this.list.querySelectorAll("li[role=option]").forEach((item, position) => item.setAttribute("aria-selected", String(position === index)));
    this.input.setAttribute("aria-activedescendant", `search-result-${index}`);
  }

  go(page) {
    window.location.hash = page.path;
    this.close();
  }

  onKey(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      this.close();
    } else if (event.key === "ArrowDown" && this.results.length) {
      event.preventDefault();
      this.select((this.active + 1) % this.results.length);
      this.list.children[this.active].scrollIntoView({ block: "nearest" });
    } else if (event.key === "ArrowUp" && this.results.length) {
      event.preventDefault();
      this.select((this.active - 1 + this.results.length) % this.results.length);
      this.list.children[this.active].scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter" && this.results[this.active]) {
      event.preventDefault();
      this.go(this.results[this.active]);
    }
  }
}

customElements.define("tg-search", TgSearch);
