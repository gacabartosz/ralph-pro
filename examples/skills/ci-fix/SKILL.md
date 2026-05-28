---
name: ci-fix
description: Autonomicznie naprawia failing CI run — czyta logi, lokalizuje błąd, próbuje minimal fix
activation:
  patterns:
    - "fix CI"
    - "ci failing"
    - "napraw CI"
    - "ci broken"
  intent_match: 0.6
requires_tools:
  - gh_workflow_run_view
  - gh_workflow_logs
  - file_read
  - run_tests
estimated_cost_usd: 1.00
---

# ci-fix

Zaadaptowane z `~/projects/personal/ralph-daemon/prompts/fix-ci.md`. Świetne
do uruchomienia przez `ralph-daemon` z profilem `github-ci-fail` — bot
reaguje na webhook `workflow_run.completed` z `conclusion=failure`.

## Inputs

- `run_id` (GitHub Actions run ID, required) **lub** `pr_url` (weźmie ostatni failing run)
- `max_iterations` (default: 2)

## Steps

1. `gh_workflow_run_view(run_id)` — workflow file, job name, step name które failed.
2. `gh_workflow_logs(run_id, job_id)` — ostatnie 200 linii logu failed step.
3. Klasyfikuj typ błędu:
   - **Test failure** — pytest/jest/go test output → znajdź konkretny test
   - **Lint/typecheck** — ruff/mypy/eslint/tsc output → znajdź file:line
   - **Build error** — kompilacja → znajdź first error
   - **Dependency missing** — package not found / version mismatch
   - **Infra failure** — npm install timeout, docker pull rate-limit → mark as flake, retry
4. Jeśli **flake** → retry workflow, exit.
5. Inaczej — minimal fix:
   - Test failure → poprawka assertion **lub** test (decyduj który jest "right" z kontekstu changelog)
   - Lint → run autofix command (ruff/eslint)
   - Build → fix import / type
6. Commit `fix(ci): {summary}` na branchu PR (jeśli `pr_url`) albo nowym `fix/ci-{run_id}`.
7. Nie pushuj — zostaw orchestrator'owi.

## Hard limits

- Nie commit'uj na main bezpośrednio.
- Nie disable test'u (kategorycznie — preferuj fix nawet jeśli długi).
- Po `max_iterations` bez zielonego runa → write `CI_INVESTIGATION.md`, exit.

## EXIT_SIGNAL

`EXIT_SIGNAL: true` na końcu ostatniego turn.
