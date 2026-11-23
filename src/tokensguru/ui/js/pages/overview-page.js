import { h } from "../dom.js";
import { bulletList, callout, card, cards, feature, features, renderPage } from "../components/ui.js";
import { flowDiagram, hierarchyDiagram, visionDiagram } from "../components/diagram.js";
import { comparisonTable } from "../components/compare.js";
import { LINKS } from "../nav.js";

const MODULES = [
  ["LLM Gateway", "Handle and route LLM requests"],
  ["Optimization Engine", "Reduce unnecessary tokens and context"],
  ["Intelligent Layer", "Select optimizers automatically and explain each decision"],
  ["Routing Engine", "Choose the best model for each request"],
  ["Context Management", "Keep long conversations within the context window"],
  ["Prompt Management", "Manage and version prompts"],
  ["Provider Management", "Connect supported LLM providers"],
  ["Tenant Management", "Manage organizations"],
  ["User Management", "Manage tenant users"],
  ["API Key Management", "Control application access"],
  ["Token Governance", "Manage usage limits"],
  ["Observability", "Monitor requests and agents"],
  ["Analytics", "Analyze usage, cost and savings"],
];

const FLOW = [
  "Developer application",
  "TokensGuru API",
  "Authentication",
  "Tenant and budget check",
  "Request classification",
  "Optimization",
  "LLM provider",
  "Response",
  "Usage, cost and trace",
  "Developer application",
];

const yes = (text) => ({ state: "yes", text });
const basic = (text) => ({ state: "basic", text });
const no = (text = "Not included") => ({ state: "no", text });

const COMPARISON = [
  { group: "Optimization" },
  { name: "Optimizers", oss: basic("Basic optimizers: extra whitespace, repeated paragraphs and bullets, JSON formatting, duplicate system messages"), cloud: yes("The full optimization engine, which picks the right technique for each request across system prompts, user messages, context, tool outputs, MCP schemas and agent outputs") },
  { name: "Intelligent layer", oss: no(), cloud: yes("Selects the right optimizers for each request automatically and explains every decision: what was chosen, what was skipped, and whether it is worth applying. It never calls an LLM. Try it first in shadow mode, which reports the savings without changing the text") },
  { name: "Advanced compression", oss: no(), cloud: yes("Content-aware compression for logs, diffs, search results, tables, code and HTML, plus semantic prompt compression and image and video optimization") },
  { name: "Context management", oss: no(), cloud: yes("Clears old tool results, summarizes long conversations and keeps session memory, so long agent runs stay inside the context window") },
  { name: "Caching", oss: no(), cloud: yes("Response caching and provider prompt caching, with the savings reported") },
  { group: "Routing and reliability" },
  { name: "Automatic routing", oss: no(), cloud: yes("Sends each request to the best model automatically: balanced, lowest cost, highest quality or lowest latency, with tenant rules and allowed models") },
  { name: "LLM providers", oss: no(), cloud: yes("One gateway for OpenAI, Anthropic and AWS Bedrock, with provider adapters") },
  { name: "Reliability", oss: no(), cloud: yes("Automatic retries, model fallbacks, timeouts and API key rotation") },
  { group: "Governance and usage" },
  { name: "Governance", oss: basic("Guardrails that run inside your own code: email, API key and personal data detection, redaction, leak checks, prompt injection and toxicity checks. They use built-in rules, with optional Hugging Face models"), cloud: yes("Full token governance: tenants, users, API keys, token budgets and budget enforcement, with managed, model-backed guardrails, configurable policies for each tenant and an audit trail") },
  { name: "Token consumption", oss: basic("Tokens before and after for each call you make"), cloud: yes("Token consumption tracked across the whole organization") },
  { name: "LLM costs", oss: no(), cloud: yes("Cost visibility for every request, together with the optimization savings") },
  { name: "Tenant-level usage", oss: no(), cloud: yes("Multi-tenancy, with usage per tenant, user and API key") },
  { group: "Prompts, agents and visibility" },
  { name: "Prompt management", oss: no(), cloud: yes("Central prompts with versions, active versions, history, diff, rollback and hot updates, plus model-assisted prompt rewriting with a safety review") },
  { name: "Agent activity", oss: no(), cloud: yes("Agent and tool activity, including tool calls, MCP tools and multi-agent workloads") },
  { name: "Dashboard and tracing", oss: basic("A local docs site and playground (tokensguru docs)"), cloud: yes("A web dashboard with live request traces, analytics and savings") },
  { group: "Support and license" },
  { name: "Support", oss: basic("Community support on GitHub"), cloud: yes("Enterprise-level support. Contact us") },
  { name: "License", oss: yes("Apache 2.0, free to use"), cloud: basic("Contact us for details") },
];

