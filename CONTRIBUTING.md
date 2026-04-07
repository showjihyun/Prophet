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

### Clone and run

```bash
git clone https://github.com/your-org/prophet.git
cd prophet
docker compose up -d
docker compose exec ollama ollama pull llama3.1:8b   # first time only
open http://localhost:5173
```

If the dashboard loads and you can create a simulation, you're done.

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
- **Don't break existing tests** — all 1,234+ must stay green.
- **Test the contract**, not the implementation.

### Database
- **All schema changes via Alembic.** No direct DDL.

---

## Pull request workflow

1. **Open or claim an issue first.** Comment "I'd like to take this" and we'll
   assign it to you. This prevents two people working on the same thing.
2. **Branch from `main`** (or whatever the active dev branch is).
3. **Write the test first** if you're changing behavior.
4. **Keep PRs small.** One concern per PR. Big refactors split into reviewable chunks.
5. **Run the full test suite locally** before pushing:
   ```bash
   cd backend && uv run pytest -q
   cd frontend && npx vitest run && npx tsc --noEmit && npx eslint .
   ```
6. **Write a clear PR description** — what changed, why, how to verify. Link the
   issue with `Closes #123`.
7. **Be patient and responsive** during review. We aim for 48-hour first response.

### What we look for in review

- Tests pass
- New code has tests
- No new lint or type errors
- The diff is focused (no drive-by refactors)
- Public API changes are documented
- Commit messages are clear

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
