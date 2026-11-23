import { h } from "../dom.js";

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = h("textarea", { readonly: true, style: "position:fixed;left:-999px;top:0" });
    area.value = text;
    document.body.append(area);
    area.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }
    area.remove();
    return copied;
  }
}

export class TgCodeBlock extends HTMLElement {
  get code() {
    return this._code || "";
  }

  set code(value) {
    this._code = value;
    if (this.isConnected) this.render();
  }

  connectedCallback() {
    this.render();
  }

  render() {
    const button = h("button", { type: "button", "aria-label": "Copy code" }, "Copy");
    button.addEventListener("click", async () => {
      const copied = await copyText(this.code);
      button.textContent = copied ? "Copied" : "Press Ctrl+C";
      setTimeout(() => (button.textContent = "Copy"), 1500);
    });
    this.replaceChildren(h("pre", {}, h("code", { text: this.code })), button);
  }
}

customElements.define("tg-code-block", TgCodeBlock);

export function codeBlock(code) {
  const block = document.createElement("tg-code-block");
  block.code = code;
  return block;
}
