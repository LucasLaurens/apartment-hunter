---
name: commit-convention
description: Generates a Conventional Commits message (type(scope): description, scope always mandatory) from the staged diff.
---

Run a `/commit` session: read `git diff --staged`, pick the right type (feat, fix, docs, refactor, test, chore, perf, style), always set an explicit scope, write the short description in the imperative mood, add a body only if the "why" isn't obvious, and propose the message without committing automatically.

---

Always write a commit with 1 to 2 lines at most. Never mention the AI in commits. Follow the commit conventions as described at: "https://www.conventionalcommits.org/en/v1.0.0/" or "https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13" so use the appropriate types depending on what was done :
- feat: Commits that add, adjust or remove a feature to/of/from the API or UI
- fix: Commits that fix an API or UI bug of a preceded feat commit
refactor: Commits that rewrite or restructure code without altering API or UI behavior
- perf: Commits are special type of refactor commits that specifically improve performance
- style: Commits that address code style (e.g., white-space, formatting, missing semi-colons) and do not affect application behavior
- test: Commits that add missing tests or correct existing ones
- docs: Commits that exclusively affect documentation
- build: Commits that affect build-related components such as build tools, dependencies, project version, ...
- ops: Commits that affect operational aspects like infrastructure (IaC), deployment scripts, CI/CD pipelines, backups, monitoring, or recovery procedures, ...
- chore: Commits that represent tasks like initial commit, modifying .gitignore, ...
