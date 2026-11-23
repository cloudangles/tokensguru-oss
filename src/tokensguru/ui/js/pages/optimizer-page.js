import { h, formatNumber } from "../dom.js";
import { getBenchmark, getOptimizers, runOptimizer } from "../api.js";
import { renderDescription } from "../doc.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage, skeletonRows } from "../components/ui.js";

function stat(value, name, good = false) {
  return h("div", { class: "stat" }, h("div", { class: good ? "value good" : "value" }, value), h("div", { class: "name" }, name));
}

const KIND_LABEL = { pipeline: "Runs all text optimizers", text: "Text optimizer", messages: "Chat messages optimizer" };

export class TgOptimizerPage extends HTMLElement {
  connectedCallback() {
    renderPage(this, "Optimizer", h("p", { class: "muted" }, "Loading…"));
    getOptimizers()
      .then((items) => {
        const entry = items.find((item) => item.id === (this.args && this.args.id));
        if (entry) this.show(entry);
        else renderPage(this, "Optimizer not found", callout("warning", "There is no optimizer called ", h("code", {}, this.args ? this.args.id : ""), "."), h("a", { class: "btn primary", href: "#/optimizers" }, "See all optimizers"));
      })
      .catch((error) => renderPage(this, "Optimizer", h("div", { class: "error", role: "alert" }, error.message)));
  }

  show(entry) {
    const example = h("div", { "aria-busy": "true" }, skeletonRows(3));
    const savings = h("div", { "aria-live": "polite", "aria-busy": "true" }, skeletonRows(4), h("p", { class: "hint" }, "Measuring the sample inputs. The first measurement can take a few seconds while the tokenizer loads."));
    renderPage(
      this,
      entry.name,
      h("p", { class: "lead" }, entry.summary),
      h("p", {}, h("span", { class: "badge" }, KIND_LABEL[entry.kind] || entry.kind), " ", h("code", {}, entry.id), " ", h("span", { class: "muted" }, "· class "), h("code", {}, entry.class_name)),
      callout("tip", "Want to see it work on your own text? ", h("a", { href: `#/playground?optimizer=${encodeURIComponent(entry.id)}` }, "Open this optimizer in the playground"), "."),
      ...renderDescription(entry.description),
      h("h2", {}, "Live example"),
      example,
      h("h2", {}, "Typical savings"),
      savings,
    );
    this.runExample(entry, example);
    this.showSavings(savings);
  }

  async showSavings(container) {
    try {
      const report = await getBenchmark(this.args.id);
      if (report.error) {
        container.replaceChildren(callout("warning", `The savings could not be measured right now: ${report.error}`));
        return;
      }
      const summary = report.summary;
      container.replaceChildren(
        h("p", {}, `Measured on ${summary.samples} built-in sample inputs with the ${report.tokenizer} tokenizer. Some samples have nothing to remove, so the average is not inflated.`),
        h(
          "div",
          { class: "stats" },
          stat(`${summary.average_percent}%`, "average saved per input", true),
          stat(`${summary.min_percent}% to ${summary.max_percent}%`, "range across the samples"),
          stat(`${summary.changed} of ${summary.samples}`, "samples it shortened"),
          stat(`${formatNumber(summary.total_original_tokens)} → ${formatNumber(summary.total_optimized_tokens)}`, `all samples together (${summary.overall_percent}% saved)`),
        ),
        h(
          "table",
          {},
          h("thead", {}, h("tr", {}, ["Sample input", "Tokens", "Saved"].map((name) => h("th", {}, name)))),
          h(
            "tbody",
            {},
            report.samples.map((sample) =>
              h(
                "tr",
                {},
                h("td", {}, sample.name),
                h("td", {}, `${formatNumber(sample.original_tokens)} → ${formatNumber(sample.optimized_tokens)}`),
                h("td", {}, h("span", { class: "savebar", style: `--pct:${Math.min(100, sample.saved_percent)}%` }), ` ${sample.saved_percent}%`),
              ),
            ),
          ),
        ),
        callout("info", "These are small, fixed sample inputs built into the package, not measurements of real traffic. Your savings depend on how much repetition and extra formatting your own text has. Use the playground to measure your own."),
      );
    } catch (error) {
      container.replaceChildren(h("div", { class: "error", role: "alert" }, error.message));
    }
  }

  async runExample(entry, container) {
    const isMessages = entry.kind === "messages";
    const payload = isMessages ? { optimizer: entry.id, messages: entry.example } : { optimizer: entry.id, text: entry.example };
    try {
      const result = await runOptimizer(payload);
      const before = isMessages ? JSON.stringify(result.original_messages, null, 2) : result.original_text;
      const after = isMessages ? JSON.stringify(result.optimized_messages, null, 2) : result.optimized_text;
      const tokens = result.saved_tokens === null ? "" : ` Tokens: ${formatNumber(result.original_tokens)} → ${formatNumber(result.optimized_tokens)} (${formatNumber(result.saved_tokens)} saved).`;
      container.replaceChildren(h("p", {}, "Before:"), codeBlock(before), h("p", {}, "After:"), codeBlock(after), h("p", { class: "muted" }, `${result.reason}${tokens}`));
    } catch (error) {
      container.replaceChildren(h("div", { class: "error", role: "alert" }, error.message));
    }
  }
}

customElements.define("tg-optimizer-page", TgOptimizerPage);
