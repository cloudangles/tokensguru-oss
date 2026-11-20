# Contributing to TokensGuru

Thanks for helping. This guide covers setup, the checks every change must pass, and how changes reach `main`.

## Setup

Requires Python 3.9 or later.

```bash
git clone https://github.com/cloudangles/tokensguru-oss.git
cd tokensguru-oss
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
make install                                         # editable install with dev tools
pre-commit install && pre-commit install --hook-type commit-msg   # optional, runs checks on commit
```

## Running the checks

These are the same checks CI runs:

| Command | What it checks |
|---|---|
| `make lint` | ruff lint and formatting |
| `make typecheck` | strict mypy on `src/tokensguru` |
| `make coverage` | tests, and fails under 80% coverage |
| `make build` | builds the wheel and sdist and checks the metadata |
| `make audit` | known vulnerabilities in dependencies |
| `make check` | lint, types, coverage and build together |

Run `make check` before you push.

## Commit messages

Use [Conventional Commits](COMMIT_MESSAGES.md): `type(scope): summary`, for example `fix(cli): handle empty trace list`. The `commit-msg` hook and the CI commit-lint check both enforce this.

## Branches and pull requests

- Branch from an up-to-date `main`. Names are described in [BRANCHING.md](BRANCHING.md).
- Open a pull request into `main` and fill in the template.
- A pull request needs passing checks and one approving review before it merges.
- Keep pull requests small and focused. One change per pull request.

## Versions and releases

- The version lives in `src/tokensguru/version.py`. Changing it on `main` publishes that version to PyPI, if PyPI does not have it yet.
- Add a `CHANGELOG.md` entry for every version before you change the version.
- See [RELEASING.md](RELEASING.md) for the full release process.

## Reporting security issues

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).
