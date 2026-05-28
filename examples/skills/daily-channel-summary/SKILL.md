---
name: daily-channel-summary
description: Czyta historię kanału Slack z ostatnich 24h i wyciąga decyzje, action items i blockers jako bullet list
activation:
  patterns:
    - "podsumuj kanał"
    - "summary kanału"
    - "co się działo na slacku"
    - "daily channel summary"
  intent_match: 0.6
requires_tools:
  - slack_channel_history
  - slack_user_lookup
estimated_cost_usd: 0.15
---

# daily-channel-summary

Idealne dla osób które wracają z urlopu / mają zbyt dużo kanałów. Filtruje
szum (memes, GIFy, single-emoji reactions) i wyciąga **decyzje + zobowiązania**.

## Inputs

- `channel` (string lub channel_id, required)
- `since` (ISO timestamp, default: 24h temu)
- `min_thread_messages` (default: 3 — pomijaj threadi z <3 wiadomościami)

## Steps

1. `slack_channel_history(channel, since)` — pobierz wszystkie wiadomości + thread replies.
2. Klastrowanie semantyczne — pogrupuj w tematy (LLM step, ~50 wiadomości max per cluster).
3. Per cluster wyciągnij:
   - **Decyzje** (zdania zawierające "decydujemy", "ustaliliśmy", "ok", "agreed")
   - **Action items** (zdania z czasownikiem przyszłym + osoba + termin)
   - **Blockers / questions** (zdania kończące się "?" bez odpowiedzi po 4h)
4. Zwróć w formacie:

```
## #{channel} — {since} → teraz

### 🎯 Decyzje (N)
- ...

### ✅ Action items (N)
- @user: ... (do: {date})

### ❓ Open questions (N)
- ...
```

## Hard limits

- Anonimizuj DM links (don't quote ID-only mentions).
- Pomijaj private subchannels do których bot nie ma joinu.
- Max 500 wiadomości per run (powyżej — proś o węższy `since`).