const SUCCESS_QUESTIONS = [
  "How much are we spending on LLMs?",
  "Where are we spending it?",
  "How many tokens are we using?",
  "How many tokens can we save?",
  "Which prompts and agents are expensive?",
  "Which provider and model is being used?",
  "What happened during an LLM request?",
  "Can we centrally control and govern LLM usage?",
];

export class TgOverviewPage extends HTMLElement {
  connectedCallback() {
    renderPage(
      this,
      "TokensGuru overview",
      h("p", { class: "lead" }, "TokensGuru is an LLM Gateway and Optimization Platform. It gives organizations centralized control over their LLM usage."),
      h("p", {}, "Applications connect to TokensGuru through a single platform interface. Each request goes through authentication, governance, optimization, provider routing and observability before the response is returned to the application."),
      h("p", {}, "The platform helps organizations manage:"),
      bulletList(["LLM providers", "Token consumption", "Prompt management", "LLM costs", "Agent activity", "API access", "Tenant-level usage", "Optimization", "Optimizer selection", "Model routing", "Context management"]),
      callout("info", "This site documents the open-source ", h("strong", {}, "tokensguru"), " Python package. It gives you basic optimizers and local guardrails. The complete platform described on this page, with the gateway, providers, prompts, costs, agents and tenants, is the Cloud and Enterprise offering."),
      h("div", { class: "toc", id: "toc", role: "navigation", "aria-label": "On this page" }),

      h("h2", {}, "Open source and Cloud and Enterprise"),
      h("p", {}, "TokensGuru comes in two forms. The open-source package gives you the basics to start shortening your LLM input today. Cloud and Enterprise adds the complete platform."),
      comparisonTable(COMPARISON),
      cards(
        card({ heading: "Use the open-source package", icon: "download", href: "#/install", cta: "Install tokensguru" }, "Free to use under the Apache 2.0 license. It needs Python 3.9 or newer."),
        card({ heading: "Talk to us about Cloud and Enterprise", icon: "server", href: LINKS.contact, cta: "Contact us", tone: "green" }, "Get the full platform, more cloud features and enterprise-level support."),
      ),

      h("h2", {}, "The complete platform"),
      callout("tip", "The sections below describe the complete TokensGuru platform. The open-source package includes only part of it. See the comparison above for what is in each."),
      h("h2", {}, "Product vision"),
      h("p", { class: "quote" }, "Make LLM usage optimized, observable, governed, and provider-independent."),
      h("p", {}, "TokensGuru aims to be the centralized control layer between applications and LLM providers."),
      visionDiagram(),

      h("h2", {}, "Mission"),
      h("p", {}, "TokensGuru's mission is to help organizations use LLMs more efficiently by providing a centralized platform for:"),
      bulletList(["Optimization", "Governance", "Observability", "Provider management", "Prompt management"]),

      h("h2", {}, "The business problem"),
      h("p", {}, "Organizations that use LLMs commonly face these challenges."),
      features(
        feature("Increasing LLM costs", h("p", {}, "Large prompts, repeated context, tool outputs and agent interactions increase token consumption.")),
        feature("Lack of visibility", h("p", {}, "Teams may not have a central view of:"), bulletList(["Token usage", "Cost", "Model usage", "Provider usage", "Agent activity", "Optimization savings"])),
        feature("Provider dependency", h("p", {}, "Applications often integrate directly with individual providers, which makes changing providers harder.")),
        feature("Prompt management", h("p", {}, "Prompts are often kept inside application repositories, which makes versioning, testing and updating them difficult.")),
        feature("Agent complexity", h("p", {}, "Modern AI systems may involve:"), bulletList(["Multiple agents", "Tool calls", "MCP tools", "Large context", "Agent-to-agent communication"]), h("p", {}, "This increases the need for central monitoring and optimization.")),
      ),

      h("h2", {}, "The product solution"),
      h("p", {}, "TokensGuru addresses these problems with a centralized LLM control layer. It provides:"),
      features(
        feature("Unified gateway", h("p", {}, "One integration point for supported LLM providers.")),
        feature("Optimization", h("p", {}, "Automatically identifies the optimization techniques that apply to each request.")),
        feature("Prompt management", h("p", {}, "Centralized prompts with versioning and controlled updates.")),
        feature("Governance", h("p", {}, "Tenant, user, API key and token-budget management.")),
        feature("Observability", h("p", {}, "Visibility into requests, tokens, cost, latency, optimization and agent activity.")),
        feature("Provider abstraction", h("p", {}, "Applications can work with several supported providers through TokensGuru.")),
        feature("Intelligent layer", h("p", {}, "Selects the right optimizers for each request automatically and explains every decision.")),
        feature("Automatic routing", h("p", {}, "Sends each request to the best model for its type, cost, quality and speed needs.")),
        feature("Context management", h("p", {}, "Keeps long conversations and agent runs inside the context window.")),
        feature("Reliability and caching", h("p", {}, "Retries, fallbacks and caching, so requests succeed and repeated work is not paid for twice.")),
      ),

      h("h2", {}, "Core capabilities"),
      h("h3", {}, "LLM gateway"),
      h("p", {}, "The gateway is the central entry point for LLM requests. It manages:"),
      bulletList(["Authentication", "Tenant identification", "Budget validation", "Request routing", "Provider communication", "Response handling"]),
      h("h3", { style: "margin-top:1.5rem" }, "LLM optimization"),
      h("p", {}, "TokensGuru analyzes each request and selects suitable optimization techniques. Optimization can be applied to:"),
      bulletList(["System prompts", "User messages", "Context", "Tool outputs", "MCP schemas", "Agent outputs"]),
      h("p", {}, "There are three primary optimization layers: system prompt, context and tool output, and user message optimization."),
      h("h3", { style: "margin-top:1.5rem" }, "Intelligent layer"),
      h("p", {}, "With so many optimization techniques, choosing the right ones for each request matters. The intelligent layer makes that choice for you. It inspects the request, decides which optimizers are worth applying, skips the ones that are not, and records the reason for every decision. It does not call an LLM. It runs in one of three modes:"),
      bulletList(["Off: use the standard optimizer", "Shadow: evaluates and runs its plan in isolation, returns your original text, and reports the savings it would have made", "Active: returns the validated, optimized text"]),
      h("p", {}, "Presets (conservative, balanced and aggressive) control how much risk it accepts. In the dashboard you can open any decision and see the stages, the optimizers it considered, the ones it skipped and why."),
      h("h3", { style: "margin-top:1.5rem" }, "Automatic model routing"),
      h("p", {}, "TokensGuru can choose the best model for each request. An application asks for an automatic model, and the platform picks one using a strategy:"),
      bulletList(["Balanced", "Lowest cost", "Highest quality", "Lowest latency", "Least used", "Weighted, for canary and A/B tests"]),
      h("p", {}, "Each request is first classified by how demanding it is (simple, standard, complex or reasoning). Models that cannot handle it are ruled out, for example when they do not support the tools or images used, have too small a context window, or are unhealthy. Each tenant sets its own routing rules, allowed models and cost limit, and every routing decision is recorded."),
      h("h3", { style: "margin-top:1.5rem" }, "Context management"),
      h("p", {}, "Long conversations and agent runs make prompts grow. TokensGuru keeps them manageable by:"),
      bulletList(["Clearing old tool results once the prompt grows past a limit", "Summarizing the older turns of a long conversation", "Optionally keeping session memory, so applications send only the new messages"]),
      h("h3", { style: "margin-top:1.5rem" }, "Reliability and caching"),
      h("p", {}, "If a provider fails, requests are retried and can fall back to another model or provider. Response caching and provider prompt caching avoid paying twice for the same work, and the savings are reported."),
      h("h3", { style: "margin-top:1.5rem" }, "Prompt management"),
      h("p", {}, "TokensGuru gives you one central place for prompts. You can manage:"),
      bulletList(["Prompt definitions", "Prompt versions", "Active versions", "Prompt history", "Model-specific configurations"]),
      h("p", {}, "It also covers prompt diff, rollback, hot updates and prompt-level tracing."),
      h("h3", { style: "margin-top:1.5rem" }, "Multi-provider access"),
      h("p", {}, "TokensGuru is designed to give access to several LLM providers. The initial providers are:"),
      bulletList(["OpenAI", "Anthropic", "AWS Bedrock"]),
      h("p", {}, "Provider adapters connect the platform to each provider."),
      h("h3", { style: "margin-top:1.5rem" }, "Token governance"),
      h("p", {}, "Organizations control LLM usage through:"),
      bulletList(["Tenant budgets", "User limits", "API keys", "Usage tracking", "Budget enforcement"]),
      h("p", {}, "The hierarchy is:"),
      hierarchyDiagram(),

      h("h2", {}, "Observability"),
      h("p", {}, "TokensGuru gives central visibility into LLM requests. It is designed to capture:"),
      bulletList(["Request", "Provider", "Model", "Input tokens", "Output tokens", "Tokens saved", "Cost", "Latency", "Errors", "Optimization activity", "Agent and tool activity"]),
      h("p", {}, "Traces are stored, and trace events are streamed to the dashboard for live visibility."),

      h("h2", {}, "Who it is for"),
      features(
        feature("Platform administrator", h("p", {}, "Manages the overall TokensGuru platform.")),
        feature("Developer", h("p", {}, "Integrates applications with TokensGuru and sends LLM requests.")),
        feature("AI/ML engineer", h("p", {}, "Uses the optimization and observability capabilities to improve AI workloads.")),
        feature("Engineering or product manager", h("p", {}, "Uses analytics to understand LLM usage, cost and performance.")),
      ),

      h("h2", {}, "Typical product flow"),
      h("p", {}, "This is the high-level flow of a request:"),
      flowDiagram(FLOW),

      h("h2", {}, "Product modules"),
      h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Module"), h("th", {}, "Purpose"))), h("tbody", {}, MODULES.map(([name, purpose]) => h("tr", {}, h("td", {}, name), h("td", {}, purpose))))),

      h("h2", {}, "Key benefits"),
      features(
        feature("For developers", bulletList(["One integration point", "Simplified provider access", "Centralized prompts", "Request visibility"])),
        feature("For AI/ML teams", bulletList(["Token optimization", "Context optimization", "Best-model routing", "Agent observability", "Optimization analytics"])),
        feature("For organizations", bulletList(["Centralized governance", "Token budgets", "Cost visibility", "Provider abstraction", "Secure credential management"])),
        feature("For management", bulletList(["LLM spend visibility", "Usage analytics", "Optimization savings", "Organizational governance"])),
      ),

      h("h2", {}, "What makes it different"),
      features(
        feature("1. Optimization at the gateway", h("p", {}, "Optimization happens before the request reaches the model provider.")),
        feature("2. Unified LLM access", h("p", {}, "Applications use a single TokensGuru interface across supported providers.")),
        feature("3. Optimization and observability together", h("p", {}, "Optimization results are connected directly to usage and cost visibility.")),
        feature("4. Prompt governance", h("p", {}, "Prompts can be managed centrally and versioned.")),
        feature("5. Agent-aware platform", h("p", {}, "Built to support modern agent, tool and multi-agent workloads.")),
      ),

      h("h2", {}, "Product scope"),
      h("p", {}, "The current core scope is:"),
      bulletList(["LLM gateway", "Provider integrations", "Token optimization", "Intelligent optimizer selection", "Automatic model routing", "Context management", "Reliability: retries and fallbacks", "Caching", "Prompt management", "Token governance", "Multi-tenancy", "API key management", "Usage tracking", "Cost tracking", "Request tracing"]),

      h("h2", {}, "How we measure success"),
      h("p", {}, "TokensGuru should let an organization answer these questions:"),
      bulletList(SUCCESS_QUESTIONS),
      h("p", {}, "If the platform answers them reliably while reducing unnecessary LLM consumption, it is delivering its core value."),

      h("h2", {}, "Start with the open-source package"),
      cards(
        card({ heading: "Install", icon: "download", href: "#/install", cta: "Install tokensguru" }, "Add the package with pip. It needs Python 3.9 or newer."),
        card({ heading: "Quickstart", icon: "play", href: "#/quickstart", cta: "Open quickstart" }, "Optimize your first text in a few lines of code."),
        card({ heading: "Optimizers", icon: "layers", href: "#/optimizers", cta: "Browse optimizers" }, "See what each optimizer removes and what it keeps."),
        card({ heading: "Try it now", icon: "terminal", href: "#/playground", cta: "Open the playground", tone: "green" }, "Paste your own text and watch the token count drop."),
      ),
    );
    this.buildContents();
  }

  buildContents() {
    const toc = this.querySelector("#toc");
    for (const heading of [...this.querySelectorAll("h2")]) {
      const chip = h("button", { type: "button", class: "chip" }, heading.textContent);
      chip.addEventListener("click", () => {
        heading.scrollIntoView({ behavior: "smooth", block: "start" });
        heading.setAttribute("tabindex", "-1");
        heading.focus({ preventScroll: true });
      });
      toc.append(chip);
    }
  }
}

customElements.define("tg-overview-page", TgOverviewPage);
