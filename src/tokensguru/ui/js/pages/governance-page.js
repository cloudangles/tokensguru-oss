import { h } from "../dom.js";
import { getGuardrails } from "../api.js";
import { guardrailIcon } from "../icons.js";
import { callout, card, cards, renderPage, skeletons } from "../components/ui.js";

export class TgGovernancePage extends HTMLElement {
  connectedCallback() {
    const list = h("div", { "aria-live": "polite", "aria-busy": "true" }, skeletons(6));
    renderPage(
      this,
      "All guardrails",
      h("p", { class: "lead" }, "Guardrails check text for problems before it reaches a model or a user: personal data, secrets, attacks and abuse. Each one is a small class you can use on its own or together."),
      callout("info", "They run on your own machine with built-in rules. For better accuracy on prompt injection and toxicity you can plug in a Hugging Face model. Check each model's license first."),
      list,
      h("p", {}, h("a", { class: "btn primary", href: "#/governance/guide" }, "How to use them"), " ", h("a", { class: "btn", href: "#/governance/playground" }, "Open the playground")),
    );
    getGuardrails()
      .then((items) => list.replaceChildren(cards(...items.map((entry) => card({ heading: entry.name, icon: guardrailIcon(entry.id), href: `#/governance/${entry.id}`, cta: "Read more" }, entry.summary)))))
      .catch((error) => list.replaceChildren(h("div", { class: "error", role: "alert" }, error.message)));
  }
}

customElements.define("tg-governance-page", TgGovernancePage);
