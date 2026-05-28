---
name: confluence-create-page
description: Tworzy nową stronę Confluence jako draft pod wskazanym parentem; markdown body konwertowany na storage format
activation:
  patterns:
    - "stwórz stronę"
    - "create confluence page"
    - "dodaj do confluence"
    - "nowy dokument"
  intent_match: 0.55
requires_tools:
  - confluence_create_page
estimated_cost_usd: 0.10
---

# confluence-create-page

Niskopoziomowy skill — używany przez inne skills (jira-sprint-report,
pr-review-checklist) ale też dostępny dla user'ów do ad-hoc dokumentowania.

## Inputs

- `title` (string, required)
- `body_markdown` (string, required) — markdown, zostanie skonwertowany na storage format
- `space_key` (default: `BA`)
- `parent_page_id` (optional — bez tego strona ląduje pod root spacu)
- `labels` (lista, optional)

## Steps

1. Sanity check — `title` <= 255 znaków, body <= 1 MB.
2. Konwersja markdown → storage XML (zachowaj nagłówki, listy, tabele, linki, code blocks).
3. `confluence_create_page(space_key, title, storage, parent_page_id, labels)`.
4. Zwróć URL nowej strony.

## Hard limits

- Default tworzy jako draft (`status=draft`). User może podać `publish: true` żeby od razu opublikować.
- Nie nadpisuje istniejących stron — duplikat tytułu = error (user musi sam zdecydować update vs create new).
- Sprawdź permissions — jeśli user nie ma `create` w danym space, zwróć błąd z URL do request access.
