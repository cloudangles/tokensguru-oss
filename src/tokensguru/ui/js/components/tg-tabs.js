import { h } from "../dom.js";
import { currentRoute, onRouteChange } from "../router.js";
import { currentSections, onSectionsChange } from "../nav-state.js";
import { firstPath, sectionFor } from "../nav.js";

export class TgTabs extends HTMLElement {
  connectedCallback() {
    this.stops = [onRouteChange(() => this.render()), onSectionsChange(() => this.render())];
    this.render();
  }

  disconnectedCallback() {
    for (const stop of this.stops) stop();
  }

  render() {
    const sections = currentSections();
    const { route } = currentRoute();
    const active = route ? sectionFor(sections, route.section).id : null;
    this.replaceChildren(
      h(
        "nav",
        { class: "tabs-row", "aria-label": "Sections" },
        sections.map((section) => h("a", { href: `#${firstPath(section)}`, "aria-current": section.id === active ? "page" : null }, section.title)),
      ),
    );
  }
}

customElements.define("tg-tabs", TgTabs);
