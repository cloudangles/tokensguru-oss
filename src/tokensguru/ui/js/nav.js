const item = (title, path, icon) => ({ title, path, icon });

export const LINKS = {
  github: "https://github.com/cloudangles/tokensguru-oss",
  pypi: "https://pypi.org/project/tokensguru/",
  changelog: "https://github.com/cloudangles/tokensguru-oss/blob/main/CHANGELOG.md",
  contact: "mailto:cloudangles@cloudangles.com?subject=tokensguru%20cloud%20and%20enterprise",
};

export function buildSections(optimizers = [], guardrails = []) {
  const ofKind = (kind) => optimizers.filter((entry) => entry.kind === kind);
  const page = (entry) => item(entry.name, `/optimizers/${entry.id}`);
  const tryIt = (entry) => item(entry.name, `/playground?optimizer=${entry.id}`);
  return [
    {
      id: "start",
      title: "Get started",
      groups: [{ items: [item("Overview", "/", "book"), item("Install", "/install", "download"), item("Quickstart", "/quickstart", "play")] }],
    },
    {
      id: "optimizers",
      title: "Optimizers",
      groups: [
        { items: [item("All optimizers", "/optimizers", "layers")] },
        { title: "Text optimizers", items: ofKind("text").map(page) },
        { title: "Chat messages", items: ofKind("messages").map(page) },
        { title: "Combine", items: ofKind("pipeline").map(page) },
      ],
    },
    {
      id: "governance",
      title: "Governance",
      groups: [
        { items: [item("All guardrails", "/governance", "shield"), item("Use guardrails", "/governance/guide", "book"), item("Guardrail playground", "/governance/playground", "play")] },
        { title: "Guardrails", items: guardrails.map((entry) => item(entry.name, `/governance/${entry.id}`)) },
      ],
    },
    {
      id: "playground",
      title: "Playground",
      groups: [
        { items: [item("Playground", "/playground", "play")] },
        { title: "Try an optimizer", items: optimizers.map(tryIt) },
      ],
    },
    {
      id: "guides",
      title: "Guides",
      groups: [
        {
          title: "Use the optimizers",
          items: [
            item("Use one optimizer", "/guides/single-optimizer"),
            item("Use a pipeline", "/guides/pipeline"),
            item("Chat messages", "/guides/chat-messages"),
            item("Options and tokenizer", "/guides/options"),
          ],
        },
      ],
    },
    {
      id: "reference",
      title: "Reference",
      groups: [
        {
          title: "Package",
          items: [item("Result fields", "/reference/result"), item("Command line", "/reference/cli")],
        },
        {
          title: "Links",
          items: [
            { title: "GitHub repository", href: LINKS.github },
            { title: "PyPI", href: LINKS.pypi },
            { title: "Changelog", href: LINKS.changelog },
          ],
        },
      ],
    },
  ];
}

export function sectionFor(sections, routeSection) {
  return sections.find((section) => section.id === routeSection) || sections[0];
}

export function firstPath(section) {
  for (const group of section.groups) {
    const first = group.items.find((entry) => entry.path);
    if (first) return first.path;
  }
  return "/";
}

export function allPages(sections) {
  const pages = [];
  for (const section of sections) {
    for (const group of section.groups) {
      for (const entry of group.items) {
        if (entry.path) pages.push({ title: entry.title, path: entry.path, section: section.title });
      }
    }
  }
  return pages;
}
