---
name: bug-investigate
description: Autonomicznie investiguje bug ticket — czyta opis, szuka root cause w repo, pisze fix + test (no push)
activation:
  patterns:
    - "investigate bug"
    - "zbadaj buga"
    - "znajdź root cause"
    - "fix this bug"
  intent_match: 0.6
requires_tools:
  - jira_get_issue
  - file_read
  - grep_repo
  - run_tests
estimated_cost_usd: 1.50
---

# bug-investigate

Zaadaptowane z `~/projects/personal/ralph-daemon/prompts/investigate-bug.md`.
Idealne do uruchamiania przez `ralph-daemon` z profilem `jira-bug-auto-investigate`
albo ad-hoc gdy chcesz mieć pierwsze rozeznanie zanim sam przysiądziesz.

## Inputs

- `ticket` (Jira key, np. `BCSH-285`, required)
- `repo` (path lub git URL, required)
- `max_iterations` (default: 3 — po tylu pętlach Ralph zatrzyma się i napisze `INVESTIGATION.md`)

## Steps

1. `jira_get_issue(ticket)` — quote summary + description do output.
2. Szukaj w repo (grep) symptomów: function names, error strings, file paths z opisu.
3. Jeśli znalazłeś likely root cause:
   a. Stwórz branch `fix/{ticket}-investigation`
   b. Napisz minimalny diff + unit test który exposes bug
   c. `run_tests` — verify test fails BEZ fixa, passes Z fixem
4. Jeśli po `max_iterations` brak reproduction — zapisz `INVESTIGATION.md` z listą co próbowałeś, zakończ.

## Hard limits

- Stay inside `{repo}`. Nie dotykaj innych repo.
- Nie pushuj, nie otwieraj PR. Orchestrator handle to po EXIT_SIGNAL.
- Nie usuwaj plików chyba że bug jest **wyraźnie** o niechciany plik.

## EXIT_SIGNAL

Ostatnia wiadomość kończy się `EXIT_SIGNAL: true`.
