import { h, formatNumber, formatPercent } from "../dom.js";

function stat(name, value, { good = false } = {}) {
  return h("div", { class: "stat" }, h("div", { class: good ? "value good" : "value" }, value), h("div", { class: "name" }, name));
}

function pretty(messages) {
  return JSON.stringify(messages, null, 2);
}

export class TgResultView extends HTMLElement {
  set data(value) {
    this._data = value;
    this.tab = "optimized";
    this.render();
  }

  get data() {
    return this._data;
  }

  render() {
    const d = this._data;
    if (!d) {
      this.replaceChildren();
      return;
    }
    const hasTokens = d.saved_tokens !== null && d.saved_tokens !== undefined;
    const parts = [
      h(
        "div",
        { class: "stats" },
        stat(hasTokens ? `tokens saved (${formatPercent(d.saved_tokens_percent)})` : "tokens saved", formatNumber(d.saved_tokens), { good: hasTokens && d.saved_tokens > 0 }),
        stat("tokens before → after", `${formatNumber(d.original_tokens)} → ${formatNumber(d.optimized_tokens)}`),
        stat(`characters (${formatPercent(d.saved_chars_percent)} fewer)`, `${formatNumber(d.original_chars)} → ${formatNumber(d.optimized_chars)}`),
        stat("time", `${d.duration_ms} ms`),
      ),
      h("p", {}, h("span", { class: d.changed ? "badge good" : "badge neutral" }, d.changed ? "Changed" : "Unchanged"), " ", d.reason),
    ];
    if (d.token_error) {
      parts.push(h("div", { class: "warning", role: "status" }, `Token counts are unavailable: ${d.token_error}`));
    }
    if (Array.isArray(d.removed_indexes)) {
      const where = d.removed_indexes.length ? ` (positions ${d.removed_indexes.join(", ")})` : "";
      parts.push(h("p", { class: "muted" }, `Messages removed: ${d.removed_count} of ${d.original_messages.length}${where}`));
    }
    parts.push(this.renderTabs(d));
    if (Array.isArray(d.steps)) parts.push(this.renderSteps(d.steps));
    parts.push(
      h(
        "details",
        {},
        h("summary", {}, "Details"),
        h(
          "table",
          {},
          h("tbody", {}, [
            ["Result id", d.id],
            ["Optimizer", `${d.optimizer_name} (${d.optimizer_id})`],
            ["Tokenizer", d.tokenizer],
            ["Created at", d.created_at],
          ].map(([name, value]) => h("tr", {}, h("th", {}, name), h("td", {}, value)))),
        ),
      ),
    );
    this.replaceChildren(...parts);
  }

  contentFor(d, which) {
    const messages = which === "optimized" ? d.optimized_messages : d.original_messages;
    if (Array.isArray(messages)) return pretty(messages);
    return which === "optimized" ? d.optimized_text : d.original_text;
  }

  renderTabs(d) {
    const output = h("pre", { class: "output", tabindex: "0" });
    const buttons = {};
    const show = (which) => {
      this.tab = which;
      output.textContent = this.contentFor(d, which);
      output.setAttribute("aria-label", which === "optimized" ? "Optimized text" : "Original text");
      for (const [name, button] of Object.entries(buttons)) button.setAttribute("aria-selected", String(name === which));
    };
    const tab = (which, label) => {
      buttons[which] = h("button", { type: "button", role: "tab" }, label);
      buttons[which].addEventListener("click", () => show(which));
      return buttons[which];
    };
    const copy = h("button", { type: "button", class: "btn", style: "margin-left:auto;padding:0.2rem 0.7rem" }, "Copy");
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(output.textContent);
        copy.textContent = "Copied";
      } catch {
        copy.textContent = "Select and copy";
      }
      setTimeout(() => (copy.textContent = "Copy"), 1500);
    });
    const wrapper = h("div", {}, h("div", { class: "tabs", role: "tablist" }, tab("optimized", "Optimized"), tab("original", "Original"), copy), output);
    show(this.tab || "optimized");
    return wrapper;
  }

  renderSteps(steps) {
    return h(
      "div",
      {},
      h("h3", { style: "margin-top:1.5rem" }, "Steps"),
      h(
        "table",
        {},
        h("thead", {}, h("tr", {}, ["#", "Optimizer", "Result", "Tokens", "Saved"].map((name) => h("th", {}, name)))),
        h(
          "tbody",
          {},
          steps.map((step, index) =>
            h(
              "tr",
              {},
              h("td", {}, index + 1),
              h("td", {}, step.optimizer_name),
              h("td", {}, h("span", { class: step.changed ? "badge good" : "badge neutral" }, step.changed ? "changed" : "unchanged")),
              h("td", {}, `${formatNumber(step.original_tokens)} → ${formatNumber(step.optimized_tokens)}`),
              h("td", {}, step.saved_tokens === null ? "–" : formatNumber(step.saved_tokens)),
            ),
          ),
        ),
      ),
    );
  }
}

customElements.define("tg-result-view", TgResultView);
