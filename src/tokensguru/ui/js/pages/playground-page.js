import { h } from "../dom.js";
import { getOptimizers, runOptimizer } from "../api.js";
import { callout, renderPage } from "../components/ui.js";

export class TgPlaygroundPage extends HTMLElement {
  connectedCallback() {
    this.select = h("select", { id: "optimizer" });
    this.input = h("textarea", { id: "input", spellcheck: "false", "aria-describedby": "input-hint" });
    this.label = h("label", { for: "input" }, "Input text");
    this.hint = h("div", { class: "hint", id: "input-hint" });
    this.status = h("div", { class: "hint", "aria-live": "polite" });
    this.error = h("div", { "aria-live": "assertive" });
    this.result = document.createElement("tg-result-view");
    this.runButton = h("button", { type: "button", class: "btn primary" }, "Run");
    const exampleButton = h("button", { type: "button", class: "btn" }, "Load example");
    const clearButton = h("button", { type: "button", class: "btn" }, "Clear");

    this.runButton.addEventListener("click", () => this.run());
    exampleButton.addEventListener("click", () => this.loadExample());
    clearButton.addEventListener("click", () => {
      this.input.value = "";
      this.input.focus();
    });
    this.select.addEventListener("change", () => this.optimizerChanged());
    this.input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        this.run();
      }
    });

    renderPage(
      this,
      "Playground",
      h("p", { class: "lead" }, "Run an optimizer on your own text and see exactly what changes and how many tokens you save."),
      callout("info", "Your text is sent only to the small server on your own computer that is running these docs."),
      h("div", { class: "field" }, h("label", { for: "optimizer" }, "Optimizer"), this.select),
      h("div", { class: "field" }, this.label, this.input, this.hint),
      h("div", { class: "actions" }, this.runButton, exampleButton, clearButton),
      this.status,
      this.error,
      this.result,
    );

    getOptimizers()
      .then((items) => {
        this.items = items;
        this.select.replaceChildren(...items.map((entry) => h("option", { value: entry.id }, entry.name + (entry.kind === "pipeline" ? " (all text optimizers)" : ""))));
        const wanted = this.params && this.params.get("optimizer");
        if (wanted && items.some((entry) => entry.id === wanted)) this.select.value = wanted;
        this.optimizerChanged(true);
      })
      .catch((error) => this.showError(error.message));
  }

  get current() {
    return this.items.find((entry) => entry.id === this.select.value);
  }

  exampleText(entry) {
    return entry.kind === "messages" ? JSON.stringify(entry.example, null, 2) : entry.example;
  }

  optimizerChanged(initial = false) {
    const entry = this.current;
    const isMessages = entry.kind === "messages";
    this.label.textContent = isMessages ? "Chat messages (a JSON list)" : "Input text";
    this.hint.textContent = isMessages ? 'A JSON list such as [{"role": "system", "content": "..."}]. Press Ctrl+Enter to run.' : "Paste any text. Press Ctrl+Enter to run.";
    const previous = this.items.find((other) => this.exampleText(other) === this.input.value);
    if (initial || !this.input.value.trim() || previous) this.input.value = this.exampleText(entry);
    this.result.data = null;
    this.error.replaceChildren();
    this.status.textContent = "";
  }

  loadExample() {
    this.input.value = this.exampleText(this.current);
    this.input.focus();
  }

  showError(message) {
    this.error.replaceChildren(h("div", { class: "error", role: "alert" }, message));
  }

  async run() {
    const entry = this.current;
    this.error.replaceChildren();
    let payload;
    if (entry.kind === "messages") {
      let messages;
      try {
        messages = JSON.parse(this.input.value);
      } catch {
        this.showError("The input is not valid JSON.");
        return;
      }
      if (!Array.isArray(messages)) {
        this.showError("The input must be a JSON list of messages.");
        return;
      }
      payload = { optimizer: entry.id, messages };
    } else {
      payload = { optimizer: entry.id, text: this.input.value };
    }
    this.runButton.disabled = true;
    this.status.textContent = "Running… the first run can take a few seconds while the tokenizer loads.";
    try {
      this.result.data = await runOptimizer(payload);
      this.status.textContent = "";
    } catch (error) {
      this.result.data = null;
      this.status.textContent = "";
      this.showError(error.message);
    } finally {
      this.runButton.disabled = false;
    }
  }
}

customElements.define("tg-playground-page", TgPlaygroundPage);
