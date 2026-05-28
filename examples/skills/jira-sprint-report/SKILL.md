---
name: jira-sprint-report
description: Generuje raport sprintu (Jira issues + Tempo worklogs) jako draft strony Confluence
activation:
  patterns:
    - "raport sprintu"
    - "sprint report"
    - "podsumowanie sprintu"
  intent_match: 0.6
requires_tools:
  - jira_get_sprint_issues
  - tempo_weekly_summary
  - confluence_create_page
estimated_cost_usd: 0.30
---

# jira-sprint-report

Generuje pełen raport zamykającego się sprintu i tworzy draft strony Confluence
(NIE publikuje — user musi sam wcisnąć "publish" po review).

## Inputs

- `sprint_id` (int) **lub** `sprint_name` (string, np. "Sprint 47 — BCSH backend")
- `confluence_space` (default: `BA`)
- `parent_page_id` (default: konfigurowalny per workspace)

## Steps

1. Resolve sprint — `jira_get_sprint_issues(sprint_id OR sprint_name)` → lista issue z `summary`, `status`, `storyPoints`, `assignee`.
2. Pobierz worklogs — `tempo_weekly_summary(sprint_start, sprint_end)` per assignee.
3. Zbuduj sekcje raportu:
   - **Done** (status=Done) — story points + lista
   - **Carried over** (status≠Done) — z powodem (komentarz ostatnich 7 dni)
   - **Tempo breakdown** — godziny per osoba + per epic
   - **Velocity** — porównanie do średniej z poprzednich 3 sprintów
4. `confluence_create_page` jako draft pod `parent_page_id`.
5. Zwróć URL draftu do user'a w threadzie.

## Hard limits

- Nie publikuj strony (zostaw jako draft).
- Nie modyfikuj statusów issue w Jira.
- Jeśli `tempo_weekly_summary` zwraca <50% expected hours — flaguj jako "data gap, manual review".
