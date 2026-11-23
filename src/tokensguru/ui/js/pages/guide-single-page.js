import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage } from "../components/ui.js";

export class TgGuideSinglePage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Use one optimizer",
      h("p", { class: "lead" }, "Every text optimizer works the same way: create it, pass it a string, read the result."),
      codeBlock('from tokensguru.optimizers import WhitespaceCleaner\n\nresult = WhitespaceCleaner().optimize("Hello     world.   \\n\\n\\n\\nBye.")\n\nprint(result.optimized_text)   # Hello world.\\n\\nBye.\nprint(result.saved_tokens)\nprint(result)                  # id, tokens, characters, reason and more'),
      callout("info", "Pass a plain Python string. To use a file, read it first: ", h("code", {}, 'text = open("file.txt", encoding="utf-8").read()'), "."),
      h("h2", {}, "The text optimizers"),
      h("table", {}, h("thead", {}, h("tr", {}, ["Class", "Removes"].map((name) => h("th", {}, name)))), h("tbody", {}, [
        ["JsonMinifier", "Indentation and line breaks in a JSON document."],
        ["WhitespaceCleaner", "Repeated spaces, trailing spaces and runs of blank lines."],
        ["ParagraphDeduplicator", "A paragraph that already appeared earlier."],
        ["BulletDeduplicator", "A bullet that repeats the bullet right above it."],
      ].map(([name, text]) => h("tr", {}, h("td", {}, h("code", {}, name)), h("td", {}, text))))),
      h("h2", {}, "When nothing changes"),
      h("p", {}, "If the text has nothing safe to remove, you get the same text back, ", h("code", {}, "result.changed"), " is ", h("code", {}, "False"), ", and ", h("code", {}, "result.reason"), " explains why. Code blocks, tables, headings and similar structure are left alone on purpose."),
      codeBlock('result = WhitespaceCleaner().optimize("Already clean.")\nprint(result.changed)   # False\nprint(result.reason)'),
    );
  }
}

customElements.define("tg-guide-single-page", TgGuideSinglePage);
