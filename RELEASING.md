# Releasing TokensGuru

Releases are automatic. You release a version by changing the version number on `main`.

## Normal release

1. On a branch, change `__version__` in `src/tokensguru/version.py`, for example from `1.0.0` to `1.0.1`.
2. Add a `## [1.0.1] - YYYY-MM-DD` section to `CHANGELOG.md`. The release is refused without it.
3. Open a pull request and get it reviewed. CI must pass.
4. Merge into `main`.
5. The **Publish to PyPI** workflow runs and does the following:
   - Checks that the version is new on PyPI and not older than the newest release.
   - Checks that the changelog has an entry for it.
   - Builds the package and checks the metadata.
   - Waits for approval in the `pypi` environment, if one is required.
   - Uploads to PyPI.
   - Installs the new version from PyPI in a clean environment and checks the command runs.
   - Creates the `v1.0.1` tag and a GitHub Release with the changelog notes.

## Pre-releases

Use a version such as `1.1.0rc1`, with its own changelog entry. The release is marked as a pre-release on GitHub. Users only get it with `pip install --pre tokensguru` or an explicit version.

## What the pipeline does not do

- **Change the version for you.** Bumping is a deliberate step in a pull request.
- **Publish code that is not on `main`.** Only merged changes are released.
- **Re-publish an existing version.** PyPI never allows the same version number twice. If a version has a problem, release the next version.

## Skipped runs

If you change the version file without changing the version number, or the version is already on PyPI, the run finishes successfully with a note in its summary, and nothing is published.

## Rolling back a bad release

PyPI does not delete releases, but it can **yank** them. A yanked release is hidden from new installs but still works for anyone who pinned it.

1. Log in to pypi.org, open the project, and open the release.
2. Choose **Options → Yank** and give a reason.
3. Release a fixed version (for example `1.0.2`) through the normal process.

Yanking does not change the GitHub tag or release. To mark the GitHub release as bad, edit its notes or delete the release.

## Setup (one time)

- Repository secret `PYPI_API_TOKEN`: a PyPI API token. Create it under your PyPI account settings.
- Environment `pypi`: optional, but recommended. Add required reviewers so each publish needs approval.
