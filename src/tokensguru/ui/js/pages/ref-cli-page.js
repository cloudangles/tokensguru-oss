import { h } from "../dom.js";
import { codeBlock } from "../components/tg-code-block.js";
import { callout, renderPage } from "../components/ui.js";

export class TgRefCliPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "Command line",
      h("p", { class: "lead" }, "The ", h("code", {}, "tokensguru"), " command shows information about the package and starts this site."),
      h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Command"), h("th", {}, "What it does"))), h("tbody", {}, [
        ["tokensguru --version", "Print the version."],
        ["tokensguru version", "Print the version, Python version and platform."],
        ["tokensguru info", "Show the logo and details about the install."],
        ["tokensguru docs", "Start this docs site and open it in your browser."],
      ].map(([command, text]) => h("tr", {}, h("td", {}, h("code", {}, command)), h("td", {}, text))))),
      h("h2", {}, "tokensguru docs"),
      codeBlock("tokensguru docs              # start on port 8765 and open the browser\ntokensguru docs --port 9000  # use another port\ntokensguru docs --no-open    # start the server without opening a browser"),
      callout("info", "If the default port is busy, a free port is picked automatically. If you ask for a port with ", h("code", {}, "--port"), " and it is busy, the command stops with a message. Press Ctrl+C to stop the server."),
    );
  }
}

customElements.define("tg-ref-cli-page", TgRefCliPage);
