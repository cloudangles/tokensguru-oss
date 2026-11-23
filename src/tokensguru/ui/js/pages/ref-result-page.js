import { h } from "../dom.js";
import { renderPage } from "../components/ui.js";

const FIELDS = [
  ["optimized_text", "The shorter text."],
  ["original_text", "The text you passed in."],
  ["original_tokens, optimized_tokens", "Token counts before and after."],
  ["saved_tokens, saved_tokens_percent", "How many tokens were saved, and the percentage."],
  ["original_chars, optimized_chars", "Character counts before and after."],
  ["saved_chars, saved_chars_percent", "How many characters were saved."],
  ["changed", "True if the text changed."],
  ["reason", "Why it changed, or why nothing was changed."],
  ["optimizer_id, optimizer_name", "Which optimizer produced the result."],
  ["tokenizer", "Which tokenizer counted the tokens (default o200k_base)."],
  ["duration_ms", "How long the optimizer took, in milliseconds."],
  ["id, created_at", "A unique id and a UTC timestamp for this run."],
  ["token_error", "Set only if tokens could not be counted. The text is still optimized."],
  ["steps", "Pipeline only: one full result per optimizer."],
  ["original_messages, optimized_messages", "Message optimizers only: the lists before and after."],
  ["removed_count, removed_indexes", "Message optimizers only: which messages were removed."],
];

export class TgRefResultPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Result fields",
      h("p", { class: "lead" }, "Every call to optimize() returns a result with these fields. Call ", h("code", {}, "result.to_dict()"), " to get them all as a plain dictionary."),
      h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Field"), h("th", {}, "Meaning"))), h("tbody", {}, FIELDS.map(([name, meaning]) => h("tr", {}, h("td", {}, h("code", {}, name)), h("td", {}, meaning))))),
    );
  }
}

customElements.define("tg-ref-result-page", TgRefResultPage);
