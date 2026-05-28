---
name: weekly-tempo-summary
description: Podsumowuje godziny Tempo z ostatnich 7 dni — per osoba, per projekt, z flagą under/over-booked
activation:
  patterns:
    - "tempo summary"
    - "ile godzin"
    - "podsumowanie godzin"
    - "weekly hours"
  intent_match: 0.6
requires_tools:
  - tempo_weekly_summary
estimated_cost_usd: 0.05
---

# weekly-tempo-summary

Szybki dashboard godzin z ostatniego tygodnia. Domyślnie ostatnie 7 dni do
dziś; user może podać `from`/`to`.

## Inputs

- `from` (ISO date, default: 7 dni temu)
- `to` (ISO date, default: dziś)
- `team` (lista emails, default: cały workspace)

## Steps

1. `tempo_weekly_summary(from, to, team)` — agregat godzin per assignee + per project.
2. Wylicz `expected_hours = workdays(from, to) * 8 * len(team)`.
3. Tagi statusu per osoba:
   - <30h → ⚠️ **under-booked**
   - 30-45h → ✅ **OK**
   - >45h → 🔥 **over-booked**
4. Wyrenderuj tabelę Markdown + total / project breakdown.

## Output format

```
## Tempo — {from} → {to}

| Osoba | Godziny | Status |
|---|---|---|
| ... | ... | ... |

Total: X / Y godzin (Z%)

### Per projekt
...
```

## Hard limits

- Read-only. Nie modyfikuj worklogs.
- Cache 1h (Tempo API rate-limit).
