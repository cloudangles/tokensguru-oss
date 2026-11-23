const PATHS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  github: '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  "chevron-right": '<path d="m9 6 6 6-6 6"/>',
  external: '<path d="M7 17 17 7M8 7h9v9"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>',
  warning: '<path d="M12 3 2 20h20L12 3zM12 10v4M12 17h.01"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5zM3 13l9 5 9-5"/>',
  braces: '<path d="M8 4c-2 0-3 1-3 3v2c0 1-1 3-2 3 1 0 2 2 2 3v2c0 2 1 3 3 3M16 4c2 0 3 1 3 3v2c0 1 1 3 2 3-1 0-2 2-2 3v2c0 2-1 3-3 3"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  text: '<path d="M4 6h16M4 12h10M4 18h14"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.5 7.2L3 21l1.8-5.5A8 8 0 1 1 21 12z"/>',
  terminal: '<path d="m4 17 6-5-6-5M12 19h8"/>',
  play: '<path d="m6 4 14 8-14 8V4z"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5zM4 21V5"/>',
  download: '<path d="M12 3v12m0 0-4-4m4 4 4-4M4 21h16"/>',
  shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3z"/><path d="m9 12 2 2 4-4"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  paragraph: '<path d="M13 4v16M17 4v16M13 4H9a4 4 0 0 0 0 8h4"/>',
  server: '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01"/>',
};

export function icon(name, size = 18) {
  const svg = new DOMParser().parseFromString(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${PATHS[name] || ""}</svg>`,
    "image/svg+xml",
  ).documentElement;
  return document.importNode(svg, true);
}

const OPTIMIZER_ICONS = {
  prose_whitespace_cleanup: "text",
  exact_paragraph_deduplication: "paragraph",
  exact_bullet_item_deduplication: "list",
  tokenguru_json_minifier: "braces",
  exact_duplicate_system_messages: "chat",
  pipeline: "layers",
};

export function optimizerIcon(id) {
  return OPTIMIZER_ICONS[id] || "sliders";
}

const GUARDRAIL_ICONS = {
  email_detection: "chat",
  api_key_detection: "braces",
  pii_detection: "shield",
  pii_redaction: "paragraph",
  pii_leakage_detection: "server",
  prompt_injection_detection: "terminal",
  toxicity_detection: "warning",
};

export function guardrailIcon(id) {
  return GUARDRAIL_ICONS[id] || "shield";
}
