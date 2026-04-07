<!--
Thanks for contributing to Prophet! Please fill out the sections below.
The PR title becomes the squash-merge commit message, so make it clear.
Format: feat: / fix: / perf: / docs: / refactor: / chore: / test: + short summary
-->

## Summary

<!-- 2-3 bullet points: what changed and why -->

-
-

## Related issue

<!-- e.g. Closes #123. Use "Closes" / "Fixes" / "Resolves" to auto-close. -->

Closes #

## Type of change

<!-- Check all that apply -->

- [ ] feat — new feature or user-facing change
- [ ] fix — bug fix
- [ ] perf — performance improvement (no behavior change)
- [ ] refactor — internal restructuring (no behavior change)
- [ ] docs — documentation only
- [ ] test — tests only
- [ ] chore — tooling, deps, CI, build

## How to test

<!-- Steps a reviewer can follow to verify your change -->

1.
2.
3.

## Checklist

- [ ] Backend tests pass — `cd backend && uv run pytest -q`
- [ ] Frontend tests pass — `cd frontend && npx vitest run`
- [ ] TypeScript clean — `cd frontend && npx tsc --noEmit`
- [ ] ESLint clean — `cd frontend && npx eslint .`
- [ ] New code has tests (or this PR is docs/config only)
- [ ] PR is focused on one concern (no drive-by refactors)
- [ ] PR title follows conventional commit format

## Screenshots / GIF

<!-- For UI changes, include before/after screenshots or a short GIF -->

## Notes for reviewers

<!-- Anything reviewers should pay extra attention to, or known limitations -->
