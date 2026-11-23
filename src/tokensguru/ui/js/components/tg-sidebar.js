import { h } from "../dom.js";
import { icon } from "../icons.js";
import { currentHash, currentRoute, onRouteChange } from "../router.js";
import { currentSections, onSectionsChange } from "../nav-state.js";
import { sectionFor } from "../nav.js";

function isActive(entry) {
  if (!entry.path) return false;
  const hash = currentHash();
  return entry.path.includes("?") ? hash === entry.path : currentRoute().path === entry.path && !hash.includes("?");
}

export class TgSidebar extends HTMLElement {
  connectedCallback() {
    this.stops = [onRouteChange(() => this.render()), onSectionsChange(() => this.render())];
    this.render();
  }

  disconnectedCallback() {
    for (const stop of this.stops) stop();
  }

  link(entry) {
    const external = Boolean(entry.href);
    const link = h(
      "a",
      {
        class: "side-link",
        href: external ? entry.href : `#${entry.path}`,
        target: external ? "_blank" : null,
        rel: external ? "noopener noreferrer" : null,
        "aria-current": isActive(entry) ? "page" : null,
      },
      entry.icon ? icon(entry.icon, 16) : null,
      h("span", { class: "side-text" }, entry.title),
      external ? icon("external", 14) : null,
    );
    return link;
  }

  render() {
    const { route } = currentRoute();
    const section = sectionFor(currentSections(), route ? route.section : "start");
    this.replaceChildren(
      h(
        "nav",
        { class: "sidebar-nav", "aria-label": `${section.title} navigation` },
        section.groups
          .filter((group) => group.items.length)
          .map((group) =>
            h("div", { class: "side-group" }, group.title ? h("div", { class: "side-heading" }, group.title) : null, group.items.map((entry) => this.link(entry))),
          ),
      ),
    );
    const current = this.querySelector("[aria-current]");
    if (current) current.scrollIntoView({ block: "nearest", behavior: "instant" });
  }
}

customElements.define("tg-sidebar", TgSidebar);
