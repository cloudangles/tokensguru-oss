import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage } from "../components/ui.js";

export class TgGuideOptionsPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Options and tokenizer",
      h("p", { class: "lead" }, "Optimizers have sensible defaults. These are the options you can change, and how to choose the tokenizer that counts the tokens."),
      h("h2", {}, "Optimizer options"),
      codeBlock("from tokensguru.optimizers import ParagraphDeduplicator, WhitespaceCleaner\n\nParagraphDeduplicator(min_length=0)         # also remove short repeats\nParagraphDeduplicator(adjacent_only=True)   # only repeats right under each other\nWhitespaceCleaner(max_blank_lines=2)        # keep up to two blank lines in a row"),
      h("h2", {}, "Choose the tokenizer"),
      h("p", {}, "Tokens are counted with tiktoken. The default is ", h("code", {}, "o200k_base"), ". Pick another by model name or by tokenizer name:"),
      codeBlock('from tokensguru import TokenCounter\nfrom tokensguru.optimizers import WhitespaceCleaner\n\ncounter = TokenCounter(model="gpt-4")           # by model name\ncounter = TokenCounter(encoding="cl100k_base")  # or by tokenizer name\n\nresult = WhitespaceCleaner(counter=counter).optimize(text)\nprint(result.tokenizer)                         # gpt-4'),
      callout("info", "Counts are exact for OpenAI models and a close estimate for other models."),
      h("h2", {}, "Count text yourself"),
      codeBlock('TokenCounter().count("hello world")   # 2'),
      callout("tip", "If the tokenizer cannot be loaded (for example there is no internet the first time), the text is still optimized, the token fields are ", h("code", {}, "None"), ", and ", h("code", {}, "result.token_error"), " says why."),
    );
  }
}

customElements.define("tg-guide-options-page", TgGuideOptionsPage);
