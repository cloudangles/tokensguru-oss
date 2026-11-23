import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, card, cards, renderPage } from "../components/ui.js";

export class TgInstallPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Install",
      h("p", { class: "lead" }, "tokensguru is a regular Python package. Install it with pip into any environment that uses Python 3.9 or newer."),
      codeBlock("pip install tokensguru"),
      h("p", {}, "The only dependency is ", h("code", {}, "tiktoken"), ", the tokenizer used to count tokens. pip installs it for you."),
      h("h2", {}, "Check the install"),
      codeBlock("tokensguru --version"),
      h("p", {}, "You can also import it from Python:"),
      codeBlock('from tokensguru.optimizers import Pipeline\n\nprint(Pipeline().optimize("Hello     world.   ").optimized_text)'),
      callout("tip", "The first time tokens are counted, tiktoken downloads the tokenizer's vocabulary once, so that first run needs the internet and takes a few seconds. After that it is cached on your machine."),
      h("h2", {}, "Open these docs"),
      h("p", {}, "This site ships inside the package. Start it from a terminal and it opens in your default browser:"),
      codeBlock("tokensguru docs"),
      h("h2", {}, "Next steps"),
      cards(
        card({ heading: "Quickstart", icon: "play", href: "#/quickstart", cta: "Open quickstart" }, "Optimize your first text."),
        card({ heading: "Command line", icon: "terminal", href: "#/reference/cli", cta: "See all commands" }, "Options for tokensguru docs."),
      ),
    );
  }
}

customElements.define("tg-install-page", TgInstallPage);
