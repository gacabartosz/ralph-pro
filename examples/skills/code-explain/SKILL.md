---
name: code-explain
description: Onboarding-style wyjaśnienie repo/folderu/pliku — architektura, data flow, kluczowe abstrakcje
activation:
  patterns:
    - "wyjaśnij kod"
    - "explain this code"
    - "jak działa ten"
    - "onboard me"
  intent_match: 0.55
requires_tools:
  - file_read
  - grep_repo
  - tree
estimated_cost_usd: 0.30
---

# code-explain

Top-down wyjaśnienie. NIE robi line-by-line walkthrough (to mało użyteczne) —
zamiast tego buduje **mapę mentalną** którą reader może rozszerzać własnym
czytaniem.

## Inputs

- `target` (path: repo root, folder, lub konkretny plik — required)
- `audience` (default: `developer` — wpływa na poziom abstrakcji; `developer | architect | new-hire`)
- `max_depth` (default: 3 dla repo, 1 dla file)

## Steps

1. **Orient** — `tree` na `target`, count files, identify top-level dirs.
2. **Stack detection** — package.json/pyproject/Cargo/go.mod → wypisz framework + key deps.
3. **Entry points** — szukaj `main.*`, `index.*`, `cli.*`, `__init__.*`, `app.*`, route definitions.
4. **Data flow** — od entry → wskaż gdzie idzie input, gdzie persistence, gdzie output (3-5 strzałek).
5. **Key abstractions** — top 5 plików/klas po LOC × import-count. Per każdy 1-2 zdania co robi.
6. **Render markdown:**
   ```
   ## {target} — overview

   **Stack:** {framework} + {key deps}
   **Lines of code:** {n} ({breakdown per language})

   ### Architektura w 60 sekund
   {3-5 zdaniowy paragraph}

   ### Entry points
   - `path/to/main` — ...

   ### Data flow
   ```
   user → router → handler → service → repo → db
   ```

   ### Key abstractions
   1. **{Class/Module}** (`path:line`) — {co robi}
   ...

   ### "Where do I look if I want to..."
   - Add new endpoint → `path/to/routes/`
   - Change auth → `path/to/auth/`
   ```

## Hard limits

- Nie generuj UML-i (text-only).
- Nie wyjaśniaj plików `vendor/`, `node_modules/`, generated code.
- Czytaj max 50 plików (powyżej — sampluj losowe + zaznacz "partial coverage").
