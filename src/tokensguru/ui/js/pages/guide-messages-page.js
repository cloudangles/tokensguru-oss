import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage } from "../components/ui.js";

export class TgGuideMessagesPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Chat messages",
      h("p", { class: "lead" }, "Some optimizers work on the messages list you send to a chat model instead of on one string."),
      codeBlock('from tokensguru.optimizers import SystemMessageDeduplicator\n\nmessages = [\n    {"role": "system", "content": "Be concise."},\n    {"role": "system", "content": "Be concise."},\n    {"role": "user", "content": "Hello"},\n]\n\nresult = SystemMessageDeduplicator().optimize(messages)\n\nsend_to_model(result.optimized_messages)\nprint(result.removed_count, result.removed_indexes)   # 1 (1,)'),
      callout("info", "Your list and its messages are never changed. ", h("code", {}, "optimized_messages"), " is a new list that holds the same message objects."),
      h("h2", {}, "How tokens are counted"),
      h("p", {}, "The tokens are counted on the whole message list written as compact JSON, so the saving includes the role and field names of every removed message."),
      h("h2", {}, "What it removes"),
      h("p", {}, "A system message that is identical to the message right before it, when that message is also a system message. If a user, assistant or tool message sits between two identical system messages, both are kept."),
    );
  }
}

customElements.define("tg-guide-messages-page", TgGuideMessagesPage);
