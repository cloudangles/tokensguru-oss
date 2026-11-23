import { h } from "../dom.js";
import "./tg-page-header.js";
import "./tg-callout.js";
import "./tg-card.js";

export function callout(type, ...children) {
  const element = document.createElement("tg-callout");
  element.setAttribute("type", type);
  element.append(...children.flat().map((child) => (child instanceof Node ? child : document.createTextNode(String(child)))));
  return element;
}

export function card({ heading, icon, href, cta, tone }, ...children) {
  const element = document.createElement("tg-card");
  element.setAttribute("heading", heading);
  element.setAttribute("href", href);
  if (icon) element.setAttribute("icon", icon);
  if (cta) element.setAttribute("cta", cta);
  if (tone) element.dataset.tone = tone;
  element.append(...children.flat().map((child) => (child instanceof Node ? child : document.createTextNode(String(child)))));
  return element;
}

export function cards(...items) {
  return h("div", { class: "card-grid" }, items);
}

export function skeletons(count = 4) {
  return h("div", { class: "card-grid", "aria-hidden": "true" }, Array.from({ length: count }, () => h("div", { class: "skeleton skeleton-card" })));
}

export function skeletonRows(count = 4) {
  return h("div", { "aria-hidden": "true" }, Array.from({ length: count }, (_, index) => h("div", { class: "skeleton skeleton-row", style: `width:${92 - index * 9}%` })));
}

export function feature(title, ...children) {
  return h("div", { class: "feature" }, h("h3", {}, title), h("div", { class: "feature-body" }, children));
}

export function features(...items) {
  return h("div", { class: "feature-grid" }, items);
}

export function bulletList(items) {
  return h("ul", { class: items.length >= 6 ? "cols" : null }, items.map((text) => h("li", {}, text)));
}

export function renderPage(host, title, ...children) {
  const header = document.createElement("tg-page-header");
  header.heading = title;
  host.replaceChildren(header, ...children.flat().filter(Boolean));
  document.title = `${title} · tokensguru docs`;
}
