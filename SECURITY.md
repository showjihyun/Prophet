# Security Policy

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you believe you've found a security vulnerability in Prophet, send an email
to **[security@prophet.io](mailto:security@prophet.io)** with:

1. A description of the issue
2. Steps to reproduce
3. Affected versions
4. Your assessment of the impact
5. Any suggested mitigation, if you have one

We will:

- Acknowledge receipt within **48 hours**
- Provide an initial assessment within **7 days**
- Work with you to confirm and fix the issue
- Credit you in the release notes (unless you'd rather stay anonymous)

## Scope

In scope:

- The Prophet backend (FastAPI, simulation engine, database layer)
- The Prophet frontend (React app, WebSocket handlers)
- The default Docker Compose deployment
- Authentication and authorization
- Any handling of user-provided LLM API keys or credentials

Out of scope:

- Vulnerabilities in upstream dependencies (report those upstream — we'll
  pick up the fix when it ships)
- Self-inflicted misconfiguration (e.g., exposing your own dev instance to
  the public internet without auth)
- Attacks requiring physical access to the machine running Prophet

## Supported Versions

Prophet is in active development. Security fixes apply to:

| Version | Supported          |
|---------|--------------------|
| `main`  | ✅                 |
| Latest tagged release | ✅   |
| Older releases | ❌ (please upgrade) |

## Disclosure Timeline

We aim for **coordinated disclosure**:

1. You report the issue privately
2. We acknowledge and confirm
3. We develop and test a fix
4. We coordinate a release date with you
5. We publish the fix and a security advisory crediting you

We aim to fix and disclose within **90 days** of confirmation, though we may
move faster for critical issues or slower for complex ones.

## Bug Bounty

We do not currently offer a paid bug bounty. We do offer:

- Public credit in release notes
- A genuine thank-you in the project changelog
- Mention in our community channels

Thank you for helping keep Prophet and its users safe.
