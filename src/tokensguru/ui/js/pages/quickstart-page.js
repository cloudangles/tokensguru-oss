import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, card, cards, renderPage } from "../components/ui.js";

export class TgQuickstartPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Quickstart",
      h("p", { class: "lead" }, "Optimize a piece of text and see how many tokens you saved. You do not need to count tokens yourself, because every optimizer does it for you."),
      h("h2", {}, "1. Run the optimizers"),
      h("p", {}, h("code", {}, "Pipeline"), " runs every built-in text optimizer in a sensible order:"),
      codeBlock('from tokensguru.optimizers import Pipeline\n\ntext = """Rules:\n- Be concise\n- Be concise\n- Cite sources\n\n\n\nThanks   a lot.   """\n\nresult = Pipeline().optimize(text)'),
      h("h2", {}, "2. Read the result"),
      codeBlock('print(result.optimized_text)\nprint(result.original_tokens, "->", result.optimized_tokens)\nprint(result.saved_tokens, result.saved_tokens_percent)\nprint(result)   # a readable summary with the id, reason and timing'),
      callout("info", "The text only ever gets shorter. If nothing can be removed safely, ", h("code", {}, "result.changed"), " is ", h("code", {}, "False"), " and ", h("code", {}, "result.reason"), " says why."),
      h("h2", {}, "3. Use a single optimizer"),
      codeBlock('from tokensguru.optimizers import BulletDeduplicator\n\nresult = BulletDeduplicator().optimize("- a\\n- a\\n- b\\n")\nprint(result.optimized_text)   # - a\\n- b\\n'),
      h("h2", {}, "Where to go next"),
      cards(
        card({ heading: "Playground", icon: "terminal", href: "#/playground", cta: "Open the playground", tone: "green" }, "Try your own text in the browser."),
        card({ heading: "All optimizers", icon: "layers", href: "#/optimizers", cta: "Browse optimizers" }, "See what each one removes and what it keeps."),
        card({ heading: "Use a pipeline", icon: "sliders", href: "#/guides/pipeline", cta: "Read the guide" }, "Choose which optimizers run and in what order."),
      ),
    );
  }
}

customElements.define("tg-quickstart-page", TgQuickstartPage);
