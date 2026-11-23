import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage } from "../components/ui.js";

export class TgGuidePipelinePage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Use a pipeline",
      h("p", { class: "lead" }, "A pipeline runs several optimizers one after another and gives you one combined result, with the details of every step inside it."),
      codeBlock("from tokensguru.optimizers import Pipeline\n\nresult = Pipeline().optimize(text)       # every built-in text optimizer\n\nprint(result.optimized_text)\nprint(result.original_tokens, result.optimized_tokens, result.saved_tokens)\nprint(result)                            # summary plus every step"),
      h("h2", {}, "Choose the optimizers and their order"),
      codeBlock("from tokensguru.optimizers import Pipeline, WhitespaceCleaner, BulletDeduplicator\n\nresult = Pipeline(WhitespaceCleaner(), BulletDeduplicator()).optimize(text)"),
      h("h2", {}, "Look at each step"),
      codeBlock("for step in result.steps:\n    print(step.optimizer_id, step.changed, step.saved_tokens)"),
      callout("tip", "The built-in order is: JSON minifier, whitespace cleaner, paragraph deduplicator, bullet deduplicator. Whitespace is cleaned before repeats are looked for, so lines that only differ by extra spaces count as the same line."),
      callout("warning", "Do not pass one result into the next optimizer. Each ", h("code", {}, "optimize()"), " returns a result object. Use ", h("code", {}, "Pipeline"), ", or pass ", h("code", {}, "result.optimized_text"), "."),
    );
  }
}

customElements.define("tg-guide-pipeline-page", TgGuidePipelinePage);
