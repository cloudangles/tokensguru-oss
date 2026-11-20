# Security Policy

## Supported Versions

Security fixes are applied to the latest released version only. Older versions do not receive patches.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| older   | :x:                |

## Reporting a Vulnerability

Please do **not** report security vulnerabilities through public GitHub issues, pull requests, or discussions.

Report them privately using one of these options:

1. **GitHub private vulnerability reporting (preferred):** open the repository's **Security** tab and click **Report a vulnerability**.
2. **Email:** send details to `security@<your-domain>` (replace with the project's security contact before publishing).

Please include as much of the following as you can:

- A description of the vulnerability and its potential impact
- The affected component (for example `src/tokensguru/...`, the SDK, or the dashboard/API)
- The version or commit you tested against
- Steps to reproduce, or a proof of concept
- Any suggested mitigation or fix

Do not include real API keys, customer data, or other secrets in your report. If a secret is needed to reproduce the issue, say so and we will arrange a safe way to share it.

## What to Expect

- **Acknowledgement:** within 3 business days of your report.
- **Triage:** within 7 business days we will confirm whether the issue is valid and how severe it is.
- **Fix and disclosure:** we aim to release a fix within 90 days of the initial report. We will keep you updated on progress and credit you in the release notes if you wish.

If a report is declined, we will explain why.

## Coordinated Disclosure

Please give us a reasonable amount of time to investigate and release a fix before disclosing the issue publicly. We will coordinate the disclosure timing with you.

## Scope

In scope:

- Code in this repository (the core package, SDKs, API, and dashboard)
- Official build and release artifacts

Out of scope:

- Vulnerabilities in third-party dependencies that have no impact on this project (please report those upstream)
- Issues that require physical access to a user's machine
- Social engineering of maintainers or contributors
- Denial-of-service testing against hosted infrastructure

## Safe Harbor

We will not pursue legal action against researchers who act in good faith, follow this policy, avoid privacy violations and data destruction, and give us a chance to fix the issue before disclosing it.
