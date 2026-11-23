# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-11-23

### Added
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
