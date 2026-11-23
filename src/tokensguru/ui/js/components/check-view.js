import { h, formatNumber } from "../dom.js";

const BADGE = { pass: "badge good", flag: "badge", redact: "badge", block: "badge danger" };

function stat(value, name) {
  return h("div", { class: "stat" }, h("div", { class: "value" }, value), h("div", { class: "name" }, name));
}

export function checkView(result) {
  const parts = [
    h(
      "div",
      { class: "stats" },
      stat(h("span", { class: BADGE[result.decision] || "badge" }, result.decision), "decision"),
      stat(String(result.score ?? 0), "score (highest confidence)"),
      stat(formatNumber(result.count), "found"),
      stat(`${result.duration_ms} ms`, "time"),
    ),
    h("p", {}, result.reason),
  ];
  if (typeof result.redacted_text === "string") {
    parts.push(h("h3", {}, "Redacted text"), h("pre", { class: "output", tabindex: "0" }, result.redacted_text));
  }
  if (result.findings.length) {
    parts.push(
      h(
        "table",
        {},
        h("thead", {}, h("tr", {}, ["Type", "Where", "Confidence", "Preview"].map((name) => h("th", {}, name)))),
        h(
          "tbody",
          {},
          result.findings.map((finding) =>
            h("tr", {}, h("td", {}, h("code", {}, finding.type)), h("td", {}, `${finding.path ? `${finding.path} ` : ""}${finding.start}–${finding.end}`), h("td", {}, String(finding.confidence)), h("td", {}, h("code", {}, finding.preview))),
          ),
        ),
      ),
    );
  }
  parts.push(h("p", { class: "muted" }, "The result holds positions and masked previews only. It never keeps your text or the secret itself."));
  return h("div", {}, ...parts);
}
