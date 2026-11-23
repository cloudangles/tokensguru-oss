# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-11-23

### Added
- More optimizers: `BulletDeduplicator`, `ParagraphDeduplicator`, `JsonMinifier` and `SystemMessageDeduplicator`, plus a `Pipeline` that runs several together.
- Automatic token counting with tiktoken, and a rich `OptimizationResult` (id, tokens, characters, reason, time).
- Guardrails in `tokensguru.governance`: `EmailDetector`, `ApiKeyDetector`, `PiiDetector`, `PiiRedactor`, `PiiLeakageDetector`, `PromptInjectionDetector` and `ToxicityDetector`, plus a `GuardrailPipeline`. They work on text and on chat message lists, report a decision, a score and masked findings, and never store the input or the secret.
- Prompt injection and toxicity detection use a trained model automatically (`protectai/deberta-v3-base-prompt-injection-v2`, `unitary/toxic-bert`). It is downloaded the first time it is needed, kept on your machine and run locally; the rules keep working if it cannot be loaded. `tokensguru models status` and `tokensguru models download` show or fetch the models; `TOKENSGURU_MODELS=off` turns them off.
- `tokensguru docs`: a local docs site with a playground, optimizer and guardrail pages, and typical token savings and detection accuracy measured on built-in samples.
- `WhitespaceCleaner` optimizer (`tokensguru.optimizers`): collapses repeated spaces and blank lines and removes trailing whitespace from prose, with a `report()` of the characters saved. Code, tables, front matter, HTML raw blocks and JSON are left untouched.

### Changed
- The logo and the `info` table now use the brand gold colour.

### Removed
- The `dashboard` and `observability` commands, their `-d` and `-o` shortcuts and the full-screen terminal UI.

## [1.0.0] - 2026-11-20

### Added
- `tokensguru` command-line tool with `--version`, `version`, `info`, `dashboard` and `observability`.
- Shortcuts `-d` (dashboard) and `-o` (observability).
- Full-screen terminal dashboard and observability views with a trace table and graph/tree details.
- Packaging for PyPI under the Apache 2.0 license.
