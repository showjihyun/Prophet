# Git Branch Strategy — Prophet (MCASP)

Version: 1.1 | Date: 2026-04-07 | Status: ACTIVE

This document defines the branching, PR, and merge workflow for Prophet.
The goal is a **linear, readable main history** with clear feature
boundaries and minimal merge friction.

## Audience

> **This document is for the core team / maintainers.**
>
> **External contributors should read [`CONTRIBUTING.md`](../CONTRIBUTING.md)
> first** — it covers the fork workflow, draft PRs, CI failure debugging,
> and other newcomer-friendly material that this document does NOT duplicate.
>
> The conventions below (branch naming, stacked PRs, `--force-with-lease`)
> are enforced for **maintainer branches inside the upstream repo only**.
> Contributor PRs from forks can use any branch name they want — we squash-merge,
> so the branch name never reaches `main` history anyway.

---

## TL;DR

```
main (protected, always deployable)
  │
  ├── feat/<topic>     ← short-lived feature branches
  ├── fix/<topic>      ← short-lived bug fix branches
  ├── perf/<topic>     ← performance work
  ├── docs/<topic>     ← documentation only
  ├── refactor/<topic> ← internal refactoring (no behavior change)
  └── chore/<topic>    ← tooling, deps, CI
```

**Rules:**
1. `main` only changes via squash-merged PR
2. All work happens on short-lived branches off latest `main`
3. Branch lives for one feature, deleted after merge
4. Tests + lint + typecheck must pass before merge
5. Squash merge keeps `main` history linear (one commit per PR)

---

## Two Workflows: Direct vs Fork

