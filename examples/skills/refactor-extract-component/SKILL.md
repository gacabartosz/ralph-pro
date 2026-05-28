---
name: refactor-extract-component
description: Wyciąga fragment JSX/TSX/Vue do osobnego komponentu — props + tests + import sites updated
activation:
  patterns:
    - "extract component"
    - "wyciągnij komponent"
    - "refactor this jsx"
    - "ekstraktuj"
  intent_match: 0.6
requires_tools:
  - file_read
  - file_write
  - grep_repo
  - run_tests
estimated_cost_usd: 0.60
---

# refactor-extract-component

Frontend refactor skill. Ten konkretny zakres bo to **najczęstsza** mid-task
zmiana frontend devów (Bartosz preferuje React + TS, ale skill rozpoznaje też Vue/Svelte).

## Inputs

- `source_file` (path do pliku z JSX/TSX/Vue/Svelte, required)
- `lines` (range `start-end`, np. `42-89`, required — identyfikuje co wyciąć)
- `component_name` (PascalCase, required)
- `target_dir` (default: `./components/` względem source_file)

## Steps

1. **Read & parse** `source_file`, izoluj selected `lines`.
2. **Identify deps:**
   - external imports używane w wycinanym fragmencie → przeniesione do nowego pliku
   - lokalne refs (state, handlers, props) → stają się **props** nowego komponentu
   - TypeScript/PropTypes → wygeneruj signature
3. **Create** `{target_dir}/{component_name}.{tsx|vue|svelte}` z:
   - imports
   - typed props interface
   - extracted JSX
   - default export
4. **Update source** — zamień wycięte linie na `<{ComponentName} {...spread props} />`, dodaj import.
5. **Generate test** `{target_dir}/{component_name}.test.{tsx|spec.ts}` — basic render + 1 happy path interaction.
6. **Verify** — `run_tests` na nowym + zmodyfikowanym pliku. Jeśli istniejące testy fail → rollback i raportuj.

## Hard limits

- Nie ekstraktuj fragmentu który używa hooks z conditional logic (rules of hooks naruszone po extract).
- Nie ekstraktuj jeśli `lines` zawierają JSX expressions które referują do >5 lokalnych zmiennych (props bloat).
- Zachowaj naming convention z otaczających komponentów (jeśli sąsiednie pliki używają `.jsx` — nie zmieniaj na `.tsx`).
- Run formatter (prettier/biome) po write.

## Output

Lista zmienionych plików + diff URL (jeśli git worktree) + test result.
