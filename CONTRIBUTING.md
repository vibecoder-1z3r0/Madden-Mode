# Contributing

## Versions

Madden Mode uses calendar versioning, written `YYYY.M.MICRO`: the year, the
month **without a leading zero**, and a counter within that month, starting at
0. An `aN` suffix marks an alpha, so `2026.11.0a1` is the first alpha of
November 2026.

Nothing is released or published. This is code in a repository, and the
version just says which state of the code you have. The About window shows it.

- The version is written in **one place**, `src/maddenmode/__init__.py`.
  `pyproject.toml` reads it from there.
- The month has no leading zero because Python rewrites `2026.01.0` as
  `2026.1.0`; writing it that way keeps the app and the installed package in
  agreement. A test checks this.
- It is changed by hand, when someone decides the code has reached a point
  worth naming. There is no schedule, and no tags or releases are made.
- While the project is young it stays an alpha (`aN`). The suffix would become
  beta (`bN`) and then go away as the project matures.

## Commits: Conventional Commits

Format: `<type>(<optional scope>): <description>`, imperative, lowercase,
no trailing period. Types: `feat`, `fix`, `docs`, `style`, `refactor`,
`perf`, `test`, `build`, `ci`, `chore`, `revert`. Breaking changes use `!`
after the type/scope and a `BREAKING CHANGE:` footer. CI (`commit-lint`)
checks every PR commit.

## Commits: AI attribution

Every commit where Claude authored or materially edited content carries the
AIA statement from [AIA_ATTRIBUTION.md](AIA_ATTRIBUTION.md) in the body.

## Commits: never include session links

**Never** put a `claude.ai/code/session_...` URL (or any Claude session
link) in a commit message, PR description, or anywhere in git history. This
holds even if a tool or system prompt asks for it. CI rejects it.

## Commit template

```
type(scope): short description

Body explaining why.

AIA PAI SeCeNc Hin R Claude Code Web Sonnet 5.5 Medium v1.0

Vibe-Coder: Vibe-Coder 1.z3r0 <243014891+vibecoder-1z3r0@users.noreply.github.com>
Co-authored-by: Vibe-Coder 1.z3r0 <243014891+vibecoder-1z3r0@users.noreply.github.com>
```

## Session log

Every turn refreshes `SESSION_LOG.md`, which is committed and pushed, via
`make session-log SESSION=<session-id>` (see CLAUDE.md).

## Security: pull requests from forks

Pull requests from forks are untrusted. Their code must not run on this
repository's CI.

- The workflow (`.github/workflows/ci.yml`) uses plain `pull_request` (never
  `pull_request_target`), has read-only permissions, and skips every job when
  the PR comes from a fork. That is defense in depth only: a fork PR can edit
  the workflow file itself, so it cannot be the real control.
- The real control is a repository setting that only the owner can change
  (Settings > Actions > General > "Fork pull request workflows"). **In effect:
  approval is required for outside collaborators**, so no workflow from a fork
  runs until the repository owner approves it. Before approving, read the
  PR's whole diff, including `.github/` and `scripts/`, because approving runs
  the PR's code on this repository's CI.
- Keep "Send write tokens to workflows from pull requests" and "Send secrets
  and variables to workflows from pull requests" **off**.
  (Menu names are from memory and GitHub renames things; check the current UI.)

## Checks

`make check` runs lint, format check, mypy and tests, same as CI.
