---
name: pr-review-checklist
description: Generuje per-PR checklistę review (tests/docs/security/breaking changes) i opcjonalnie postuje jako comment na PR
activation:
  patterns:
    - "review checklist"
    - "checklist do PR"
    - "co sprawdzić w tym PR"
    - "pr review"
  intent_match: 0.6
requires_tools:
  - gh_pr_view
  - gh_pr_diff
  - gh_pr_comment
estimated_cost_usd: 0.20
---

# pr-review-checklist

Pomaga reviewerowi nie zapomnieć o niczym. Analizuje diff, klasyfikuje co
zostało zmienione (frontend/backend/migration/config/test/docs), generuje
**ukierunkowaną** checklistę (nie generyczną — np. "sprawdź czy migration
jest backward-compatible" tylko gdy są pliki *.sql).

## Inputs

- `pr_url` lub `repo` + `pr_number` (required)
- `post_as_comment` (bool, default: false — domyślnie tylko zwraca markdown)

## Steps

1. `gh_pr_view(pr_url)` — title, body, files changed, additions/deletions.
2. `gh_pr_diff(pr_url)` — pełen diff (max 10k linii — powyżej, ostrzeż).
3. Klasyfikacja zmian:
   - migration files (*.sql, alembic, knex) → checks: backward-compat, rollback plan, locking concerns
   - auth/security files (regex: auth|token|session|cors|csrf) → security review wymagany
   - new dependencies (package.json/lock, requirements.txt) → license check, supply chain
   - public API surface (route handlers, OpenAPI) → breaking changes section
   - test coverage delta — flaguj jeśli prod LOC > test LOC
4. Wygeneruj checklistę markdown.
5. Jeśli `post_as_comment=true` — `gh_pr_comment(pr_url, checklist)`.

## Output template

```
## Review checklist for PR #{n}: {title}

**Risk:** 🟢 low / 🟡 medium / 🔴 high (auto-classified)

### Must check
- [ ] {kontekstowo wygenerowane items}

### Nice to check
- [ ] ...
```

## Hard limits

- Nie approve'uj automatycznie (zostaw decyzję człowiekowi).
- Nie postuj do PR autora (only do reviewerów chyba że `post_as_comment=true`).
