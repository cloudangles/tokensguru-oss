import { getGuardrails, getOptimizers } from "./api.js";
import { buildSections } from "./nav.js";

let sections = buildSections([]);
let optimizers = [];
let guardrails = [];
const listeners = new Set();

export function currentSections() {
  return sections;
}

export function currentOptimizers() {
  return optimizers;
}

export function currentGuardrails() {
  return guardrails;
}

export function onSectionsChange(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

export function loadSections() {
  return Promise.all([getOptimizers(), getGuardrails()])
    .then(([list, checks]) => {
      optimizers = list;
      guardrails = checks;
      sections = buildSections(list, checks);
      for (const callback of listeners) callback();
    })
    .catch(() => {});
}