| Who | Workflow | Doc |
|-----|----------|-----|
| **Maintainers / core team** with push access | Direct branch in upstream repo | This document |
| **External contributors** without push access | Fork → branch in fork → PR back to upstream | [`CONTRIBUTING.md`](../CONTRIBUTING.md#pull-request-workflow) |

The two workflows produce identical PRs from `main`'s point of view —
both end in a squash merge of one PR onto `main`. The difference is just
*where* the working branch lives (upstream repo vs. a fork).

If you're a maintainer reviewing a fork PR, the standard `gh pr checkout
<number>` command works the same way regardless of where the branch lives.

---

## Branch Lifecycle (maintainer flow)

### 1. Start a new piece of work

```bash
# Always start from latest main
git checkout main
git pull origin main
git checkout -b feat/my-topic
```

### 2. Work iteratively

```bash
# Commit often, locally — these will be squashed at merge
git add -p
git commit -m "wip: trying approach A"
git commit -m "wip: refine approach A"
git commit -m "test: cover edge case"
```

### 3. Push and open a PR

```bash
git push -u origin feat/my-topic
gh pr create --base main --title "feat: my topic" --body "..."
```

### 4. Merge (squash)

```bash
gh pr merge <number> --squash --delete-branch
```

The squash combines all WIP commits into a single commit on `main` with
the PR title as the message. This gives `main` a clean, scannable history.

### 5. Sync local

```bash
git checkout main
git pull origin main
git branch -d feat/my-topic   # local cleanup
```

---

## Branch Naming Convention

| Prefix     | Use for                                   | Example                              |
|------------|-------------------------------------------|--------------------------------------|
| `feat/`    | New features, user-facing changes         | `feat/graph-3d`                      |
| `fix/`     | Bug fixes                                 | `fix/pause-resume-409`               |
| `perf/`    | Performance optimizations                 | `perf/network-cache-etag`            |
| `docs/`    | Documentation only                        | `docs/contributing-guide`            |
| `refactor/`| Internal refactoring, no behavior change  | `refactor/sim-status-constants`      |
| `chore/`   | Tooling, dependencies, CI, build configs  | `chore/upgrade-vite-5`               |
| `test/`    | Test-only changes                         | `test/agent-perception-edge-cases`   |
| `wip/`     | Throwaway experiments (rarely pushed)     | `wip/cytoscape-3d-spike`             |

**Naming rules:**
- Lowercase, kebab-case after the prefix
- Topic should describe the *outcome*, not the implementation (`feat/agent-tooltips` not `feat/add-help-circle`)
- Keep it short — under 40 characters
- One topic per branch — if scope grows, split it

---

## PR Conventions

### PR title format

Same as conventional commits, mirrors the branch prefix:

```
feat: <short summary>
fix: <short summary>
perf: <short summary>
docs: <short summary>
refactor: <short summary>
```

Examples (from real Prophet history):
- `feat: GAP-7 real-time propagation animation system`
- `fix: pause/resume control during Run All`
- `perf: O(N²) node lookup elimination + async LLM gather`
- `refactor: extract SIM_STATUS literals to constants`

### PR description format

```markdown
## Summary
- Bullet point of what changed
- Another bullet point
- Why this matters

## Test plan
- [ ] Backend tests pass (`uv run pytest`)
- [ ] Frontend tests pass (`npx vitest run`)
- [ ] TypeScript clean (`npx tsc --noEmit`)
- [ ] Manual verification: <steps>

## Related
Closes #123
```

### PR size

- **Ideal:** under 400 lines of diff
- **Acceptable:** under 1000 lines
- **Needs splitting:** over 1000 lines (open multiple PRs in dependency order)

If a feature is large, split into reviewable chunks:
- `feat/graph-3d-1-renderer` → renderer scaffolding
- `feat/graph-3d-2-controls` → camera controls
- `feat/graph-3d-3-integration` → wire into SimulationPage

Each PR builds on the previous one and is independently reviewable.

---

## Merge Strategy: Squash

We use **squash merge** for every PR. Reasons:

| Reason | Why it matters |
|--------|---------------|
| Linear history on main | `git log main` reads like a changelog |
| One commit = one feature | Easy to revert, bisect, cherry-pick |
| WIP messages don't pollute main | Local commits stay readable for reviewers but merge cleanly |
| No merge commits | No "Merge branch 'main' into feat/x" noise |

**Never** use:
- `git merge feat/x main --no-ff` (creates merge commits)
- `git rebase main && git push --force` on a shared branch (rewrites history others may have pulled)

The only acceptable way main changes is `gh pr merge --squash`.

---

## Conflict Resolution

### Scenario A — `main` moves while your PR is open

```bash
git checkout feat/my-topic
git fetch origin
git rebase origin/main      # rebase your branch on top of new main
# resolve conflicts, then:
git rebase --continue
git push --force-with-lease   # safe force push (refuses if remote moved)
```

**Always use `--force-with-lease`**, never `--force`.

### Scenario B — Your branch was off the wrong base

```bash
# Branched off feat/parent instead of main, but parent already merged
git checkout feat/my-topic
git rebase --onto main feat/parent feat/my-topic
git push --force-with-lease
```

### Scenario C — Conflict cascade (rebase blows up)

If a rebase has conflicts on every commit because the parent was squash-merged:

```bash
git rebase --abort

# Recreate the branch from clean main
git checkout main
git pull
git checkout -B feat/my-topic main

# Cherry-pick only your unique commits
git cherry-pick <sha1> <sha2> ...
git push --force-with-lease
```

This is exactly how we handled the `feat/graph-3d` cleanup when `feat/core-fixes`
was squash-merged.

---

## Protected Branches

`main` should be protected on GitHub with these rules:

- ✅ Require PR before merging
- ✅ Require status checks (tests, typecheck, lint) to pass
- ✅ Require branches to be up to date before merging
- ✅ Require linear history (squash merge only)
- ❌ Allow force pushes — never
- ❌ Allow direct commits to main — never
- ✅ Auto-delete head branches after merge

---

## Workflow Examples

### Example 1 — Solo feature

```bash
git checkout main && git pull
git checkout -b feat/agent-tooltips
# work, commit often
git push -u origin feat/agent-tooltips
gh pr create --base main --title "feat: agent tooltips on graph hover"
# review, get green CI
gh pr merge --squash --delete-branch
git checkout main && git pull
git branch -d feat/agent-tooltips
```

### Example 2 — Stacked PRs (large feature)

```bash
# PR 1: data layer
git checkout main && git pull
git checkout -b feat/graph-3d-1-data
# work, push, open PR
gh pr create --base main --title "feat(graph-3d): data layer"

# PR 2: builds on PR 1
git checkout -b feat/graph-3d-2-renderer feat/graph-3d-1-data
# work, push, open PR with base = feat/graph-3d-1-data
gh pr create --base feat/graph-3d-1-data --title "feat(graph-3d): renderer"

# When PR 1 merges to main, rebase PR 2 onto main
git checkout feat/graph-3d-2-renderer
git fetch origin
git rebase --onto main feat/graph-3d-1-data
git push --force-with-lease
gh pr edit --base main
```

### Example 3 — Hotfix during active feature work

```bash
# Currently on feat/big-thing — hotfix needed
git stash
git checkout main && git pull
git checkout -b fix/critical-bug
# fix, commit, PR, merge fast
git checkout main && git pull
git checkout feat/big-thing
git rebase main      # bring hotfix into your feature branch
git stash pop
```

---

## Anti-Patterns

| ❌ Don't | ✅ Do instead |
|---------|-------------|
| Commit directly to main | Open a PR, even for one-line fixes |
| Long-lived `develop` branch | Trunk-based with short feature branches |
| Merge commits on main | Squash merge only |
| Force-push shared branches without warning | `--force-with-lease` only, communicate first |
| Mix unrelated changes in one PR | One topic per PR |
| Branch off another feature branch unnecessarily | Branch off main; use stacked PRs only when there's a real dependency |
| Rebase a PR after review started | Add commits on top; squash will clean it up at merge |
| Delete branch before PR merges | Wait for `--delete-branch` flag on the merge command |

---

## Current Branch State (snapshot 2026-04-07)

```
main                  ← e0f45f9 (PR #1 squash merge: core fixes)
└── feat/graph-3d       ← 0e7ba32 (1 WIP commit on top of main)
```

PR #1 (`feat/core-fixes`) was squash-merged to main and the branch was
deleted from origin and local. `feat/graph-3d` was rebased to start from
the new main with only its unique WIP commit, then pushed.

---

## Quick Reference Card

```bash
# Start new work
git checkout main && git pull
git checkout -b feat/<topic>

# During work
git add -p && git commit -m "wip: ..."

# Open PR
git push -u origin feat/<topic>
gh pr create --base main --title "feat: ..." --body "..."

# Sync with main mid-PR
git fetch origin
git rebase origin/main
git push --force-with-lease

# Merge
gh pr merge <num> --squash --delete-branch

# After merge
git checkout main && git pull
git branch -d feat/<topic>
```
