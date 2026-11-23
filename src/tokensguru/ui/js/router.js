export const ROUTES = [
  { path: "/", tag: "tg-overview-page", title: "Overview", section: "start" },
  { path: "/install", tag: "tg-install-page", title: "Install", section: "start" },
  { path: "/quickstart", tag: "tg-quickstart-page", title: "Quickstart", section: "start" },
  { path: "/optimizers", tag: "tg-optimizers-page", title: "All optimizers", section: "optimizers" },
  { path: "/optimizers/:id", tag: "tg-optimizer-page", title: "Optimizer", section: "optimizers" },
  { path: "/governance", tag: "tg-governance-page", title: "All guardrails", section: "governance" },
  { path: "/governance/guide", tag: "tg-governance-guide-page", title: "Use guardrails", section: "governance" },
  { path: "/governance/playground", tag: "tg-governance-playground-page", title: "Guardrail playground", section: "governance" },
  { path: "/governance/:id", tag: "tg-guardrail-page", title: "Guardrail", section: "governance" },
  { path: "/playground", tag: "tg-playground-page", title: "Playground", section: "playground" },
  { path: "/guides/single-optimizer", tag: "tg-guide-single-page", title: "Use one optimizer", section: "guides" },
  { path: "/guides/pipeline", tag: "tg-guide-pipeline-page", title: "Use a pipeline", section: "guides" },
  { path: "/guides/chat-messages", tag: "tg-guide-messages-page", title: "Chat messages", section: "guides" },
  { path: "/guides/options", tag: "tg-guide-options-page", title: "Options and tokenizer", section: "guides" },
  { path: "/reference/result", tag: "tg-ref-result-page", title: "Result fields", section: "reference" },
  { path: "/reference/cli", tag: "tg-ref-cli-page", title: "Command line", section: "reference" },
];

function match(pattern, path) {
  const wanted = pattern.split("/");
  const actual = path.split("/");
  if (wanted.length !== actual.length) return null;
  const args = {};
  for (let index = 0; index < wanted.length; index++) {
    if (wanted[index].startsWith(":")) args[wanted[index].slice(1)] = decodeURIComponent(actual[index]);
    else if (wanted[index] !== actual[index]) return null;
  }
  return args;
}

export function currentHash() {
  return window.location.hash.replace(/^#/, "") || "/";
}

export function currentRoute() {
  const hash = currentHash();
  const [path, query = ""] = hash.split("?");
  for (const route of ROUTES) {
    const args = match(route.path, path);
    if (args) return { route, path, args, params: new URLSearchParams(query) };
  }
  return { route: null, path, args: {}, params: new URLSearchParams(query) };
}

export function onRouteChange(callback) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}
