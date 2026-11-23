import { h, formatNumber } from "../dom.js";
import { getGuardrailBenchmark, getGuardrails, runCheck } from "../api.js";
import { renderDescription } from "../doc.js";
import { checkView } from "../components/check-view.js";
import { callout, renderPage, skeletonRows } from "../components/ui.js";

function stat(value, name, good = false) {
  return h("div", { class: "stat" }, h("div", { class: good ? "value good" : "value" }, value), h("div", { class: "name" }, name));
}

const percent = (value) => `${Math.round(value * 1000) / 10}%`;

export class TgGuardrailPage extends HTMLElement {
  connectedCallback() {
    renderPage(this, "Guardrail", h("p", { class: "muted" }, "Loading…"));
    getGuardrails()
      .then((items) => {
        const entry = items.find((item) => item.id === (this.args && this.args.id));
        if (entry) this.show(entry);
        else renderPage(this, "Guardrail not found", callout("warning", "There is no guardrail called ", h("code", {}, this.args ? this.args.id : ""), "."), h("a", { class: "btn primary", href: "#/governance" }, "See all guardrails"));
      })
      .catch((error) => renderPage(this, "Guardrail", h("div", { class: "error", role: "alert" }, error.message)));
  }

  show(entry) {
    const example = h("div", { "aria-busy": "true" }, skeletonRows(3));
    const accuracy = h("div", { "aria-live": "polite", "aria-busy": "true" }, skeletonRows(4));
    renderPage(
      this,
      entry.name,
      h("p", { class: "lead" }, entry.summary),
      h("p", {}, h("span", { class: "badge" }, `default: ${entry.default_action}`), " ", h("code", {}, entry.id), " ", h("span", { class: "muted" }, "· class "), h("code", {}, entry.class_name)),
      callout("tip", "Try it on your own text: ", h("a", { href: `#/governance/playground?guardrail=${encodeURIComponent(entry.id)}` }, "open this guardrail in the playground"), "."),
      ...renderDescription(entry.description),
      h("h2", {}, "Live example"),
      example,
      ...(entry.has_benchmark ? [h("h2", {}, "Typical detection accuracy"), accuracy] : []),
    );
    this.runExample(entry, example);
    if (entry.has_benchmark) this.showAccuracy(entry, accuracy);
  }

  async runExample(entry, container) {
    try {
      const result = await runCheck({ guardrail: entry.id, text: entry.example, context: entry.example_context });
      container.replaceChildren(h("p", {}, "Input:"), h("pre", { class: "output" }, entry.example), h("p", {}, "Result:"), checkView(result));
    } catch (error) {
      container.replaceChildren(h("div", { class: "error", role: "alert" }, error.message));
    }
  }

  async showAccuracy(entry, container) {
    try {
      const report = await getGuardrailBenchmark(entry.id);
      const s = report.summary;
      container.replaceChildren(
        h("p", {}, `Measured${report.model ? ` with the ${report.model} model` : " with the rules only"} on ${s.samples} labelled examples built into the package: clear cases, tricky safe text that looks suspicious, disguised cases and a few that the rules are known to miss.`),
        h("div", { class: "stats" }, stat(percent(s.precision), "precision: of what it reported, how much was right", true), stat(percent(s.recall), "recall: of what it should find, how much it found", true), stat(percent(s.f1), "F1: the two balanced"), stat(`${formatNumber(s.true_positive)} / ${formatNumber(s.false_positive)} / ${formatNumber(s.false_negative)}`, "found / false alarms / missed")),
        report.mistakes.length
          ? h("div", {}, h("p", {}, "What it got wrong on these examples:"), h("table", {}, h("thead", {}, h("tr", {}, ["#", "Kind", "Example"].map((name) => h("th", {}, name)))), h("tbody", {}, report.mistakes.map((m) => h("tr", {}, h("td", {}, m.number), h("td", {}, m.kind), h("td", {}, h("code", {}, m.label)))))))
          : h("p", {}, "It got every one of these examples right."),
        callout("info", "These are small, fixed examples, not measurements of real traffic. Accuracy on your own data will differ, so test with your own samples in the playground."),
      );
    } catch (error) {
      container.replaceChildren(h("div", { class: "error", role: "alert" }, error.message));
    }
  }
}

customElements.define("tg-guardrail-page", TgGuardrailPage);
