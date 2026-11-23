import { h } from "../dom.js";
import { icon } from "../icons.js";

const STATES = {
  yes: { icon: "check", label: "Included" },
  basic: { icon: "check", label: "Basic" },
  no: { icon: "x", label: "Not included" },
};

function cell(entry) {
  const state = STATES[entry.state];
  return h(
    "td",
    { class: `compare-cell ${entry.state}` },
    h(
      "div",
      { class: "compare-body" },
      h("span", { class: "compare-state" }, icon(state.icon, 15), h("span", { class: "visually-hidden" }, `${state.label}: `)),
      h("span", { class: "compare-text" }, entry.text),
    ),
  );
}

export function comparisonTable(rows) {
  return h(
    "div",
    { class: "compare-wrap" },
    h(
      "table",
      { class: "compare" },
      h(
        "thead",
        {},
        h("tr", {}, h("th", { scope: "col" }, "Capability"), h("th", { scope: "col" }, "Open source"), h("th", { scope: "col", class: "compare-cloud" }, "Cloud and Enterprise")),
      ),
      h(
        "tbody",
        {},
        rows.map((row) =>
          row.group
            ? h("tr", { class: "compare-group" }, h("th", { scope: "colgroup", colspan: "3" }, row.group))
            : h("tr", {}, h("th", { scope: "row" }, row.name), cell(row.oss), cell(row.cloud)),
        ),
      ),
    ),
  );
}
