# Contributing to Prophet

Thanks for thinking about contributing — Prophet only gets better when people
who actually use it tell us what's broken, what's missing, and what's confusing.

This guide will get you from zero to a merged PR in under 30 minutes.

---

## Ways to contribute

Not all contributions are code. We need all of these:

| Type | Effort | Impact |
|------|--------|--------|
| **Bug report with reproduction** | 10 min | Huge — we can fix what we can reproduce |
| **Documentation fix** (typo, clarity, missing example) | 10 min | High — every confused user matters |
| **Use case write-up** (you ran a simulation, share what you learned) | 1 hour | High — becomes our case studies |
| **Test case** for an edge case you found | 1 hour | High — prevents regressions |
| **`good first issue` pick** | 1–4 hours | High — small scoped tasks for newcomers |
| **Feature work** | varies | Open a Discussion first |
| **Translation** (README, docs) | varies | Helps non-English communities |

If your change is bigger than a small bug fix or documentation tweak, **please
open a GitHub Discussion or Issue first** so we can align on the approach. We
don't want you to write a thousand lines of code we'd ask you to throw away.

---

## Setup (under 10 minutes)

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ and [`uv`](https://github.com/astral-sh/uv)
- Node.js 20+ and `npm`

### Fork and clone (external contributors)

If you don't have push access to the main repo (you probably don't yet — and
that's normal), use the **fork workflow**. This is the standard open-source
pattern: you fork to your own GitHub account, push changes to your fork, then
open a PR back to the upstream repo.

```bash
# 1. Fork the repo on GitHub (button in the top-right of the repo page)
#    OR with the GitHub CLI:
gh repo fork showjihyun/Prophet --clone

# 2. cd into your local clone (gh fork --clone does this automatically)
cd Prophet

# 3. Add the upstream remote so you can pull updates from the main repo
git remote add upstream https://github.com/showjihyun/Prophet.git

# 4. Verify your remotes
git remote -v
# origin    https://github.com/<your-username>/Prophet.git  (your fork)
# upstream  https://github.com/showjihyun/Prophet.git       (the main repo)
```

### Run it

```bash
docker compose up -d
docker compose exec ollama ollama pull gemma4:latest   # first time only (~9.6 GB)
open http://localhost:5173
```

If the dashboard loads and you can create a simulation, you're done.

### Direct clone (core team / push access)

If you have push access to the upstream repo, skip the fork:

```bash
git clone https://github.com/showjihyun/Prophet.git
cd Prophet
docker compose up -d
```

### Backend dev loop

```bash
cd backend
uv sync                            # install deps
uv run uvicorn app.main:app --reload
uv run pytest -q                   # run all tests
uv run pytest tests/test_01_perception.py -v   # run one file
```

### Frontend dev loop

```bash
cd frontend
npm install
npm run dev                        # dev server with HMR
npx vitest run                     # run all tests
npx tsc --noEmit                   # type check
npx eslint .                       # lint
```

---

## Coding rules

A few non-negotiables. The full list is in `CLAUDE.md`.

### Python
- **Use `uv`, never `pip`.** `uv add package` to add a dep, `uv sync` to install.
- **Type hints required** on all function parameters and return values.
- **`async/await` first.** Sync code only for pure CPU work.
- **Specific exception types.** No bare `except:`.

### TypeScript / React
- **No hardcoded domain enum literals.** Import from `@/config/constants`.
  Example: use `SIM_STATUS.PAUSED`, not `'paused'`.
- **`interface` over `type`** for object shapes (use `type` for unions only).
- **Zustand store lives in `src/store/`** — nowhere else.
- **API calls go through `src/api/client.ts`** — no `fetch()` scattered around.

### Tests
- **Test before code** when changing behavior. The test should fail first, then pass after your fix.
- **Don't break existing tests** — all 1,658+ must stay green.
- **Test the contract**, not the implementation.

### Database
- **All schema changes via Alembic.** No direct DDL.

---

## Pull request workflow

The full walkthrough — from "I want to fix this" to "merged":

### 1. Claim an issue (or open one)

Comment **"I'd like to take this"** on an existing issue, or open a new one
describing what you want to do. This prevents two people working on the same
thing and gives you a sanity check before writing code.

For tiny fixes (typos, doc clarifications, one-line bugs) you can skip this
and go straight to a PR.

### 2. Sync your fork with upstream

Always start from the latest `main`:

```bash
git fetch upstream
git checkout main
git merge upstream/main         # or: git rebase upstream/main
git push origin main            # keep your fork in sync too
```

### 3. Create a branch

```bash
git checkout -b feat/my-thing     # or fix/, docs/, perf/, refactor/, chore/
```

Branch naming is a *suggestion*, not a hard rule for fork PRs. We squash-merge,
so your branch name doesn't end up in the commit history. Use whatever helps
you stay organized.

### 4. Write the test first

If you're changing behavior, write the failing test first. This is the single
fastest way to make sure your change does what you intended and doesn't break
something else. Skip this step only for documentation, build configuration,
or trivial typo fixes.

### 5. Make small, focused commits

Commit early and often locally. Don't worry about cleaning up your commit
history — we squash-merge, so all your WIP commits collapse into one clean
commit when the PR lands.

### 6. Run the full test suite locally

```bash
cd backend && uv run pytest -q
cd frontend && npx vitest run && npx tsc --noEmit && npx eslint .
```

If anything fails, fix it before pushing. Saves a CI roundtrip.

### 7. Push to your fork

```bash
git push -u origin feat/my-thing
```

### 8. Open the PR

```bash
gh pr create --repo showjihyun/Prophet --base main \
  --title "feat: my thing" \
  --body "Closes #123. ..."
```

Or use the GitHub web UI — when you push to your fork, GitHub shows a
"Compare & pull request" button.

**Use Draft PR if you're not done yet.** Draft PRs are perfect for "I want
early feedback before finishing" — they tell reviewers "don't merge yet, but
look at the approach":

```bash
gh pr create --draft --base main --title "feat: my thing (WIP)" --body "..."
```

When ready for real review, click **"Ready for review"** in the PR UI.

### 9. Respond to review

We aim for first response within 48 hours. When you address feedback:

- **Don't squash or rebase your branch** during review — just push new commits
  on top. Reviewers will use GitHub's "view changes since last review" feature.
- Reply to each comment with a short note ("done", "good catch", or "I'd
  rather not because…"). Don't leave comments unanswered.
- If review feedback expands the scope significantly, it's OK to push back
  and suggest a follow-up PR.

### 10. Merge

A maintainer will squash-merge when the PR is approved and CI is green. You
don't need to do anything — the merge button is on our side. Your fork's
branch can be deleted after merge (GitHub will offer a button).

---

## What if CI fails on my PR?

CI runs on every push. If it fails:

1. **Click the "Details" link** next to the failing check on the PR — this
   takes you to the actual error log
2. **Look for the test name or lint rule** that failed
3. **Reproduce locally** with the same command CI uses (`uv run pytest -q` /
   `npx vitest run` / `npx tsc --noEmit` / `npx eslint .`)
4. **Fix and push again** — CI will re-run automatically

If you can't figure it out:

- **Comment on the PR** with what you tried and what you see
- **Mention `@maintainers`** if it's been more than 24 hours
- We'd rather help than have you give up

---

## What if `main` moves while my PR is open?

Pull the latest upstream into your branch:

```bash
git fetch upstream
git checkout feat/my-thing
git merge upstream/main         # safer for newcomers
# OR
git rebase upstream/main        # cleaner history (advanced)
git push                          # if you rebased: --force-with-lease
```

If you hit conflicts you can't resolve, comment on the PR — we can usually
help in 5 minutes.

---

## What we look for in review

- Tests pass
- New code has tests (unless docs/config only)
- No new lint or type errors
- The diff is focused — one concern per PR
- Public API changes are documented
- Commit messages are clear (especially the PR title, since that becomes
  the squash-merge commit message)

---

## Issue labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Small, well-scoped, perfect for newcomers |
| `help wanted` | We'd love community help here |
| `bug` | Something is broken |
| `enhancement` | New feature or improvement |
| `documentation` | Docs / examples / clarity |
| `discussion` | Needs design conversation before code |
| `needs reproduction` | Bug report missing repro steps |
| `priority: low / medium / high` | Maintainer priority |

If you're new, filter by `good first issue` to find something approachable.

---

## Reporting bugs

Open a GitHub Issue with:

1. **What you did** (exact commands or clicks)
2. **What you expected**
3. **What actually happened**
4. **Environment** (OS, Docker version, browser if frontend)
5. **Logs** if you have them

The more we can reproduce, the faster we can fix it.

---

## Reporting security issues

**Do not open a public issue for security bugs.** Email
[security@prophet.io](mailto:security@prophet.io) instead. See
[`SECURITY.md`](SECURITY.md) for details.

---

## Recognition

Every contributor is listed in our release notes. First-time contributors get
a thank-you in the Discussions board. Regular contributors get commit access.

We're a small team building this in the open. Your help genuinely matters.

---

## Code of Conduct

Be kind. Be patient. Be willing to be wrong. Full text in
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
