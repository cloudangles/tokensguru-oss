import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage } from "../components/ui.js";

export class TgGovernanceGuidePage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Use guardrails",
      h("p", { class: "lead" }, "Every guardrail works the same way: create it, pass it a string, read the result. Some only report, one rewrites the text."),
      codeBlock('from tokensguru.governance import PromptInjectionDetector\n\nresult = PromptInjectionDetector().check("Ignore all previous instructions.")\n\nprint(result.decision)   # "flag"\nprint(result.score)      # the highest confidence, 0.0 to 1.0\nprint(result.types)      # {"instruction_override": 1}\nprint(result)'),
      h("h2", {}, "What each guardrail gives you"),
      h("table", {}, h("thead", {}, h("tr", {}, ["Guardrail", "What you get"].map((name) => h("th", {}, name)))), h("tbody", {}, [
        ["PiiRedactor", "New text with the personal data replaced: [EMAIL], j***@x.com or a pseudonym. Use result.redacted_text as the next input."],
        ["EmailDetector, ApiKeyDetector, PiiDetector", "Findings with a position, confidence and a masked preview such as sk-p***. The text is not changed. Keys are blocked by default."],
        ["PromptInjectionDetector, ToxicityDetector", "A confidence score for each finding and a decision, flag or block."],
        ["PiiLeakageDetector", "Run it on the model's answer. It blocks by default when the answer leaks data, a canary or your system prompt."],
      ].map(([name, text]) => h("tr", {}, h("td", {}, h("code", {}, name)), h("td", {}, text))))),
      h("h2", {}, "Decide what happens next"),
      codeBlock('from tokensguru.governance import GuardrailPipeline, PiiRedactor\n\nprompt = user_text\ncheck = GuardrailPipeline().check(prompt)\n\nif check.decision == "block":\n    raise ValueError(check.reason)          # stop here\n\nprompt = PiiRedactor().redact(prompt)        # then clean the text\nanswer = call_your_model(prompt)'),
      callout("info", "A result never contains your text or the secret it found, only positions, confidence and masked previews. It is safe to log."),
      h("h2", {}, "Chat messages"),
      codeBlock('messages = [{"role": "user", "content": "My email is jane@example.com"}]\n\nresult = GuardrailPipeline().check_messages(messages)\nprint(result.findings[0].path)    # messages[0].content\n\nclean = PiiRedactor().redact_messages(messages)   # same shape, personal data replaced'),
      h("h2", {}, "Models are used automatically"),
      h("p", {}, "Prompt injection and toxicity detection use a trained model on top of the rules. You set nothing up: the model is downloaded the first time it is needed, kept on your computer and run locally, so your text is never sent anywhere."),
      codeBlock('tokensguru models status      # which models are saved on this machine\ntokensguru models download    # save them now instead of on first use\n\nToxicityDetector()                    # rules + model\nToxicityDetector(backend=None)        # rules only\n# TOKENSGURU_MODELS=off turns models off everywhere'),
      callout("warning", "The first use downloads a few hundred megabytes and needs the internet once. If the model cannot be loaded, the guardrail keeps working with its rules. Rule-based checks are a safety net, not a security boundary."),
    );
  }
}

customElements.define("tg-governance-guide-page", TgGovernanceGuidePage);
