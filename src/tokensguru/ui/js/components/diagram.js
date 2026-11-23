import { h } from "../dom.js";
import { icon } from "../icons.js";

const arrow = () => h("div", { class: "darrow", "aria-hidden": "true" }, icon("chevron-down", 20));

function figure(label, ...children) {
  return h("figure", { class: "diagram", "aria-label": label }, ...children);
}

export function visionDiagram() {
  return figure(
    "Applications call TokensGuru, which sits between them and the LLM providers",
    h("div", { class: "dnode" }, "Applications"),
    arrow(),
    h(
      "div",
      { class: "dnode dmain" },
      h("div", { class: "dtitle" }, "TokensGuru"),
      h("div", { class: "dchips" }, ["Gateway", "Optimization", "Governance", "Observability"].map((name) => h("span", { class: "dchip" }, name))),
    ),
    arrow(),
    h("div", { class: "drow" }, [1, 2, 3].map(() => h("div", { class: "dnode" }, "LLM provider"))),
  );
}

export function hierarchyDiagram() {
  return figure(
    "The hierarchy: a platform has tenants, and each tenant has users, API keys, token budgets and usage",
    h("div", { class: "dnode" }, "Platform"),
    arrow(),
    h(
      "div",
      { class: "dnode dmain" },
      h("div", { class: "dtitle" }, "Tenant"),
      h("div", { class: "dchips" }, ["Users", "API keys", "Token budgets", "Usage"].map((name) => h("span", { class: "dchip" }, name))),
    ),
  );
}

export function flowDiagram(steps) {
  const nodes = [];
  steps.forEach((step, index) => {
    if (index) nodes.push(arrow());
    nodes.push(h("div", { class: index === 0 || index === steps.length - 1 ? "dnode dmain" : "dnode" }, step));
  });
  return figure("The typical product flow, from the developer application and back", ...nodes);
}
