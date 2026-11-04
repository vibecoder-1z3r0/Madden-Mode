# Contributing

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

## Checks

`make check` runs lint, format check, mypy and tests, same as CI.
