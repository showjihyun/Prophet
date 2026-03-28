# 11 — Skills & Plugins SPEC
Version: 0.1.0 | Status: DRAFT

---

## 1. Overview

Prophet 프로젝트에서 사용하는 Claude Code 플러그인 및 커스텀 스킬 구성.
개발 생산성, 코드 품질, SPEC-GATE 규칙 준수를 자동화한다.

---

## 2. Official Plugins (설치 대상)

`/install-plugin` 으로 설치하는 공식 플러그인.

| Plugin | Skills | 용도 | 대상 |
|--------|--------|------|------|
| **commit-commands** | commit, commit-push-pr | Git 커밋 + PR 워크플로우 | 전체 |
| **frontend-design** | frontend-design | React 18 고품질 UI 생성 | Frontend |
| **feature-dev** | feature-dev | E2E 기능 개발 워크플로우 | 전체 |
| **code-simplifier** | simplify | 코드 리뷰/간소화 | 전체 |
| **hookify** | writing-rules | Hook/자동화 규칙 생성 | 전체 |
| **pyright-lsp** | (LSP) | Python 타입 체크 | Backend |
| **typescript-lsp** | (LSP) | TypeScript 타입 체크 | Frontend |
| **security-guidance** | (guidance) | 보안 가이드라인 | 전체 |
| **pr-review-toolkit** | (review) | PR 리뷰 자동화 | 전체 |
| **claude-md-management** | claude-md-improver | CLAUDE.md 품질 관리 | 전체 |

---

## 3. External Plugins (설치 대상)

| Plugin | Skills | 용도 |
|--------|--------|------|
| **github** | GitHub issue/PR 연동 | Git 워크플로우 |
| **playwright** | E2E 브라우저 테스트 | Frontend 테스트 |
| **supabase** | PostgreSQL 관리 참조 | DB 마이그레이션 참조 |

---

## 4. Custom Project Skills

현재 없음. CLAUDE.md의 SPEC-GATE 규칙 + PostToolUse hook이 동일 역할 수행.
필요 시 Phase 6~7에서 api-sync 스킬 검토.

---

## 5. 설치 순서

```bash
# Phase 1 (프로젝트 초기화 시)
/install-plugin commit-commands
/install-plugin feature-dev
/install-plugin code-simplifier
/install-plugin hookify
/install-plugin security-guidance
/install-plugin claude-md-management
/install-plugin pr-review-toolkit
/install-plugin github

# Phase 2+ (Backend 개발 시)
/install-plugin pyright-lsp

# Phase 7 (Frontend 개발 시)
/install-plugin frontend-design
/install-plugin typescript-lsp
/install-plugin playwright
```
