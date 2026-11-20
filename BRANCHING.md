# Branching Guide

This document describes how branches are named and used in this repository.

## Main Branches

| Branch | Purpose |
| ------ | ------- |
| `main` | Stable, releasable code. All pull requests target `main` unless stated otherwise. |
| `release/<version>` | Optional. Used to prepare and patch a specific released version, for example `release/1.0.0`. |

Do not commit directly to `main`. Changes must come through a pull request.

## Working Branches

Create a new branch from the latest `main` for each change:

| Prefix | Use for | Example |
| ------ | ------- | ------- |
| `feature/` | New functionality | `feature/enterprise-license-check` |
| `fix/` | Bug fixes | `fix/tokenizer-empty-input` |
| `docs/` | Documentation only | `docs/update-readme-logo` |
| `refactor/` | Code restructuring with no behaviour change | `refactor/split-optimizer-core` |
| `ci/` | CI/CD and build configuration | `ci/add-type-check-workflow` |
| `chore/` | Maintenance, dependency updates | `chore/bump-ruff` |

Use lowercase letters, numbers, and hyphens only. Keep names short and descriptive. Include an issue number when one exists, for example `fix/123-tokenizer-empty-input`.

## Typical Workflow

1. Update your local `main`: `git checkout main && git pull`
2. Create a branch: `git checkout -b feature/<short-description>`
3. Make small, focused commits with clear messages.
4. Push the branch and open a pull request into `main`.
5. Fill in the pull request template completely.
6. Get at least one approving review and passing CI before merging.
7. Delete the branch after it is merged.

Keep branches short-lived. Rebase or merge `main` into your branch regularly to avoid large conflicts.

## Releases

1. Merge all planned changes into `main`.
2. Update `CHANGELOG.md` and the version number.
3. Tag the release on `main`, for example `v1.0.0`.
4. If a patch is needed for an older version, branch from its tag as `release/<version>`, apply the fix, and tag the new patch version.

## Protected Branches

The following should be protected on GitHub:

- `main`: require pull requests, at least one approving review, and passing status checks. Block force pushes and deletion.

## Existing Branches

- `project-foundation`: setup work for the project structure. Merge into `main` or delete once that work is complete.
- `tokensgutu_v1_0_0`: the name contains a typo ("tokensgutu" instead of "tokensguru"). Consider renaming it to `release/1.0.0` before the release is published.
