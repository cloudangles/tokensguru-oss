# Commit Message Guide

This project uses the [Conventional Commits](https://www.conventionalcommits.org/) format. Consistent commit messages make the history easy to read, and they allow the CHANGELOG and release notes to be generated automatically.

## Format

```
<type>(<optional scope>): <short summary>

<optional body: what changed and why>

<optional footer: breaking changes, issue references>
```

Example:

```
feat(optimizer): add repeated-content detection

Detects repeated prompt segments and replaces them with references
to reduce input token counts.

Closes #123
```

## Types

| Type | Use for |
| ---- | ------- |
| `feat` | A new feature |
| `fix` | A bug fix |
| `perf` | A performance improvement |
| `refactor` | Code change with no behaviour change |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `ci` | CI/CD or workflow changes |
| `build` | Build system or dependency changes |
| `chore` | Maintenance that doesn't fit another type |
| `revert` | Reverts an earlier commit |

## Rules

- Use the imperative mood: "add", "fix", "remove", not "added" or "fixes".
- Keep the summary line under 72 characters.
- Do not end the summary line with a period.
- Use lowercase for the type and the first word of the summary.
- Explain **why** in the body when the reason isn't obvious from the diff.
- One logical change per commit. Don't mix a feature and an unrelated fix.

## Breaking Changes

Mark breaking changes with `!` after the type or scope, and describe them in a `BREAKING CHANGE:` footer:

```
feat(api)!: rename `optimize()` to `compress()`

BREAKING CHANGE: `optimize()` has been renamed to `compress()`.
Update callers to use the new name.
```

## Good and Bad Examples

| Good | Bad |
| ---- | --- |
| `fix(client): retry on 429 responses` | `fixed stuff` |
| `docs: add install steps for Windows` | `Update README.md` |
| `refactor(tokenizer): extract cache helper` | `WIP` |
| `chore(deps): bump ruff to 0.6.0` | `more changes` |

## Enforcement

Messages are checked in two places:

1. **Locally, on commit.** The `commit-msg` hook in `.githooks/` rejects a message that doesn't match the format. Enable it once after cloning:

   ```bash
   git config core.hooksPath .githooks
   ```

2. **In CI, on every pull request.** The `Commit Message Lint` workflow checks every commit subject in the pull request. This catches commits made with `git commit --no-verify`, which skips local hooks. A pull request with an invalid commit subject cannot pass this check.

Merge and revert commits are allowed through both checks.

## Notes

- The existing commit `feat: add new SDK, update project files, and refresh README documentation` already follows this format. The earlier commits (`Initial commit: ...`, `Add README, ...`) do not. New commits should follow this guide.
- Keep commits focused, and squash fixup commits before merging a pull request.
